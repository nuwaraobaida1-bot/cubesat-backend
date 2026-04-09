import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyPDF2 import PdfReader
from docx import Document
from google import genai
from google.genai import types


load_dotenv()

app = FastAPI(
    title="Document Question Answering API",
    description="Upload PDF or DOCX files, ask questions, and get Gemini answers based only on the document.",
    version="1.0.0",
)


UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

if CORS_ORIGINS.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


document_store: Dict[str, Dict[str, str]] = {}


class AskRequest(BaseModel):
    document_id: str
    question: str


class SummaryRequest(BaseModel):
    document_id: str


def get_gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing. Add it to your .env file before using /ask or /summary.",
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def extract_text_from_docx(file_path: Path) -> str:
    document = Document(str(file_path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs).strip()


def extract_text(file_path: Path, content_type: str) -> str:
    if content_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)

    docx_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    }
    if content_type in docx_types or file_path.suffix.lower() == ".docx":
        return extract_text_from_docx(file_path)

    raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def build_answer_prompt(document_text: str, question: str) -> str:
    return f"""
You are answering questions using only the uploaded document.

Rules:
1. Answer only from the document text below.
2. If the answer is not clearly in the document, say: "I could not find that information in the uploaded document."
3. Keep the answer clear and direct.
4. Do not add outside knowledge.

Document text:
\"\"\"
{document_text}
\"\"\"

User question:
{question}
""".strip()


def build_summary_prompt(document_text: str) -> str:
    return f"""
Create a short structured report based only on the document text below.

Use this format:
- Title
- Main purpose
- Key points
- Important findings
- Short conclusion

If a section is missing in the document, write "Not clearly stated".
Do not use outside knowledge.

Document text:
\"\"\"
{document_text}
\"\"\"
""".strip()


def ask_gemini(prompt: str) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=700,
        ),
    )
    if response.text:
        return response.text.strip()
    return "No response was returned by Gemini."


@app.get("/")
def root():
    return {
        "message": "FastAPI backend is running.",
        "available_endpoints": ["/upload", "/ask", "/summary"],
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name was provided.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")

    document_id = str(uuid.uuid4())
    saved_file_path = UPLOAD_DIR / f"{document_id}{file_extension}"

    save_upload_file(file, saved_file_path)

    extracted_text = extract_text(saved_file_path, file.content_type or "")
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Text could not be extracted from this file. Please try another document.",
        )

    document_store[document_id] = {
        "filename": file.filename,
        "file_path": str(saved_file_path),
        "content": extracted_text,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    return {
        "message": "File uploaded and processed successfully.",
        "document_id": document_id,
        "filename": file.filename,
        "characters_extracted": len(extracted_text),
        "preview": extracted_text[:500],
    }


@app.post("/ask")
def ask_question(request: AskRequest):
    document = document_store.get(request.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found. Please upload a file first.")

    prompt = build_answer_prompt(document["content"], request.question)
    answer = ask_gemini(prompt)

    return {
        "document_id": request.document_id,
        "question": request.question,
        "answer": answer,
    }


@app.post("/summary")
def generate_summary(request: SummaryRequest):
    document = document_store.get(request.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found. Please upload a file first.")

    prompt = build_summary_prompt(document["content"])
    summary = ask_gemini(prompt)

    return {
        "document_id": request.document_id,
        "filename": document["filename"],
        "summary": summary,
    }
