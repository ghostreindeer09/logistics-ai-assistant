"""
Logistics AI Assistant — FastAPI Backend
Endpoints: POST /upload, POST /ask, POST /extract
"""

import os
import shutil
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from .models import AskRequest, ExtractRequest, UploadResponse, AskResponse, ExtractResponse
from .document_processor import process_and_store, document_exists, UPLOAD_DIR
from .retriever import answer_question
from .extractor import extract_structured_data

load_dotenv()

# ── App Init ────────────────────────────────────────────────────────

app = FastAPI(
    title="Logistics AI Assistant",
    description="RAG-powered AI assistant for logistics document analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K = int(os.getenv("TOP_K_RESULTS", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── Serve Frontend ──────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Logistics AI Assistant API", "docs": "/docs"}


# Mount static files for frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── Health Check ────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": OPENAI_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
    }


# ── POST /upload ────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a logistics document (PDF, DOCX, or TXT).
    The document will be parsed, chunked, embedded, and stored in the vector index.
    """
    # Validate file extension
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save file to disk
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Process and store
    try:
        doc_id, num_chunks = process_and_store(
            file_path=file_path,
            filename=filename,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            embedding_model=EMBEDDING_MODEL,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    return UploadResponse(
        document_id=doc_id,
        filename=filename,
        num_chunks=num_chunks,
        message=f"Document '{filename}' processed successfully: {num_chunks} chunks created.",
    )


# ── POST /ask ───────────────────────────────────────────────────────

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a natural language question about an uploaded document.
    Returns the answer, supporting sources, and confidence score.
    """
    if not document_exists(request.document_id):
        raise HTTPException(
            status_code=404,
            detail=f"Document '{request.document_id}' not found. Please upload first.",
        )

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response = answer_question(
            doc_id=request.document_id,
            question=request.question,
            top_k=TOP_K,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            model=OPENAI_MODEL,
            embedding_model=EMBEDDING_MODEL,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ── POST /extract ───────────────────────────────────────────────────

@app.post("/extract", response_model=ExtractResponse)
async def extract_data(request: ExtractRequest):
    """
    Extract structured shipment data from an uploaded document.
    Returns JSON with logistics fields (nulls for missing values).
    """
    if not document_exists(request.document_id):
        raise HTTPException(
            status_code=404,
            detail=f"Document '{request.document_id}' not found. Please upload first.",
        )

    try:
        response = extract_structured_data(
            doc_id=request.document_id,
            model=OPENAI_MODEL,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")


# ── Run Server ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"🚛 Logistics AI Assistant starting on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=True)
