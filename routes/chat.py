# chat.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Tuple
from io import BytesIO
import re
import os
from dotenv import load_dotenv
import PyPDF2
import openai
from pydantic import BaseModel
from utilities.minio import client  # Import the MinIO client
from minio.error import S3Error
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_router = APIRouter()

load_dotenv()

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return api_key

openai.api_key = get_openai_api_key()  # Initialize OpenAI API key

def extract_text_from_pdf_bytes(pdf_bytes: BytesIO) -> str:
    try:
        reader = PyPDF2.PdfReader(pdf_bytes)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_sections_from_sue_letter(sue_letter: str) -> List[str]:
    section_pattern = r"Section\s+(\d+)"
    sections = re.findall(section_pattern, sue_letter)
    return sections

def extract_section_from_nda(nda: str, section_number: str) -> str:
    section_pattern = rf"Section\s+{section_number}[\s\S]+?(?=Section\s+\d+|\Z)"
    match = re.search(section_pattern, nda)
    if match:
        return match.group(0)
    return ""

def match_with_ipc(section_content: str) -> str:
    prompt = (
        f"Given the following section from an NDA, identify the most relevant section(s) of the Indian Penal Code (IPC) that could be applicable. "
        f"Provide the IPC section number(s) and a brief explanation of why it's relevant:\n\nNDA Section: {section_content}\n\nRelevant IPC Section(s):"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {str(e)}")
        return ""

def analyze_documents(sue_letter: str, nda: str) -> Dict[str, List[Tuple[str, str]]]:
    results = {}
    sections = extract_sections_from_sue_letter(sue_letter)
    if not sections:
        results["message"] = "No sections found in the sue letter."
        return results

    for section in sections:
        nda_section = extract_section_from_nda(nda, section)
        if nda_section:
            ipc_match = match_with_ipc(nda_section)
            cleaned_nda_section = nda_section.replace('\n', ' ')
            cleaned_ipc_match = ipc_match.replace('\n', ' ')
            results[section] = [
                ("NDA Content", cleaned_nda_section),
                ("IPC Match", cleaned_ipc_match)
            ]
        else:
            results[section] = [("Error", f"Section {section} not found in NDA.")]
    return results

# Define the Pydantic model for the request body
class AnalyzeDocumentsMinioRequest(BaseModel):
    sue_letter_path: str
    nda_path: str

@chat_router.post("/analyze-documents-minio")
async def analyze_documents_minio_endpoint(
    request: AnalyzeDocumentsMinioRequest
):
    logger.info("Received request for analyze_documents_minio_endpoint")
    sue_letter_path = request.sue_letter_path
    nda_path = request.nda_path

    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="MinIO bucket name is not configured")

    # Retrieve files from MinIO
    try:
        # Fetch sue_letter
        sue_letter_data = client.get_object(bucket_name, sue_letter_path)
        sue_letter_bytes = BytesIO(sue_letter_data.read())
        sue_letter_data.close()
        sue_letter_data.release_conn()

        # Fetch NDA
        nda_data = client.get_object(bucket_name, nda_path)
        nda_bytes = BytesIO(nda_data.read())
        nda_data.close()
        nda_data.release_conn()
    except S3Error as err:
        logger.error(f"MinIO S3Error: {str(err)}")
        raise HTTPException(status_code=404, detail=f"File not found in MinIO: {str(err)}")
    except Exception as e:
        logger.error(f"Error retrieving files from MinIO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving files from MinIO: {str(e)}")

    # Extract text from PDFs
    sue_letter_text = extract_text_from_pdf_bytes(sue_letter_bytes)
    nda_text = extract_text_from_pdf_bytes(nda_bytes)

    if not sue_letter_text or not nda_text:
        logger.error("Failed to extract text from one or both PDFs")
        raise HTTPException(
            status_code=400, detail="Failed to extract text from one or both PDFs"
        )

    # Analyze documents
    results = analyze_documents(sue_letter_text, nda_text)

    if not results:
        logger.error("No results generated from document analysis")
        raise HTTPException(status_code=500, detail="No results generated")

    return JSONResponse(content=results)
