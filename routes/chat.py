from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Tuple
from io import BytesIO
import re
import os
from dotenv import load_dotenv
import PyPDF2
from openai import OpenAI

chat_router = APIRouter()

load_dotenv()

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it before running the script.")
    return api_key

client = OpenAI(api_key=get_openai_api_key())

def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    try:
        pdf_data = BytesIO(pdf_file.file.read())
        reader = PyPDF2.PdfReader(pdf_data)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_file.filename}: {str(e)}")
        return ""

def extract_sections_from_sue_letter(sue_letter: str) -> List[str]:
    section_pattern = r"Section\s+(\d+)"
    sections = re.findall(section_pattern, sue_letter)
    return sections

def extract_section_from_nda(nda: str, section_number: str) -> str:
    section_pattern = rf"Section\s+{section_number}[\s\S]+?(?=Section|\Z)"
    match = re.search(section_pattern, nda)
    if match:
        return match.group(0)
    return ""

def match_with_ipc(section_content: str) -> str:
    prompt = f"Given the following section from an NDA, identify the most relevant section(s) of the Indian Penal Code (IPC) that could be applicable. Provide the IPC section number(s) and a brief explanation of why it's relevant: NDA Section: {section_content} Relevant IPC Section(s):"
    try:
        response = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in OpenAI API call: {str(e)}")
        return ""

def analyze_documents(sue_letter: str, nda: str) -> Dict[str, List[Tuple[str, str]]]:
    results = {}
    sections = extract_sections_from_sue_letter(sue_letter)
    for section in sections:
        nda_section = extract_section_from_nda(nda, section)
        if nda_section:
            ipc_match = match_with_ipc(nda_section)
            cleaned_nda_section = nda_section.replace('\n', ' ')
            cleaned_ipc_match = ipc_match.replace('\n', ' ')
            results[section] = [("NDA Content", cleaned_nda_section), ("IPC Match", cleaned_ipc_match)]
    return results

@chat_router.post("/analyze-documents")
async def analyze_documents_endpoint(
    sue_letter: UploadFile = File(...), nda: UploadFile = File(...)
):
    sue_letter_text = extract_text_from_pdf(sue_letter)
    nda_text = extract_text_from_pdf(nda)

    if not sue_letter_text or not nda_text:
        raise HTTPException(
            status_code=400, detail="Failed to extract text from one or both PDFs"
        )

    results = analyze_documents(sue_letter_text, nda_text)

    if not results:
        raise HTTPException(status_code=500, detail="No results generated")

    return JSONResponse(content=results)
