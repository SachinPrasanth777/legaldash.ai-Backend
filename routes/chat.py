from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Tuple
from io import BytesIO
import re
import os
from dotenv import load_dotenv
import PyPDF2
from openai import OpenAI
from pydantic import BaseModel
from utilities.minio import client
from minio.error import S3Error
import logging
import json
import asyncio
import functools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_router = APIRouter()

load_dotenv()


def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return api_key


openai_client = OpenAI(api_key=get_openai_api_key())


def extract_text_from_pdf_bytes(pdf_bytes: BytesIO) -> str:
    try:
        reader = PyPDF2.PdfReader(pdf_bytes)
        text = "".join(page.extract_text() for page in reader.pages)
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""


def extract_sections_from_sue_letter(sue_letter: str) -> List[str]:
    section_pattern = r"Section\s+(\d+)"
    sections = re.findall(section_pattern, sue_letter)
    logger.info(f"Extracted sections from sue letter: {sections}")
    return sections


def extract_section_from_nda(nda: str, section_number: str) -> str:
    section_pattern = rf"Section\s+{section_number}[\s\S]+?(?=Section|\Z)"
    match = re.search(section_pattern, nda)
    if match:
        logger.info(f"Found content for Section {section_number}")
        return match.group(0)
    else:
        logger.info(f"No content found for Section {section_number}")
        return ""


async def match_with_ipc(section_content: str) -> str:
    prompt = f"""
    Given the following section from an NDA, identify the most relevant section(s) 
    of the Indian Penal Code (IPC) that could be applicable. Provide the IPC section 
    number(s) and a brief explanation of why it's relevant:

    NDA Section:
    {section_content}

    Relevant IPC Section(s):
    """
    try:
        response = await asyncio.to_thread(
            functools.partial(
                openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {str(e)}")
        return ""


async def analyze_documents(
    sue_letter: str, nda: str
) -> Dict[str, List[Tuple[str, str]]]:
    results = {}
    sections = extract_sections_from_sue_letter(sue_letter)

    if not sections:
        logger.warning("No sections found in the sue letter.")
        results["message"] = "No sections found in the sue letter."
        return results

    tasks = []
    for section in sections:
        nda_section = extract_section_from_nda(nda, section)
        if nda_section:
            task = asyncio.create_task(match_with_ipc(nda_section))
            tasks.append((section, nda_section, task))
        else:
            logger.warning(f"Section {section} not found in NDA.")
            results[section] = [("Error", f"Section {section} not found in NDA.")]

    await asyncio.gather(*(task for _, _, task in tasks))

    for section, nda_section, task in tasks:
        ipc_match = await task
        results[section] = [("NDA Content", nda_section), ("IPC Match", ipc_match)]

    return results


def clean_text(text):
    return re.sub(r"(\n|\\n)", " ", text)


def clean_dict(d):
    if isinstance(d, dict):
        return {k: clean_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_dict(v) for v in d]
    elif isinstance(d, str):
        return clean_text(d)
    else:
        return d


class AnalyzeDocumentsMinioRequest(BaseModel):
    sue_letter_path: str
    nda_path: str


@chat_router.post("/analyze-documents-minio")
async def analyze_documents_minio_endpoint(
    request: AnalyzeDocumentsMinioRequest, background_tasks: BackgroundTasks
):
    logger.info("Received request for analyze_documents_minio_endpoint")
    sue_letter_path = request.sue_letter_path
    nda_path = request.nda_path

    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(
            status_code=500, detail="MinIO bucket name is not configured"
        )

    try:
        sue_letter_data, nda_data = await asyncio.gather(
            asyncio.to_thread(client.get_object, bucket_name, sue_letter_path),
            asyncio.to_thread(client.get_object, bucket_name, nda_path),
        )

        sue_letter_bytes = BytesIO(sue_letter_data.read())
        nda_bytes = BytesIO(nda_data.read())

        sue_letter_data.close()
        nda_data.close()
        sue_letter_data.release_conn()
        nda_data.release_conn()
    except S3Error as err:
        logger.error(f"MinIO S3Error: {str(err)}")
        raise HTTPException(
            status_code=404, detail=f"File not found in MinIO: {str(err)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving files from MinIO: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving files from MinIO: {str(e)}"
        )

    sue_letter_text, nda_text = await asyncio.gather(
        asyncio.to_thread(extract_text_from_pdf_bytes, sue_letter_bytes),
        asyncio.to_thread(extract_text_from_pdf_bytes, nda_bytes),
    )

    if not sue_letter_text or not nda_text:
        logger.error("Failed to extract text from one or both PDFs")
        raise HTTPException(
            status_code=400, detail="Failed to extract text from one or both PDFs"
        )

    results = await analyze_documents(sue_letter_text, nda_text)

    if not results:
        logger.error("No results generated from document analysis")
        raise HTTPException(status_code=500, detail="No results generated")

    clean_results = clean_dict(results)
    json_results = json.dumps(
        clean_results, ensure_ascii=False, indent=2, separators=(",", ": ")
    )

    background_tasks.add_task(sue_letter_bytes.close)
    background_tasks.add_task(nda_bytes.close)

    return JSONResponse(content=json.loads(json_results))
