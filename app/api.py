"""
FastAPI backend for NEXA AI Chatbot.

Endpoints:
  GET  /                     -> serves the web chat UI
  POST /api/chat             -> send a message, get a reply
  POST /api/upload           -> upload a .txt/.pdf for RAG Q&A
  GET  /api/history/{sid}    -> fetch conversation history
  GET  /api/health           -> simple health check

Run with:  uvicorn app.api:app --reload
"""

import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .chatbot import NexaChatbot
from .file_reader import load_document, UnsupportedFileType
from .config import settings
from .logger import get_logger

log = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title=settings.APP_NAME, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = NexaChatbot()

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    user_name: str = "Friend"
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@app.get("/")
def serve_ui():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="UI not found")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "llm_configured": settings.has_llm_key,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session_id = req.session_id or bot.start_session(req.user_name)
        # make sure the session row exists even if a client-supplied id is reused
        bot.start_session(req.user_name, session_id=session_id)
        reply = bot.handle_message(session_id, req.user_name, req.message)
        return ChatResponse(session_id=session_id, reply=reply)
    except Exception as exc:  # noqa: BLE001
        log.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/upload")
async def upload(session_id: str, file: UploadFile = File(...)):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".txt", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")

    dest_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        text = load_document(dest_path)
        n_chunks = bot.load_document(session_id, text)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"session_id": session_id, "chunks_indexed": n_chunks, "filename": file.filename}


@app.get("/api/history/{session_id}")
def history(session_id: str):
    return {"session_id": session_id, "history": bot.memory.get_history(session_id, limit=100)}
