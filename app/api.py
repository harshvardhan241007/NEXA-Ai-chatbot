"""
FastAPI backend for NEXA AI Chatbot.

Endpoints:
  GET  /                     -> serves the web chat UI
  POST /api/auth/signup      -> create an account, get a token back
  POST /api/auth/login       -> log in, get a token back
  POST /api/auth/logout      -> invalidate the current token
  GET  /api/auth/me          -> who am I (based on the bearer token)
  POST /api/chat             -> send a message, get a reply (auth required)
  POST /api/upload           -> upload a .txt/.pdf for RAG Q&A (auth required)
  GET  /api/history/{sid}    -> fetch conversation history (auth required)
  GET  /api/health           -> simple health check

Run with:  uvicorn app.api:app --reload
"""

import os
import shutil
import uuid

from fastapi import Depends, FastAPI, Header, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import auth
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


class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str


# ---- auth dependency --------------------------------------------------------

def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """Reads `Authorization: Bearer <token>`, returns {user_id, username}."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    user = auth.get_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Please log in to continue.")
    return user


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


# ---- auth endpoints ----------------------------------------------------------

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        result = auth.signup(req.username, req.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthResponse(token=result["token"], username=result["username"])


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        result = auth.login(req.username, req.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthResponse(token=result["token"], username=result["username"])


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        auth.logout(authorization.split(" ", 1)[1].strip())
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "username": user["username"]}


# ---- chat endpoints (all require a logged-in user) ---------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        session_id = req.session_id or bot.start_session(user["username"], user_id=user["user_id"])
        # make sure the session row exists even if a client-supplied id is reused,
        # and that it belongs to this user
        owner_id = bot.memory.get_session_owner(session_id)
        if owner_id is not None and owner_id != user["user_id"]:
            raise HTTPException(status_code=403, detail="This session belongs to another account.")
        bot.start_session(user["username"], session_id=session_id, user_id=user["user_id"])
        reply = bot.handle_message(session_id, user["username"], req.message)
        return ChatResponse(session_id=session_id, reply=reply)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/upload")
async def upload(session_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    owner_id = bot.memory.get_session_owner(session_id)
    if owner_id is not None and owner_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="This session belongs to another account.")

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
def history(session_id: str, user: dict = Depends(get_current_user)):
    owner_id = bot.memory.get_session_owner(session_id)
    if owner_id is not None and owner_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="This session belongs to another account.")
    return {"session_id": session_id, "history": bot.memory.get_history(session_id, limit=100)}
