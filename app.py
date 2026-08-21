import os
import json
import uuid
import shutil
import re
import html
import threading
import secrets
from datetime import datetime
from urllib.parse import unquote, quote
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, Response, RedirectResponse
import base64
import httpx
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Setup Security Audit Logger
security_logger = logging.getLogger("security")

def log_security_event(event_type: str, user_target: str, details: dict):
    """Log security and privacy audit events."""
    try:
        security_logger.warning(f"[SECURITY_AUDIT][{event_type}] Target: {user_target} | Details: {json.dumps(details)}")
    except Exception:
        print(f"[SECURITY_AUDIT][{event_type}] Target: {user_target} | Details: {details}")

def detect_cheating_attempt(session_id: int, user_email: str, time_taken: int) -> bool:
    """Detect automated scripting or unnatural cheating patterns during adaptive practice."""
    if time_taken < 2:
        log_security_event("FAST_ANSWER_ANOMALY", user_email or "anonymous", {
            "session_id": session_id,
            "time_taken": time_taken,
            "alert": "Response submitted in under 2 seconds"
        })
        return True
    return False

# Import LangGraph workflow and config
from backend_rag import workflow, active_streams
from rag import add_pdf_to_vectordb
from paths import UPLOADS_DIR
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="BU Prepz AI Workspace", description="Academic Intelligence & Exam Preparation Platform")

from auth.routes import router as auth_router
app.include_router(auth_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Access-Token"
    response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    # Allow Firebase auth iframe (prepz-workspace.firebaseapp.com) and Google auth domains
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://apis.google.com https://www.gstatic.com "
            "https://cdnjs.cloudflare.com https://accounts.google.com; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://youtube.com https://*.youtube.com "
            "https://prepz-workspace.firebaseapp.com https://accounts.google.com https://www.gstatic.com; "
        "connect-src 'self' https://www.googleapis.com https://accounts.google.com "
            "https://api.dicebear.com https://*.firebaseio.com "
            "https://identitytoolkit.googleapis.com https://securetoken.googleapis.com "
            "https://www.gstatic.com https://prepz-workspace.firebaseapp.com; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' https: blob: data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "frame-ancestors *;"
    )
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "BU Prepz AI Workspace", "timestamp": datetime.utcnow().isoformat()}

# ── Firebase Auth Proxy ────────────────────────────────────────────────────────
# HF Spaces CSP only allows frame-src 'self'. Firebase auth iframe normally
# loads from prepz-workspace.firebaseapp.com (blocked). By proxying /__/auth/*
# from our own hf.space origin, the iframe becomes same-origin → CSP allows it.
FIREBASE_AUTH_ORIGIN = "https://prepz-workspace.firebaseapp.com"

@app.api_route("/__/auth/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def firebase_auth_proxy(path: str, request: Request):
    upstream = f"{FIREBASE_AUTH_ORIGIN}/__/auth/{path}"
    qs = str(request.url.query)
    if qs:
        upstream += "?" + qs
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            if request.method == "GET":
                resp = await client.get(upstream, headers={"Accept": "*/*"})
            else:
                body = await request.body()
                resp = await client.post(upstream, content=body,
                                         headers={"Content-Type": request.headers.get("content-type", "")})
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "text/html"),
            headers={"Cache-Control": "no-store", "Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return Response(content=f"Proxy error: {e}", status_code=502)
# ────────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    thread_id: str
    user_email: Optional[str] = None

import hmac
import hashlib
import base64
import time

SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SESSION_SECRET") or "prepz_super_secret_cryptographic_key_2026_x89q"

def generate_signed_token(payload_data: dict, exp_seconds: int = 86400) -> str:
    payload = payload_data.copy()
    payload["exp"] = int(time.time()) + exp_seconds
    payload["jti"] = str(uuid.uuid4())
    
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    
    signature = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"

def verify_signed_token(token: str) -> Optional[dict]:
    if not token or "." not in token:
        return None
    try:
        parts = token.strip().split(".")
        if len(parts) != 2:
            return None
        b64_payload, signature = parts[0], parts[1]
        
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None
        
        padding = "=" * (-len(b64_payload) % 4)
        payload_json = base64.urlsafe_b64decode(b64_payload + padding).decode("utf-8")
        payload = json.loads(payload_json)
        
        if payload.get("exp") and payload["exp"] < time.time():
            return None
            
        return payload
    except Exception:
        return None

def get_current_user_payload(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Access-Token") or request.cookies.get("session_token")
    if token:
        return verify_signed_token(token)
    return None

def serialize_message(msg):
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    elif isinstance(msg, AIMessage):
        # Only return AIMessages that have content (skipping tool-call triggers)
        if msg.content:
            return {"role": "assistant", "content": msg.content}
    return None

from collections import defaultdict

# Sliding window IP & route rate limiter
RATE_LIMIT_WINDOWS = defaultdict(list)

def check_ip_rate_limit(client_ip: str, endpoint_key: str, max_requests: int, window_seconds: int = 60) -> bool:
    now = time.time()
    key = f"{client_ip}:{endpoint_key}"
    history = RATE_LIMIT_WINDOWS[key]
    
    # Prune expired timestamps outside the sliding window
    cutoff = now - window_seconds
    RATE_LIMIT_WINDOWS[key] = [t for t in history if t > cutoff]
    
    if len(RATE_LIMIT_WINDOWS[key]) >= max_requests:
        return False
        
    RATE_LIMIT_WINDOWS[key].append(now)
    return True

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)
    path = request.url.path
    
    if path == "/chat" and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "chat", max_requests=60, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"error": "Rate limit exceeded. Maximum 60 chat queries per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path == "/upload" and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "upload", max_requests=25, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded. Maximum 25 file uploads per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path.startswith("/api/login") and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "login", max_requests=30, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded. Please wait a minute before trying again."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path.startswith("/api/practice/generate"):
        if not check_ip_rate_limit(client_ip, "practice_gen", max_requests=50, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded. Maximum 50 adaptive practice generations per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )

    elif path.startswith("/api/practice/") and "/answer" in path and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "practice_ans", max_requests=120, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded."}).encode()]),
                status_code=429,
                media_type="application/json"
            )

    elif path.startswith("/api/") and not path.startswith("/api/analytics/heartbeat") and not check_ip_rate_limit(client_ip, "api_general", max_requests=300, window_seconds=60):
        return StreamingResponse(
            iter([json.dumps({"detail": "Too many requests. Please slow down."}).encode()]),
            status_code=429,
            media_type="application/json"
        )
        
    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Request body payload size limit check (15MB Max)
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 15 * 1024 * 1024:
        return StreamingResponse(
            iter([json.dumps({"detail": "Payload too large. Request body exceeds 15MB limit."}).encode()]),
            status_code=413,
            media_type="application/json"
        )

    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval' https://*.hf.space https://huggingface.co; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://apis.google.com https://accounts.google.com https://www.gstatic.com https://cdnjs.cloudflare.com; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://youtube.com https://*.youtube.com https://prepz-workspace.firebaseapp.com https://accounts.google.com https://www.gstatic.com https://*.hf.space https://huggingface.co; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' https: blob: data:; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' https: wss:; "
        "frame-ancestors 'self' https://huggingface.co https://*.hf.space *;"
    )
    return response

class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers):
        return False
        
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Serve static frontend folder
os.makedirs("static", exist_ok=True)
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0"
}

@app.get("/")
@app.get("/index.html")
def read_root():
    return FileResponse("static/index.html", headers=NO_CACHE_HEADERS)

@app.get("/style.css")
def read_style():
    return FileResponse("static/style.css", headers=NO_CACHE_HEADERS)

@app.get("/app.js")
def read_app_js():
    return FileResponse("static/app.js", headers=NO_CACHE_HEADERS)

@app.get("/om_avatar.png")
def read_om_avatar():
    return FileResponse("static/om_avatar.png")

@app.get("/om_face_avatar.png")
def read_om_face_avatar():
    return FileResponse("static/om_face_avatar.png")

@app.get("/favicon.ico")
def read_favicon_ico():
    return FileResponse("static/favicon.ico")

@app.get("/favicon.png")
@app.get("/favicon-32x32.png")
def read_favicon_png():
    return FileResponse("static/favicon.png")

@app.get("/favicon.svg")
def read_favicon_svg():
    return FileResponse("static/favicon.svg")

class PinRequest(BaseModel):
    is_pinned: bool

class ArchiveRequest(BaseModel):
    is_archived: bool

@app.get("/threads")
def get_threads():
    try:
        from backend_rag import retrieve_all_threads_metadata
        threads = retrieve_all_threads_metadata()
        threads_data = []
        for t in threads:
            tid = t["thread_id"]
            is_pinned = t["is_pinned"]
            title = "New Chat"
            try:
                config = {"configurable": {"thread_id": tid}}
                state = workflow.get_state(config)
                if state.values and "messages" in state.values:
                    for msg in state.values["messages"]:
                        if msg.type == "human" or (hasattr(msg, "role") and msg.role == "user"):
                            content = msg.content
                            if len(content) > 35:
                                title = content[:32] + "..."
                            else:
                                title = content
                            break
            except Exception:
                pass
            threads_data.append({"thread_id": tid, "title": title, "is_pinned": is_pinned})
        return {"threads": threads_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thread/{thread_id}/metadata")
def get_metadata(thread_id: str):
    try:
        from backend_rag import get_thread_metadata
        return get_thread_metadata(thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/thread/{thread_id}")
def delete_thread_route(thread_id: str):
    try:
        from backend_rag import delete_thread_from_db
        delete_thread_from_db(thread_id)
        return {"status": "success", "message": f"Thread {thread_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/thread/{thread_id}/pin")
def pin_thread_route(thread_id: str, req: PinRequest):
    try:
        from backend_rag import set_thread_metadata
        set_thread_metadata(thread_id, is_pinned=req.is_pinned)
        return {"status": "success", "message": f"Thread {thread_id} pin state set to {req.is_pinned}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/thread/{thread_id}/archive")
def archive_thread_route(thread_id: str, req: ArchiveRequest):
    try:
        from backend_rag import set_thread_metadata
        set_thread_metadata(thread_id, is_archived=req.is_archived)
        return {"status": "success", "message": f"Thread {thread_id} archive state set to {req.is_archived}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thread/{thread_id}/history")
def get_thread_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = workflow.get_state(config)
        messages = []
        if state.values and "messages" in state.values:
            for msg in state.values["messages"]:
                serialized = serialize_message(msg)
                if serialized:
                    messages.append(serialized)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from langchain_core.callbacks import BaseCallbackHandler
from fastapi.concurrency import run_in_threadpool
import asyncio

class QueueCallbackHandler(BaseCallbackHandler):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop
        self.in_tool_call = False
        self.tokens_streamed = 0

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        self.in_tool_call = False

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        self.in_tool_call = False
        tool_name = serialized.get("name", "tool") if serialized else "tool"
        display_name = "Reading uploaded documents..." if "rag" in tool_name else ("Searching Wikipedia..." if "wiki" in tool_name else f"Executing {tool_name}...")
        self.loop.call_soon_threadsafe(self.queue.put_nowait, f"__STATUS__:{display_name}")

    def on_llm_new_token(self, token: str, chunk=None, **kwargs) -> None:
        if not token:
            return
        if chunk is not None:
            msg = getattr(chunk, "message", chunk)
            tool_chunks = getattr(msg, "tool_call_chunks", None)
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_chunks or tool_calls:
                self.in_tool_call = True
                return
            else:
                self.in_tool_call = False
        if self.in_tool_call:
            return
        self.tokens_streamed += 1
        self.loop.call_soon_threadsafe(self.queue.put_nowait, token)

    def clear_queue(self) -> None:
        self.in_tool_call = False
        self.tokens_streamed = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break

class ApiChatRequest(BaseModel):
    message: str
    subject: Optional[str] = "General"
    topic: Optional[str] = None
    mode: Optional[str] = "exam"
    user_id: Optional[int] = 1
    university_id: Optional[int] = 1
    session_id: Optional[str] = None
    user_email: Optional[str] = None

class RatePlaylistRequest(BaseModel):
    user_id: Optional[int] = 1
    rating: int
    was_helpful: bool
    watched_percentage: Optional[int] = 30

class ConceptPracticeRequest(BaseModel):
    concept: str = Field(..., min_length=1, max_length=200)
    difficulty: Optional[str] = "easy"
    user_id: Optional[int] = 1
    user_email: Optional[str] = None
    
    @validator("concept")
    def validate_concept_safety(cls, v):
        if not v or not v.strip():
            raise ValueError("Concept name cannot be empty")
        v_clean = v.strip()
        dangerous_patterns = [";", "--", "/*", "*/", "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE "]
        for pattern in dangerous_patterns:
            if pattern.lower() in v_clean.lower():
                raise ValueError("Invalid concept name characters detected")
        return html.escape(v_clean)
    
    @validator("difficulty")
    def validate_difficulty_enum(cls, v):
        allowed = {"easy", "medium", "hard"}
        v_clean = (v or "easy").strip().lower()
        if v_clean not in allowed:
            raise ValueError(f"Difficulty must be one of: {sorted(list(allowed))}")
        return v_clean

class PracticeAnswerRequest(BaseModel):
    question_id: int
    user_answer: str = Field(..., min_length=1, max_length=5000)
    time_taken: Optional[int] = 15
    user_id: Optional[int] = 1
    user_email: Optional[str] = None

    @validator("time_taken")
    def validate_time_taken(cls, v):
        if v is None:
            return 15
        if v < 0 or v > 3600:
            raise ValueError("Time taken must be between 0 and 3600 seconds")
        return v

    @validator("user_answer")
    def sanitize_user_answer(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Answer cannot be empty")
        v_str = str(v)
        # Strip script tags and HTML escape
        v_clean = re.sub(r'<script[^>]*>.*?</script>', '', v_str, flags=re.IGNORECASE)
        return html.escape(v_clean.strip())

@app.post("/chat")
async def chat_stream(request: ChatRequest):
    if request.user_email:
        add_contribution_points(request.user_email, 1)
        update_user_activity(request.user_email)

    thread_id = request.thread_id or "default_thread"
    config = {"configurable": {"thread_id": thread_id}}

    detected_topic = "general"
    topic_attempts = 0
    intent_result = {
        "should_recommend_videos": False,
        "recommendation_strength": "none",
        "intent": "initial",
        "explanation_style": "normal",
        "reason": ""
    }
    history = []

    # Keep HumanMessage pure without prepending leaking system notes
    state = {"messages": [HumanMessage(content=request.query)]}

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    handler = QueueCallbackHandler(queue, loop)

    # Store handler in registry mapped to thread ID
    active_streams[thread_id] = handler

    accumulated_ai_response = []

    async def run_workflow():
        try:
            try:
                res = await asyncio.wait_for(
                    run_in_threadpool(workflow.invoke, state, config=config),
                    timeout=60
                )
            except asyncio.TimeoutError:
                raise Exception("The AI took too long to respond. Please try again — this usually means the Groq API is slow or unreachable right now.")

            # Save message & update context
            try:
                ai_text = ""
                if res and "messages" in res and res["messages"]:
                    last_msg = res["messages"][-1]
                    if hasattr(last_msg, "content") and last_msg.content:
                        ai_text = str(last_msg.content)

                # Guaranteed token delivery fallback if callback stream produced 0 tokens:
                if ai_text and handler and getattr(handler, "tokens_streamed", 0) == 0:
                    print(f"[STREAM FALLBACK] Delivering {len(ai_text)} chars from final workflow response")
                    chunks = re.findall(r'\S+\s*|\s+', ai_text)
                    for ch in chunks:
                        await queue.put(ch)
                
                update_conversation_context_record(
                    session_id=thread_id,
                    user_message=request.query,
                    ai_message=ai_text[:500],
                    topic=detected_topic,
                    topic_attempts=topic_attempts + 1,
                    intent=intent_result.get("intent", "initial"),
                    strength=intent_result.get("recommendation_strength", "none")
                )
            except Exception as dbe:
                print(f"[CONTEXT DB UPDATE ERROR] {dbe}")

            # ── Detect Concept Weakness (Academic Edge) ──
            try:
                weakness_det = detect_concept_weakness(
                    user_id=1,
                    user_email=request.user_email or "",
                    topic=detected_topic,
                    message=request.query,
                    attempt_number=topic_attempts,
                    conversation_history=history
                )
                if weakness_det.get("weakness_detected"):
                    record_concept_weakness(
                        user_id=1,
                        user_email=request.user_email or "",
                        subject=weakness_det.get("subject", "General"),
                        concept_name=weakness_det.get("confused_concept", detected_topic),
                        topic=detected_topic,
                        dependent_topics=weakness_det.get("related_topics", []),
                        is_foundational=weakness_det.get("is_foundational", False),
                        is_critical=weakness_det.get("is_foundational", False) or topic_attempts >= 2
                    )
                    weakness_payload = json.dumps({
                        "detected": True,
                        "concept": weakness_det.get("confused_concept", detected_topic),
                        "subject": weakness_det.get("subject", "General"),
                        "is_foundational": weakness_det.get("is_foundational", False),
                        "related_topics": weakness_det.get("related_topics", []),
                        "impact_score": weakness_det.get("impact_score", 50.0),
                        "message": f"Academic Edge Alert: You seem stuck on '{weakness_det.get('confused_concept')}'. This foundational concept affects {len(weakness_det.get('related_topics', []))} topics. Master it now with targeted adaptive practice!"
                    })
                    print(f"[STREAM EMIT CONCEPT_WEAKNESS] {weakness_payload[:120]}...")
                    await queue.put(f"__CONCEPT_WEAKNESS__:{weakness_payload}")
            except Exception as cwe:
                print(f"[CONCEPT WEAKNESS DETECT ERROR] {cwe}")

            # Emit video recommendation if needed
            print(f"[STREAM] Checking video rec: should={intent_result.get('should_recommend_videos')} strength={intent_result.get('recommendation_strength')} topic='{detected_topic}'")
            if intent_result.get("should_recommend_videos"):
                videos = get_recommended_videos(
                    subject="",
                    topic=detected_topic,
                    difficulty_level=intent_result.get("video_difficulty", "Beginner"),
                    mode="exam",
                    limit=4
                )
                strength = intent_result.get("recommendation_strength", "medium")
                if strength == "urgent":
                    rec_msg = "🚨 I see you're really struggling with this.\n\nLet me show you the BEST videos recommended by Bennett students:"
                elif strength == "medium":
                    rec_msg = "📺 Recommended videos for this topic:"
                else:
                    rec_msg = "Optional: Here are helpful video resources:"

                rec_payload = json.dumps({
                    "topic": detected_topic.title(),
                    "strength": strength,
                    "attempt_number": topic_attempts + 1,
                    "intent_reason": intent_result.get("reason", ""),
                    "recommendation_message": rec_msg,
                    "next_action": get_next_action_message(strength, topic_attempts + 1),
                    "videos": videos
                })
                print(f"[STREAM EMIT VIDEO_REC] {rec_payload[:120]}...")
                await queue.put(f"__VIDEO_REC__:{rec_payload}")
        except Exception as e:
            print(f"[RUN_WORKFLOW ERROR] {e}")
            await queue.put(f"__ERROR__:{str(e)}")
        finally:
            active_streams.pop(thread_id, None)
            await queue.put(None)

    asyncio.create_task(run_workflow())

    async def response_generator():
        while True:
            token = await queue.get()
            if token is None:
                break
            if isinstance(token, str) and token.startswith("__ERROR__:"):
                err_msg = token[len("__ERROR__:"):]
                yield f"data: {json.dumps({'error': err_msg})}\n\n"
                break
            elif isinstance(token, str) and token.startswith("__STATUS__:"):
                status_msg = token[len("__STATUS__:"):]
                yield f"data: {json.dumps({'status': status_msg})}\n\n"
            elif isinstance(token, str) and token.startswith("__CONCEPT_WEAKNESS__:"):
                w_json = token[len("__CONCEPT_WEAKNESS__:"):]
                yield f"data: {json.dumps({'concept_weakness': json.loads(w_json)})}\n\n"
            elif isinstance(token, str) and token.startswith("__VIDEO_REC__:"):
                rec_json = token[len("__VIDEO_REC__:"):]
                yield f"data: {json.dumps({'video_rec': json.loads(rec_json)})}\n\n"
            else:
                yield f"data: {json.dumps({'text': token})}\n\n"

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(response_generator(), headers=headers, media_type="text/event-stream")

# ── Part 3: JSON Smart Chat Endpoint (/api/chat) ──────────────────────────────
@app.post("/api/chat")
async def exam_chat_api(request: ApiChatRequest):
    """
    Smart chat endpoint with intent understanding, adaptive prompts, and Bennett University recommendations
    """
    try:
        session_id = request.session_id or f"session_{secrets.token_hex(8)}"
        conv = get_or_create_conversation(user_id=request.user_id or 1, session_id=session_id, subject=request.subject or "General")
        history = conv.get("messages", [])
        
        last_topic = conv.get("topics_discussed", [""])[-1] if conv.get("topics_discussed") else ""
        topic = request.topic or extract_topic_from_query(request.message, last_topic=last_topic)
        topic_attempts = conv.get("topic_attempts", {}).get(topic, 0)

        # Intent analysis
        intent_analysis = analyze_user_intent(
            current_message=request.message,
            conversation_history=history,
            topic=topic,
            topic_attempts=topic_attempts
        )

        # Generate explanation
        style = intent_analysis.get("explanation_style", "normal")
        prompt_instruction = ""
        if style == "basic":
            prompt_instruction = f"VERY BASIC explanation of {topic}. Use only simple everyday words. Real-world example. No technical jargon at all. Step by step."
        elif style == "simpler":
            prompt_instruction = f"Simplify explanation of {topic}. Use everyday examples. Break into tiny steps."
        elif style == "detailed":
            prompt_instruction = f"Explain {topic} from a DIFFERENT angle. Use analogies. Keep simple and clear."
        else:
            prompt_instruction = f"Explain {topic} clearly for exam prep. Include examples."

        prompt_text = f"[SYSTEM: {prompt_instruction}] {request.message}"
        config = {"configurable": {"thread_id": session_id}}
        state = {"messages": [HumanMessage(content=prompt_text)]}
        try:
            res = await asyncio.wait_for(
                run_in_threadpool(workflow.invoke, state, config=config),
                timeout=60
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="The AI took too long to respond. Please try again.")
        explanation = str(res["messages"][-1].content) if (res and "messages" in res and res["messages"]) else f"Explanation for {topic}."

        # Video recommendations
        recommended_videos = []
        recommendation_message = ""
        if intent_analysis["should_recommend_videos"]:
            recommended_videos = get_recommended_videos(
                subject=request.subject or "Basic Electrical & Electronics Engineering",
                topic=topic,
                difficulty_level=intent_analysis["video_difficulty"],
                mode=request.mode or "exam",
                limit=4
            )
            strength = intent_analysis["recommendation_strength"]
            if strength == "urgent":
                recommendation_message = "🚨 I see you're really struggling with this.\n\nLet me show you the BEST videos recommended by Bennett students:"
            elif strength == "medium":
                recommendation_message = "📺 Recommended videos for this topic:"
            else:
                recommendation_message = "Optional: Here are helpful videos:"

        # Update conversation context in DB
        update_conversation_context_record(
            session_id=session_id,
            user_message=request.message,
            ai_message=explanation[:500],
            topic=topic,
            topic_attempts=topic_attempts + 1,
            intent=intent_analysis["intent"],
            strength=intent_analysis["recommendation_strength"]
        )

        # Detect Concept Weakness
        concept_weakness_data = None
        try:
            weakness_det = detect_concept_weakness(
                user_id=request.user_id or 1,
                user_email="",
                topic=topic,
                message=request.message,
                attempt_number=topic_attempts,
                conversation_history=history
            )
            if weakness_det.get("weakness_detected"):
                record_concept_weakness(
                    user_id=request.user_id or 1,
                    user_email="",
                    subject=weakness_det.get("subject", request.subject or "General"),
                    concept_name=weakness_det.get("confused_concept", topic),
                    topic=topic,
                    dependent_topics=weakness_det.get("related_topics", []),
                    is_foundational=weakness_det.get("is_foundational", False),
                    is_critical=weakness_det.get("is_foundational", False) or topic_attempts >= 2
                )
                concept_weakness_data = {
                    "detected": True,
                    "concept": weakness_det.get("confused_concept", topic),
                    "subject": weakness_det.get("subject", "General"),
                    "is_foundational": weakness_det.get("is_foundational", False),
                    "related_topics": weakness_det.get("related_topics", []),
                    "impact_score": weakness_det.get("impact_score", 50.0),
                    "message": f"Academic Edge Alert: I noticed you're stuck on '{weakness_det.get('confused_concept')}'. This concept affects {len(weakness_det.get('related_topics', []))} topics. Let's do targeted adaptive practice to master it!",
                    "offer_practice": True,
                    "practice_link": f"/api/practice/generate?concept={weakness_det.get('confused_concept')}&user_id={request.user_id or 1}"
                }
        except Exception as cwe:
            print(f"[API CHAT CONCEPT WEAKNESS ERROR] {cwe}")

        res_payload = {
            "status": "success",
            "explanation": explanation,
            "intent": intent_analysis["intent"],
            "intent_reason": intent_analysis["reason"],
            "attempt_number": topic_attempts + 1,
            "should_recommend_videos": intent_analysis["should_recommend_videos"],
            "recommendation_strength": intent_analysis["recommendation_strength"],
            "recommendation_message": recommendation_message,
            "recommended_videos": recommended_videos,
            "session_id": session_id,
            "next_action": get_next_action_message(intent_analysis["recommendation_strength"], topic_attempts + 1)
        }
        if concept_weakness_data:
            res_payload["concept_weakness"] = concept_weakness_data

        if request.user_email and request.user_email != "anonymous@college.edu":
            add_contribution_points(request.user_email, 2)
            update_user_activity(request.user_email)

        return res_payload
    except Exception as e:
        print(f"[API CHAT ERROR] {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# ── Part 4: Video Rating Endpoint (/api/videos/{playlist_id}/rate) ────────────
@app.post("/api/videos/{playlist_id}/rate")
async def rate_playlist_endpoint(playlist_id: int, request: RatePlaylistRequest):
    """
    Record user rating for a playlist
    """
    try:
        res = rate_playlist_record(
            playlist_id=playlist_id,
            user_id=request.user_id or 1,
            rating=request.rating,
            was_helpful=request.was_helpful,
            watched_percentage=request.watched_percentage or 30
        )
        return {
            "status": "success",
            "message": "Thanks for rating! This helps other Bennett students.",
            "playlist_score": res.get("avg_rating", 4.5)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _reindex_all_uploads_sync():
    """Every restart starts with an empty chroma_db/ (it's gitignored, no persistent volume).
    Uploaded file bytes + their DB records get restored from the committed JSON bundle
    (see database.py's _restore_uploads_from_backup), but that restore never re-embeds
    them into the vector store -- so previously-uploaded documents show up in the file
    lists yet RAG search finds nothing for them until someone re-uploads. Re-index
    every known upload on boot; add_file_to_vectordb already skips anything whose
    `source` path is already present in the collection, so this is safe to re-run."""
    try:
        uploads = get_file_uploads_metadata()
        indexed = 0
        for meta in uploads.values():
            fp = meta.get("file_path")
            if not fp or not os.path.exists(fp):
                continue
            try:
                add_pdf_to_vectordb(
                    fp,
                    user_email=meta.get("user_email") or "anonymous@college.edu",
                    user_name=meta.get("user_name") or "Anonymous",
                    subject=meta.get("subject") or "General Engineering",
                    semester=meta.get("semester") or "Semester 1",
                    file_type=meta.get("file_type") or "Notes"
                )
                indexed += 1
            except Exception as fe:
                print(f"[STARTUP REINDEX] Failed to index {fp}: {fe}")
        print(f"[STARTUP] Vector store re-index check complete ({indexed} upload(s) verified/indexed).")
    except Exception as e:
        print(f"[STARTUP REINDEX NOTICE] {e}")

@app.on_event("startup")
async def startup_event():
    try:
        from database import seed_bennett_channels_if_needed
        seed_bennett_channels_if_needed()
        print("[STARTUP] Real user system and Bennett verified channels initialized successfully.")
    except Exception as e:
        print(f"[STARTUP NOTICE] {e}")

    # Run in the background so re-indexing a large document library doesn't delay
    # the app becoming ready to serve requests.
    asyncio.create_task(run_in_threadpool(_reindex_all_uploads_sync))

# ── Part 5: Seed Channels Endpoint (/api/admin/seed-channels) ─────────────────
@app.post("/api/admin/seed-channels")
async def seed_channels_endpoint(admin_token: Optional[str] = None):
    """Populate database with Bennett University recommended channels"""
    try:
        seed_bennett_channels_if_needed()
        return {"status": "success", "message": f"Seeded {len(BENNETT_CHANNELS)} Bennett University channels."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class HeartbeatRequest(BaseModel):
    session_id: Optional[str] = None
    user_email: str
    user_name: Optional[str] = ""

@app.post("/api/analytics/heartbeat")
async def record_heartbeat_endpoint(req: HeartbeatRequest, request: Request):
    """Receive periodic client heartbeat and compute active screen engagement / dwell time."""
    ip = request.client.host if request.client else ""
    return record_session_heartbeat(
        user_email=req.user_email,
        user_name=req.user_name or "",
        session_id=req.session_id or "",
        ip_address=ip
    )

@app.get("/api/admin/dashboard")
async def get_admin_dashboard_endpoint(admin_email: str):
    """Retrieve full creator / super-admin platform intelligence dashboard."""
    if not is_admin_user(admin_email):
        raise HTTPException(status_code=403, detail="Unauthorized Access. Only verified creator/admins can view this dashboard.")
    return get_admin_dashboard_stats(admin_email)

@app.get("/api/admin/user-drilldown")
async def get_admin_user_drilldown_endpoint(admin_email: str, user_email: str):
    """Retrieve individual student activity timeline, sessions, uploads, and queries."""
    if not is_admin_user(admin_email):
        raise HTTPException(status_code=403, detail="Unauthorized Access.")
    return get_admin_user_drilldown(admin_email, user_email)

@app.get("/api/admin/users")
async def get_admin_users_analytics_endpoint():
    """Retrieve list and total count of all registered / logged in students."""
    try:
        data = get_users_admin_analytics()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Part 6: Concept Weakness Profiler & Adaptive Practice Endpoints ───────────
@app.get("/api/weaknesses/profile")
async def get_weakness_profile_api(request: Request, user_id: int = 1, user_email: Optional[str] = None):
    """Return student's full concept weakness profile with critical gaps and priorities."""
    email = user_email
    user_payload = get_current_user_payload(request)
    if user_payload:
        email = user_payload.get("email") or email
        user_id = user_payload.get("id") or user_id
    elif not email:
        user_token = request.headers.get("X-Access-Token") or request.cookies.get("auth_token")
        if user_token:
            verified = verify_signed_token(user_token)
            if verified:
                email = verified.get("email") or email
                user_id = verified.get("id") or user_id

    profile = create_weakness_profile(user_id=user_id, user_email=email or "")
    log_security_event("WEAKNESS_PROFILE_ACCESSED", email or f"user_{user_id}", {
        "user_id": user_id,
        "total_weaknesses": profile.get("total_weaknesses", 0)
    })
    return profile

class ConceptAnalysisRequest(BaseModel):
    text: str
    subject: Optional[str] = None
    user_email: Optional[str] = None

@app.post("/api/concept-profile/analyze")
async def analyze_concept_endpoint(req: ConceptAnalysisRequest):
    """Deep AI cognitive diagnosis of student queries, confusion root-causes, and remediation roadmap."""
    raw_text = (req.text or "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Please enter a concept, topic, or confusion to analyze.")

    from rag import llm
    import json, re

    prompt = f"""You are a senior Engineering Academic Diagnostic Professor and Cognitive Concept Profiler.
Analyze the following student doubt, topic explanation, confusion, or question with rigorous academic depth:

STUDENT INPUT: "{raw_text}"
OPTIONAL SUBJECT CONTEXT: "{req.subject or 'General Engineering'}"

Perform a deep cognitive diagnostic analysis and output a single JSON object with EXACTLY the following schema:
{{
  "concept_name": "Canonical name of the core engineering concept (e.g. 'Dijkstra Algorithm with Negative Weights', 'Bayes Theorem Posterior Probability', 'Mutex vs Counting Semaphore')",
  "subject": "Engineering Subject category (e.g. 'Data Structures & Algorithms', 'Operating Systems', 'Probability & Statistics', 'BEEE', 'Linear Algebra', 'Digital Design', 'Computer Networks', etc.)",
  "diagnostic_summary": "Crisp 2-3 sentence diagnosis explaining the exact underlying misconception or reason students struggle with this concept.",
  "prerequisites": ["2-3 essential prerequisite concepts the student must master first"],
  "downstream_impact": ["3-4 advanced university syllabus topics that directly depend on mastering this concept"],
  "exam_risk_score": 85,
  "mastery_percentage": 25,
  "is_foundational": true,
  "is_critical": true,
  "remediation_plan": [
    {{"step": "1. Intuition & Visual Mental Model", "action": "Clear actionable explanation to build core intuition."}},
    {{"step": "2. Mathematical / Algorithmic Core", "action": "The core rule, equation, or algorithm invariant to remember."}},
    {{"step": "3. Exam Numerical / Problem Pattern", "action": "Common exam trap and how to solve it."}}
  ],
  "practice_questions": [
    {{
      "question": "A high-yield diagnostic question to test this concept.",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "B) Option 2",
      "explanation": "Why B is correct and why other options are common traps."
    }},
    {{
      "question": "A second problem-solving or numerical question on this concept.",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "C) Option 3",
      "explanation": "Step-by-step logic and formula application."
    }}
  ]
}}

Return ONLY valid JSON. No markdown code blocks, no preamble, no backticks."""

    try:
        response = await run_in_threadpool(llm.invoke, prompt)
        res_text = response.content if hasattr(response, 'content') else str(response)

        clean_json = res_text.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r'^```(?:json)?\s*', '', clean_json)
            clean_json = re.sub(r'\s*```$', '', clean_json)

        data = json.loads(clean_json.strip())

        # Save as a tracked weakness in DB if user email provided
        if req.user_email and req.user_email != "anonymous@college.edu":
            try:
                record_concept_weakness(
                    user_email=req.user_email,
                    subject=data.get("subject", req.subject or "General Engineering"),
                    concept_name=data.get("concept_name", raw_text),
                    confusion_context=raw_text,
                    dependent_topics=data.get("downstream_impact", []),
                    is_foundational=data.get("is_foundational", True),
                    is_critical=data.get("is_critical", True)
                )
            except Exception as dbe:
                print(f"[RECORD WEAKNESS ERROR] {dbe}")

        if req.user_email:
            log_user_activity(req.user_email, "", "CONCEPT_ANALYSIS", f"Diagnosed concept '{raw_text[:60]}' under {req.subject or 'General'}")

        return {"success": True, "analysis": data}
    except Exception as e:
        print(f"[CONCEPT ANALYZE ERROR] {e}")
        # Structured fallback if LLM response format fails
        concept_clean = raw_text.title()[:40]
        fallback_data = {
            "concept_name": concept_clean,
            "subject": req.subject or "General Engineering",
            "diagnostic_summary": f"Identified conceptual friction regarding '{raw_text}'. Focus on foundational definitions and practice applying the core formulas to standard exam questions.",
            "prerequisites": ["Core Definitions & Mathematical Foundations", "Basic Problem Solving"],
            "downstream_impact": ["Advanced Problem Scenarios", "University Mid-Sem/End-Sem Exam Questions"],
            "exam_risk_score": 75,
            "mastery_percentage": 30,
            "is_foundational": True,
            "is_critical": True,
            "remediation_plan": [
                {"step": "1. Intuition & Visual Mental Model", "action": f"Review the visual concept diagram for {concept_clean}."},
                {"step": "2. Core Principles", "action": "Memorize the core governing equations and edge conditions."},
                {"step": "3. Past Question Practice", "action": "Solve 3 recent university PYQ questions for this topic."}
            ],
            "practice_questions": [
                {
                    "question": f"Which of the following is the fundamental governing condition for {concept_clean}?",
                    "options": ["A) Optimal condition holds under standard constraints", "B) Condition fails when parameters diverge", "C) Universal conservation principle", "D) Depends entirely on hardware architecture"],
                    "correct_answer": "A) Optimal condition holds under standard constraints",
                    "explanation": "Standard theoretical formulation assumes constraint satisfaction."
                }
            ]
        }
        return {"success": True, "analysis": fallback_data}

@app.get("/api/weaknesses/graph")
async def get_weakness_graph_api(subject: str = ""):
    """Return subject concept dependency graph."""
    subject_clean = html.escape((subject or "").strip())
    deps = get_concept_dependency_graph(subject=subject_clean)
    return {"success": True, "dependencies": deps}

@app.get("/api/practice/generate")
async def generate_practice_api(request: Request, concept: str, difficulty: str = "easy", user_id: int = 1, user_email: Optional[str] = None):
    """Generate or retrieve an adaptive practice session for a concept."""
    if not concept or not concept.strip():
        raise HTTPException(status_code=400, detail="Concept parameter is required.")
    
    # Input validation and anti-injection check
    dangerous_patterns = [";", "--", "/*", "*/", "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE "]
    for pattern in dangerous_patterns:
        if pattern.lower() in concept.lower():
            raise HTTPException(status_code=400, detail="Invalid characters in concept name.")

    diff_clean = difficulty.strip().lower()
    if diff_clean not in ("easy", "medium", "hard"):
        diff_clean = "easy"

    email = user_email
    user_payload = get_current_user_payload(request)
    if user_payload:
        email = user_payload.get("email") or email
        user_id = user_payload.get("id") or user_id
    elif not email:
        user_token = request.headers.get("X-Access-Token") or request.cookies.get("auth_token")
        if user_token:
            verified = verify_signed_token(user_token)
            if verified:
                email = verified.get("email") or email
                user_id = verified.get("id") or user_id

    session_data = generate_adaptive_practice(concept=concept.strip(), user_id=user_id, user_email=email or "", difficulty=diff_clean)
    log_security_event("PRACTICE_SESSION_GENERATED", email or f"user_{user_id}", {
        "concept": concept,
        "difficulty": diff_clean,
        "session_id": session_data.get("session_id")
    })
    return session_data

@app.post("/api/practice/{session_id}/answer")
async def submit_practice_answer_api(session_id: int, req: PracticeAnswerRequest, request: Request):
    """Submit user answer for adaptive evaluation and difficulty progression with ownership check."""
    email = req.user_email
    user_id = req.user_id or 1
    user_payload = get_current_user_payload(request)
    if user_payload:
        email = user_payload.get("email") or email
        user_id = user_payload.get("id") or user_id
    elif not email:
        user_token = request.headers.get("X-Access-Token") or request.cookies.get("auth_token")
        if user_token:
            verified = verify_signed_token(user_token)
            if verified:
                email = verified.get("email") or email
                user_id = verified.get("id") or user_id

    # Ownership Verification
    if not verify_user_ownership(user_id=user_id, resource_id=session_id, resource_type="practice_session", user_email=email or ""):
        log_security_event("UNAUTHORIZED_PRACTICE_ACCESS_ATTEMPT", email or f"user_{user_id}", {
            "session_id": session_id,
            "action": "submit_answer"
        })
        raise HTTPException(status_code=403, detail="Access denied. You can only submit answers to your own practice sessions.")

    # Cheating and Anomaly Detection
    time_taken = req.time_taken or 15
    detect_cheating_attempt(session_id=session_id, user_email=email or "", time_taken=time_taken)

    res = submit_practice_answer(
        session_id=session_id,
        question_id=req.question_id,
        user_answer=req.user_answer,
        time_taken=time_taken,
        user_id=user_id,
        user_email=email or ""
    )

    log_security_event("PRACTICE_ANSWER_EVALUATED", email or f"user_{user_id}", {
        "session_id": session_id,
        "question_id": req.question_id,
        "is_correct": res.get("is_correct", False),
        "time_taken": time_taken
    })

    if email and email != "anonymous@college.edu":
        pts = 5 if res.get("is_correct") else 3
        add_contribution_points(email, pts)
        update_user_activity(email)

    return res

@app.post("/api/practice/{session_id}/complete")
async def complete_practice_session_api(session_id: int, request: Request, user_id: int = 1, user_email: Optional[str] = None):
    """Finalize practice session and return mastery progress report with ownership verification."""
    email = user_email
    user_payload = get_current_user_payload(request)
    if user_payload:
        email = user_payload.get("email") or email
        user_id = user_payload.get("id") or user_id
    elif not email:
        user_token = request.headers.get("X-Access-Token") or request.cookies.get("auth_token")
        if user_token:
            verified = verify_signed_token(user_token)
            if verified:
                email = verified.get("email") or email
                user_id = verified.get("id") or user_id

    # Ownership Verification
    if not verify_user_ownership(user_id=user_id, resource_id=session_id, resource_type="practice_session", user_email=email or ""):
        log_security_event("UNAUTHORIZED_PRACTICE_COMPLETE_ATTEMPT", email or f"user_{user_id}", {
            "session_id": session_id,
            "action": "complete_session"
        })
        raise HTTPException(status_code=403, detail="Access denied. You can only complete your own practice sessions.")

    res = complete_practice_session(session_id=session_id, user_id=user_id, user_email=email or "")
    log_security_event("PRACTICE_SESSION_COMPLETED", email or f"user_{user_id}", {
        "session_id": session_id,
        "accuracy_percentage": res.get("accuracy_percentage", 0.0),
        "mastery_level": res.get("mastery_level", "intermediate")
    })

    if email and email != "anonymous@college.edu":
        add_contribution_points(email, 10)
        update_user_activity(email)

    return res

from database import (
    create_user, get_user_by_email, verify_password,
    record_upload, get_file_uploads_metadata, get_all_uploads, delete_upload_record,
    get_upload_by_filename, get_upload_by_scope, record_report, get_reported_files,
    update_user_activity, add_contribution_points, get_top_contributors,
    mark_onboarding_completed, validate_password_strength, create_otp,
    verify_otp_code, update_user_password, mark_user_verified,
    check_rate_limit, record_rate_limit_attempt,
    create_document, get_document_by_id, get_user_documents,
    get_shared_documents, update_document_record, delete_document_record,
    toggle_document_share_record, check_login_lockout, record_failed_login,
    clear_failed_logins,
    analyze_user_intent, get_recommended_videos, get_or_create_conversation,
    get_recent_messages, rate_playlist_record, get_next_action_message,
    extract_topic_from_query, BENNETT_CHANNELS, seed_bennett_channels_if_needed,
    update_conversation_context_record,
    get_concept_dependency_graph, detect_concept_weakness, record_concept_weakness,
    create_weakness_profile, generate_adaptive_practice, submit_practice_answer,
    complete_practice_session, verify_user_ownership, encrypt_sensitive, decrypt_sensitive,
    get_users_admin_analytics, record_session_heartbeat, log_user_activity,
    get_admin_dashboard_stats, get_admin_user_drilldown, is_admin_user,
    get_db, db_retry
)
from fastapi import Form
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def send_otp_email(to_email: str, otp_code: str, subject: str, body_text: str):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM", smtp_user or "noreply@prepz.app")

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "html"))

            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            print(f"[EMAIL SENT] OTP successfully sent to {to_email}")
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
    else:
        print(f"[DEV NOTICE] SMTP credentials not set. OTP for {to_email} is: {otp_code}")
    return False

def send_google_login_notification(to_email: str, student_name: str = ""):
    """
    Send an official welcome / login security notification email to the student's Gmail address upon Google Sign-In.
    Dispatched asynchronously in a background daemon thread so it never blocks login latency.
    """
    def _send_worker():
        clean_email = (to_email or "").strip().lower()
        if not is_valid_email(clean_email):
            return False

        display_name = student_name.strip() if student_name else clean_email.split("@")[0].title()
        subject = "🎓 Welcome to BU Prepz AI — Google Sign-In Successful"
        login_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to BU Prepz AI</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 30px 15px;">
                <tr>
                    <td align="center">
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 580px; background: #1e293b; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                            <!-- Header Banner -->
                            <tr>
                                <td style="padding: 32px 32px 22px; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); text-align: center;">
                                    <div style="font-size: 38px; margin-bottom: 8px;">🎓</div>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">BU Prepz AI</h1>
                                    <p style="margin: 6px 0 0; color: #e0e7ff; font-size: 13.5px;">Bennett University Exam Preparation & Academic Intelligence Workspace</p>
                                </td>
                            </tr>

                            <!-- Body Content -->
                            <tr>
                                <td style="padding: 32px;">
                                    <h2 style="margin: 0 0 16px; color: #ffffff; font-size: 19px; font-weight: 700;">Hello, {display_name}! 👋</h2>
                                    <p style="margin: 0 0 18px; color: #cbd5e1; font-size: 14.5px; line-height: 1.6;">
                                        You have successfully signed in to <strong>BU Prepz AI</strong> using your Google account (<strong>{clean_email}</strong>) on <em>{login_time}</em>.
                                    </p>

                                    <!-- Quick Feature Highlights -->
                                    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px 20px; margin-bottom: 24px;">
                                        <div style="color: #818cf8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Your Academic Edge:</div>
                                        
                                        <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 10px;">⚡</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.4;"><strong>AI Doubt Solver:</strong> Ask complex engineering questions and get step-by-step syllabus-aligned solutions.</span>
                                        </div>
                                        <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 10px;">🎯</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.4;"><strong>Concept Weakness Profiler:</strong> Diagnose foundational blocker gaps and practice adaptive exam questions.</span>
                                        </div>
                                        <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 10px;">📚</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.4;"><strong>Course Repository:</strong> Access notes, PYQs, tutorials, and faculty-curated video playlists.</span>
                                        </div>
                                        <div style="display: flex; align-items: flex-start;">
                                            <span style="margin-right: 10px;">📈</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.4;"><strong>Exam Paper Predictor:</strong> Analyze recurring mid-term & end-term question patterns.</span>
                                        </div>
                                    </div>

                                    <!-- Launch Button -->
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                        <tr>
                                            <td align="center">
                                                <a href="https://om123bansal-prepz-app.hf.space" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; font-weight: 700; font-size: 14.5px; text-decoration: none; padding: 12px 28px; border-radius: 10px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">
                                                    Open BU Prepz Workspace &rarr;
                                                </a>
                                            </td>
                                        </tr>
                                    </table>

                                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                                        <p style="margin: 0 0 6px;">🔒 <strong>Security Notice:</strong> If you did not initiate this sign-in, please review your Google account security settings immediately.</p>
                                    </div>
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td style="padding: 20px 32px; background: #0f172a; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); color: #64748b; font-size: 11.5px;">
                                    &copy; {datetime.now().year} BU Prepz AI &bull; Bennett University Engineering Intelligence &bull; All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASSWORD")
        from_email = os.environ.get("SMTP_FROM", smtp_user or "noreply@prepz.app")

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = f"BU Prepz AI <{from_email}>"
                msg["To"] = clean_email
                msg["Subject"] = subject
                msg.attach(MIMEText(html_body, "html"))

                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                server.quit()
                print(f"[GOOGLE LOGIN EMAIL SENT] Welcome email successfully sent to {clean_email}")
                return True
            except Exception as e:
                print(f"[GOOGLE LOGIN EMAIL ERROR] Failed sending to {clean_email}: {e}")
        else:
            print(f"[GOOGLE LOGIN EMAIL NOTICE] (SMTP not configured) Google Sign-in confirmation logged for: {clean_email}")
        return False

    threading.Thread(target=_send_worker, daemon=True).start()

def verify_captcha_challenge(answer: Optional[str], expected: Optional[str]):
    if expected is not None and answer is not None:
        if str(answer).strip() != str(expected).strip():
            raise HTTPException(status_code=400, detail="Security challenge (CAPTCHA) answer is incorrect. Please try again.")

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    captcha_answer: Optional[str] = None
    captcha_expected: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str
    otp_type: str = "signup"

class ForgotPasswordRequest(BaseModel):
    email: str
    captcha_answer: Optional[str] = None
    captcha_expected: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    email: str
    otp_code: str
    new_password: str

class CompleteOnboardingRequest(BaseModel):
    email: str

class FirebaseSyncRequest(BaseModel):
    uid: str
    email: str
    name: Optional[str] = None
    provider: Optional[str] = "firebase"
    avatar_url: Optional[str] = None

# ── BACKEND GOOGLE OAUTH2 ── pure server-side, no CSP issues ─────────────────
# Reads from env first so a Space secret (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)
# overrides these without a code change -- set real secrets in your Hugging Face
# Space settings once you rotate the values below, since they've been public in git history.
GOOGLE_CLIENT_ID_OAUTH = os.environ.get("GOOGLE_CLIENT_ID") or "585299422541-edqtcaaoljev3op2cffl98jfvr8asn56.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET_OAUTH = os.environ.get("GOOGLE_CLIENT_SECRET") or "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"
GOOGLE_REDIRECT_URI = "https://om123bansal-prepz-app.hf.space/api/auth/google/callback"

def get_google_redirect_uri(request: Request) -> str:
    """Resolve correct Google OAuth redirect URI accounting for Hugging Face proxy headers."""
    # If running in Hugging Face Space, always use official Space callback
    if os.environ.get("SPACE_ID") or os.environ.get("SPACE_AUTHOR_NAME") or os.environ.get("HF_SPACE_ID"):
        return GOOGLE_REDIRECT_URI
    host = request.headers.get("host", "")
    if ("localhost" in host or "127.0.0.1" in host) and "hf.space" not in host:
        return f"http://{host}/api/auth/google/callback"
    return GOOGLE_REDIRECT_URI

@app.get("/api/auth/google")
def google_auth_start(request: Request):
    from urllib.parse import urlencode
    redirect_uri = get_google_redirect_uri(request)
    params = {
        "client_id": GOOGLE_CLIENT_ID_OAUTH,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    print(f"[GOOGLE OAUTH] Redirecting to Google: {url[:80]}... (redirect_uri={redirect_uri})")
    return RedirectResponse(url)

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request, code: str = None, error: str = None):
    if error or not code:
        print(f"[GOOGLE OAUTH] Error/cancelled: {error}")
        return RedirectResponse("/?auth_error=" + (error or "cancelled"))

    redirect_uri = get_google_redirect_uri(request)
    email = ""
    name = ""
    avatar_url = ""
    tokens = {}

    # Exchange code for access token & id_token
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID_OAUTH,
                "client_secret": GOOGLE_CLIENT_SECRET_OAUTH,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            })
        tokens = token_resp.json()

        # Retry with standard GOOGLE_REDIRECT_URI if first attempt returned error
        if "error" in tokens and redirect_uri != GOOGLE_REDIRECT_URI:
            print(f"[GOOGLE OAUTH] Retrying token exchange with fallback GOOGLE_REDIRECT_URI...")
            async with httpx.AsyncClient(timeout=10) as client:
                retry_resp = await client.post("https://oauth2.googleapis.com/token", data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID_OAUTH,
                    "client_secret": GOOGLE_CLIENT_SECRET_OAUTH,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                })
            retry_tokens = retry_resp.json()
            if "id_token" in retry_tokens or "access_token" in retry_tokens:
                tokens = retry_tokens

        print(f"[GOOGLE OAUTH] Token response keys: {list(tokens.keys())}")

        # Primary: Extract directly from signed id_token JWT (zero extra network calls)
        id_token_str = tokens.get("id_token")
        if id_token_str and "." in id_token_str:
            try:
                parts = id_token_str.split(".")
                if len(parts) >= 2:
                    padding = "=" * ((4 - len(parts[1]) % 4) % 4)
                    payload_bytes = base64.urlsafe_b64decode(parts[1] + padding)
                    jwt_data = json.loads(payload_bytes.decode("utf-8"))
                    email = (jwt_data.get("email") or "").strip().lower()
                    name = jwt_data.get("name") or jwt_data.get("given_name") or ""
                    avatar_url = jwt_data.get("picture") or ""
                    print(f"[GOOGLE OAUTH] Decoded from id_token: email={email}, name={name}")
            except Exception as jwt_err:
                print(f"[GOOGLE OAUTH] id_token decode warning: {jwt_err}")

        # Secondary: Fallback to Google UserInfo endpoint if email not present in id_token
        access_token = tokens.get("access_token")
        if not email and access_token:
            async with httpx.AsyncClient(timeout=8) as client:
                info_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
            info = info_resp.json()
            email = info.get("email", "").strip().lower()
            name = name or info.get("name") or ""
            avatar_url = avatar_url or info.get("picture") or ""

    except Exception as exc:
        print(f"[GOOGLE OAUTH] Token exchange exception: {exc}")

    if not email:
        print(f"[GOOGLE OAUTH FAILED] Could not extract email from Google response: {tokens}")
        return RedirectResponse("/?auth_error=token_failed")

    name = name or email.split("@")[0].title()
    avatar_url = avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    print(f"[GOOGLE OAUTH SUCCESS] Logged in: {email}")

    user = get_user_by_email(email)
    if not user:
        user = create_user(name=name, email=email, password=None, provider="google", avatar_url=avatar_url, is_verified=True)
    user = update_user_activity(email) or user
    send_google_login_notification(to_email=email, student_name=name)

    user_payload = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "provider": "google",
        "avatar_url": user["avatar_url"]
    }
    encoded = base64.b64encode(json.dumps(user_payload).encode()).decode()
    user_json = json.dumps(user_payload)

    # Return HTML bridge supporting both window.opener postMessage (popup flow) and direct redirect
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Logging in...</title>
</head>
<body style="background:#0a0c0f;color:#ffffff;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
    <div style="text-align:center;">
        <div style="width:40px;height:40px;border:3px solid rgba(255,107,0,0.3);border-top-color:#ff6b00;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 16px;"></div>
        <p style="font-size:15px;font-weight:600;">Authenticated! Connecting to BU Prepz workspace...</p>
    </div>
    <style>@keyframes spin {{ to {{ transform: rotate(360deg); }} }}</style>
    <script>
        const userPayload = {user_json};
        const authData = "{encoded}";
        try {{
            if (window.opener && !window.opener.closed) {{
                window.opener.postMessage({{ type: "PREPZ_GOOGLE_AUTH_SUCCESS", user: userPayload, authData: authData }}, "*");
                setTimeout(function() {{ window.close(); }}, 300);
            }} else {{
                window.location.href = "/?auth_data=" + authData;
            }}
        }} catch(e) {{
            window.location.href = "/?auth_data=" + authData;
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
# ────────────────────────────────────────────────────────────────────────────────


@app.post("/api/auth/google-token")
async def google_token_auth(request: Request):
    """Verify Google token (access_token or id_token) from GIS and return/create user."""
    body = await request.json()
    access_token = body.get("access_token", "")
    id_token = body.get("id_token", "")

    async with httpx.AsyncClient(timeout=8) as client:
        if access_token:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid access token")
            info = resp.json()
        elif id_token:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid ID token")
            raw = resp.json()
            info = {"email": raw.get("email",""), "name": raw.get("name",""), "picture": raw.get("picture",""), "id": raw.get("sub","")}
        else:
            raise HTTPException(status_code=400, detail="access_token or id_token required")

    email = info.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Could not get email from Google")
    name = info.get("name") or email.split("@")[0].title()
    avatar_url = info.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    print(f"[GIS AUTH] Verified Google user: {email}")
    user = get_user_by_email(email)
    if not user:
        user = create_user(name=name, email=email, password=None, provider="google", avatar_url=avatar_url, is_verified=True)
    user = update_user_activity(email) or user
    send_google_login_notification(to_email=email, student_name=name)
    return {"user": {"id": user["id"], "name": user["name"], "email": user["email"], "provider": "google", "avatar_url": user["avatar_url"]}}

@app.post("/api/firebase-sync")
def firebase_sync(req: FirebaseSyncRequest):
    email = req.email.strip().lower() if req.email else ""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    name = req.name.strip() if (req.name and req.name.strip()) else email.split("@")[0].title()
    provider = req.provider or "firebase"
    avatar_url = req.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"

    print(f"[FIREBASE SERVER] Syncing user email='{email}', uid='{req.uid}', provider='{provider}'")

    user = get_user_by_email(email)
    if not user:
        user = create_user(name=name, email=email, password=None, provider=provider, avatar_url=avatar_url, is_verified=True)
        print(f"[FIREBASE SERVER] Created new user in SQLite DB: id={user['id']}, email='{email}'")
    else:
        print(f"[FIREBASE SERVER] Existing user synchronized: id={user['id']}, email='{email}'")

    user = update_user_activity(email) or user
    if provider in ("google", "google.com", "firebase"):
        send_google_login_notification(to_email=email, student_name=name)
    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "provider": user["provider"],
            "avatar_url": user["avatar_url"],
            "contribution_score": user.get("contribution_score", 0),
            "current_streak": user.get("current_streak", 1),
            "has_seen_onboarding": user.get("has_seen_onboarding", False)
        }
    }

@app.post("/api/signup")
def signup(req: SignupRequest):
    email = req.email.strip().lower() if req.email else ""
    name = req.name.strip() if req.name else ""
    password = req.password if req.password else ""

    print(f"[AUTH SERVER] Signup request received for name='{name}', email='{email}'")

    if not name or not email or not password:
        print("[AUTH SERVER] Signup failed: missing required fields")
        raise HTTPException(status_code=400, detail="All fields are required.")
    
    if not is_valid_email(email):
        print(f"[AUTH SERVER] Signup failed: invalid email format '{email}'")
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    verify_captcha_challenge(req.captcha_answer, req.captcha_expected)

    # Rate limiting on OTP / Signup
    if not check_rate_limit(email, "signup_otp", max_attempts=5, window_minutes=60):
        print(f"[AUTH SERVER] Signup failed: rate limit exceeded for '{email}'")
        raise HTTPException(status_code=429, detail="Too many signup OTP requests. Please wait an hour before trying again.")

    # Validate password strength
    is_valid, pwd_msg = validate_password_strength(password)
    if not is_valid:
        print(f"[AUTH SERVER] Signup failed: password strength check failed for '{email}' -> {pwd_msg}")
        raise HTTPException(status_code=400, detail=pwd_msg)

    existing = get_user_by_email(email)
    if existing and existing.get("is_verified", True):
        print(f"[AUTH SERVER] Signup failed: verified account already exists for '{email}'")
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please log in.")
    
    if not existing:
        user = create_user(name=name, email=email, password=password, provider="local", is_verified=True)
        print(f"[AUTH SERVER] New verified user created in DB: id={user['id']}, email='{email}'")
    else:
        user = existing
        print(f"[AUTH SERVER] Existing user retrieved from DB: id={user['id']}, email='{email}'")

    user = update_user_activity(email) or user
    return {
        "status": "success",
        "message": "Account created successfully!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "provider": user["provider"],
            "avatar_url": user["avatar_url"],
            "contribution_score": user.get("contribution_score", 0),
            "current_streak": user.get("current_streak", 1),
            "has_seen_onboarding": user.get("has_seen_onboarding", False)
        }
    }

@app.post("/api/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    print(f"[AUTH SERVER] Verify OTP request for email='{req.email}', type='{req.otp_type}', code='{req.otp_code}'")
    if not req.email.strip() or not req.otp_code.strip():
        raise HTTPException(status_code=400, detail="Email and OTP code are required.")

    is_valid = verify_otp_code(req.email, req.otp_code, otp_type=req.otp_type)
    if not is_valid:
        print(f"[AUTH SERVER] OTP verification failed for '{req.email}'")
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code. Please try again.")

    if req.otp_type == "signup":
        mark_user_verified(req.email)
        user = get_user_by_email(req.email)
        user = update_user_activity(req.email) or user
        print(f"[AUTH SERVER] User '{req.email}' verified successfully! Session issued.")
        return {
            "status": "success",
            "message": "Account verified successfully!",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "provider": user["provider"],
                "avatar_url": user["avatar_url"],
                "contribution_score": user.get("contribution_score", 0),
                "current_streak": user.get("current_streak", 1),
                "has_seen_onboarding": user.get("has_seen_onboarding", False)
            }
        }

    print(f"[AUTH SERVER] Forgot-password OTP verified successfully for '{req.email}'")
    return {
        "status": "success",
        "message": "OTP verified successfully. You can now set your new password."
    }

@app.post("/api/login")
def login(req: LoginRequest):
    email = req.email.strip().lower() if req.email else ""
    password = req.password if req.password else ""

    print(f"[AUTH SERVER] Login request received for email='{email}'")

    if not email or not password:
        print("[AUTH SERVER] Login failed: missing email or password")
        raise HTTPException(status_code=400, detail="Please enter both email and password.")

    if not is_valid_email(email):
        print(f"[AUTH SERVER] Login failed: invalid email format '{email}'")
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # 1. Rate Limit Lockout Check (Max 5 failed attempts per 15 minutes)
    if check_login_lockout(email):
        print(f"[AUTH SERVER] Account locked out due to failed attempts for '{email}'")
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Account temporarily locked for 15 minutes for your security."
        )

    user = get_user_by_email(email)
    if not user:
        default_name = email.split("@")[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()
        user = create_user(name=default_name, email=email, password=password, provider="local", is_verified=True)
        print(f"[AUTH SERVER] Auto-created user on login for '{email}'")
    else:
        # 2. Verify Password if user has a password hash set
        if user.get("password_hash"):
            if not verify_password(password, user["password_hash"], email):
                record_failed_login(email)
                print(f"[AUTH SERVER] Login failed: incorrect password for '{email}'")
                raise HTTPException(status_code=401, detail="Invalid email or password.")

    # 3. Clear failed login counter on success
    clear_failed_logins(email)

    user = update_user_activity(email) or user
    auth_token = generate_signed_token({"id": user["id"], "email": user["email"], "name": user["name"]})
    print(f"[AUTH SERVER] Login SUCCESS for '{email}' (id={user['id']})")
    return {
        "status": "success",
        "token": auth_token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "provider": user["provider"],
            "avatar_url": user["avatar_url"],
            "contribution_score": user.get("contribution_score", 0),
            "current_streak": user.get("current_streak", 1),
            "has_seen_onboarding": user.get("has_seen_onboarding", False),
            "token": auth_token
        }
    }

@app.post("/api/forgot-password/request-otp")
def forgot_password_request_otp(req: ForgotPasswordRequest):
    print(f"[AUTH SERVER] Forgot Password OTP request for email='{req.email}'")
    if not req.email.strip():
        raise HTTPException(status_code=400, detail="Email is required.")

    verify_captcha_challenge(req.captcha_answer, req.captcha_expected)

    if not check_rate_limit(req.email, "forgot_otp", max_attempts=3, window_minutes=60):
        print(f"[AUTH SERVER] Forgot Password OTP request rate limited for '{req.email}'")
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please wait an hour before requesting another OTP.")

    user = get_user_by_email(req.email)
    if not user:
        print(f"[AUTH SERVER] Forgot Password OTP request failed: user not found for '{req.email}'")
        raise HTTPException(status_code=400, detail="No account found with this email.")

    otp_code = create_otp(req.email, otp_type="forgot_password", expiry_minutes=10)
    record_rate_limit_attempt(req.email, "forgot_otp")
    print(f"[AUTH SERVER] Forgot Password OTP generated for '{req.email}': OTP={otp_code}")

    email_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f5; color: #18181b;">
        <h2 style="color: #6366f1;">BU Prepz Workspace - Password Reset OTP</h2>
        <p>Hello <strong>{user['name']}</strong>,</p>
        <p>You requested a password reset. Your 6-digit OTP code is:</p>
        <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #4f46e5; margin: 16px 0;">{otp_code}</div>
        <p>This code expires in 10 minutes. If you did not request a password reset, please ignore this email.</p>
    </div>
    """
    send_otp_email(req.email, otp_code, "BU Prepz Workspace - Reset Password OTP", email_html)

    return {
        "status": "success",
        "email": req.email,
        "otp_code": otp_code,
        "message": f"Password reset OTP sent to {req.email}."
    }

@app.post("/api/forgot-password/reset")
def forgot_password_reset(req: ResetPasswordRequest):
    print(f"[AUTH SERVER] Forgot Password Reset request for email='{req.email}', OTP='{req.otp_code}'")
    if not req.email.strip() or not req.otp_code.strip() or not req.new_password:
        print("[AUTH SERVER] Forgot Password Reset failed: missing required fields")
        raise HTTPException(status_code=400, detail="All fields are required.")

    is_valid = verify_otp_code(req.email, req.otp_code, otp_type="forgot_password")
    if not is_valid:
        print(f"[AUTH SERVER] Forgot Password Reset failed: invalid/expired OTP for '{req.email}'")
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code.")

    is_valid_pwd, pwd_msg = validate_password_strength(req.new_password)
    if not is_valid_pwd:
        print(f"[AUTH SERVER] Forgot Password Reset failed: password strength check failed for '{req.email}' -> {pwd_msg}")
        raise HTTPException(status_code=400, detail=pwd_msg)

    update_user_password(req.email, req.new_password)
    print(f"[AUTH SERVER] Password updated successfully for '{req.email}' in SQLite DB")
    return {
        "status": "success",
        "message": "Password updated successfully! You can now log in with your new password."
    }

@app.get("/api/user/stats")
def get_user_stats(email: str):
    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="Email parameter is required.")
    user = update_user_activity(email)
    if not user:
        if email.lower().strip() == "anonymous@college.edu":
            return {
                "status": "success",
                "email": email,
                "name": "Anonymous Student",
                "contribution_score": 0,
                "current_streak": 0,
                "last_active_date": "",
                "has_seen_onboarding": True
            }
        user = create_user(name=email.split("@")[0].capitalize(), email=email)
    return {
        "status": "success",
        "email": user["email"],
        "name": user["name"],
        "contribution_score": user.get("contribution_score", 0),
        "current_streak": user.get("current_streak", 1),
        "last_active_date": user.get("last_active_date", ""),
        "has_seen_onboarding": user.get("has_seen_onboarding", False)
    }

@app.post("/api/user/complete-onboarding")
def complete_onboarding(req: CompleteOnboardingRequest):
    if not req.email or not req.email.strip():
        raise HTTPException(status_code=400, detail="Email parameter is required.")
    mark_onboarding_completed(req.email.strip())
    return {"status": "success", "message": "Onboarding marked as completed."}

@app.get("/api/leaderboard")
def get_leaderboard(email: Optional[str] = None):
    data = get_top_contributors(limit=25, current_user_email=email)
    banned_names = {"aryan sharma", "priya patel", "rohan mehta", "sneha gupta", "aditya verma", "ananya roy", "harsh vardhan", "ritik singh", "tanvi saxena"}
    clean_lb = [
        u for u in data.get("leaderboard", []) 
        if (u.get("name") or "").lower().strip() not in banned_names 
        and not (u.get("email") or "").lower().endswith(".s@bennett.edu.in")
        and not (u.get("email") or "").lower().endswith(".v@bennett.edu.in")
        and u.get("email", "").lower() not in {"aryan.sharma@bennett.edu.in", "priya.patel@bennett.edu.in", "rohan.mehta@bennett.edu.in"}
    ]
    # Re-calculate ranks for clean real user list
    for idx, item in enumerate(clean_lb):
        item["rank"] = idx + 1
    clean_podium = clean_lb[:3]
    return {
        "status": "success",
        "leaderboard": clean_lb,
        "top_podium": clean_podium,
        "user_rank": data.get("user_rank"),
        "total_active_students": len(clean_lb)
    }

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB limit

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user_email: str = Form("anonymous@college.edu"),
    user_name: str = Form("Anonymous Student"),
    subject: str = Form("General Engineering"),
    semester: str = Form("Semester 1"),
    file_type: str = Form("Notes"),
    exam_type: str = Form("Other"),
    is_private: int = Form(0),
    confirm_overwrite: bool = Form(False)
):
    allowed_exts = (".pdf", ".docx", ".doc", ".txt")
    filename_clean = os.path.basename(file.filename or "").strip()
    if not filename_clean or ".." in filename_clean or "/" in filename_clean or "\\" in filename_clean:
        raise HTTPException(status_code=400, detail="Invalid or unsafe filename.")

    if not any(filename_clean.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="Only PDF (.pdf), Word (.docx, .doc), and Text (.txt) files are supported.")
    
    # Strict MIME-type checking
    allowed_mimes = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/octet-stream"
    }
    if file.content_type and file.content_type.lower() not in allowed_mimes:
        raise HTTPException(status_code=400, detail=f"Unsupported file MIME type: {file.content_type}")
    
    if not subject or not subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required.")
        
    if not semester or not semester.strip():
        raise HTTPException(status_code=400, detail="Semester is required.")

    if not file_type or not file_type.strip():
        raise HTTPException(status_code=400, detail="File Type is required.")

    # Check for existing duplicate file under same subject & semester within the target scope
    is_priv_int = 1 if int(is_private) == 1 else 0
    if not confirm_overwrite:
        existing = get_upload_by_scope(
            filename=filename_clean,
            subject=subject,
            semester=semester,
            is_private=is_priv_int,
            user_email=user_email
        )
        if existing:
            scope_desc = "your Personal Workspace" if is_priv_int == 1 else f"Course Repository ({subject} - {semester})"
            raise HTTPException(
                status_code=409,
                detail=f"A document named '{filename_clean}' already exists under {scope_desc}. Do you still want to overwrite it?"
            )

    # Check headers / size if provided by client
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        size_mb = round(file.size / (1024 * 1024), 2)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 20MB limit ({size_mb} MB). Please select a smaller PDF."
        )

    # Scoped file storage directory (Completely separate storage for Course Repo and Personal Workspace)
    import re
    if is_priv_int == 1:
        safe_user = re.sub(r'[^a-zA-Z0-9_.-]', '_', (user_email or "anonymous").strip().lower())
        upload_dir = os.path.join(UPLOADS_DIR, "workspace", safe_user)
    else:
        upload_dir = os.path.join(UPLOADS_DIR, "course_repo")

    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    file_path = os.path.join(upload_dir, filename_clean)
    
    try:
        content = await file.read()
        size_bytes = len(content)

        if size_bytes > MAX_FILE_SIZE_BYTES:
            size_mb = round(size_bytes / (1024 * 1024), 2)
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds 20MB limit ({size_mb} MB). Please select a smaller PDF."
            )

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Also write / mirror to root uploads/ for legacy static serving compatibility if it doesn't overwrite a different file
        root_path = os.path.join(UPLOADS_DIR, filename_clean)
        if not os.path.exists(root_path) or is_priv_int == 0:
            try:
                with open(root_path, "wb") as r_buf:
                    r_buf.write(content)
            except Exception:
                pass
        
        # Record file uploader info and subject/semester/file_type/exam_type/is_private in database
        record_upload(
            filename=filename_clean,
            user_email=user_email,
            user_name=user_name,
            file_path=file_path,
            size_bytes=size_bytes,
            subject=subject,
            semester=semester,
            file_type=file_type,
            exam_type=exam_type,
            is_private=is_priv_int
        )
        
        # Add to vector DB with clean text parsing and user/subject/semester/file_type metadata
        add_pdf_to_vectordb(
            file_path,
            user_email=user_email,
            user_name=user_name,
            subject=subject,
            semester=semester,
            file_type=file_type
        )

        # Award +10 contribution points to uploader & update study streak
        if user_email and user_email != "anonymous@college.edu":
            add_contribution_points(user_email, 10)
            update_user_activity(user_email)

        scope_lbl = "Private Workspace" if is_priv_int == 1 else "Course Repo"
        log_user_activity(
            user_email=user_email,
            user_name=user_name,
            action_type="UPLOAD_DOC",
            action_details=f"Uploaded '{filename_clean}' [{scope_lbl}] ({file_type}) for {subject} - {semester}"
        )

        return {
            "status": "success",
            "filename": filename_clean,
            "user_email": user_email,
            "user_name": user_name,
            "subject": subject,
            "semester": semester,
            "file_type": file_type,
            "size_bytes": size_bytes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

from fastapi.responses import HTMLResponse
from urllib.parse import quote

def render_docx_viewer_html(filename: str, meta: dict, text_docs: list) -> HTMLResponse:
    import html
    title = filename
    subject = meta.get("subject", "General Engineering") if meta else "General Engineering"
    semester = meta.get("semester", "Semester 1") if meta else "Semester 1"
    file_type = meta.get("file_type", "Notes") if meta else "Notes"
    uploader = meta.get("user_name", "Anonymous Student") if meta else "Anonymous Student"
    
    extracted_text = "\n\n".join([d.page_content for d in text_docs]) if text_docs else "No readable text content found in this document."
    
    safe_text = html.escape(extracted_text)
    paragraphs = safe_text.split("\n")
    
    body_html = ""
    for p in paragraphs:
        p_str = p.strip()
        if not p_str:
            continue
        if p_str.startswith("#"):
            body_html += f"<h3 style='margin: 18px 0 8px 0; color: #a78bfa; font-size: 18px;'>{p_str.lstrip('#').strip()}</h3>"
        elif " | " in p_str:
            cells = p_str.split(" | ")
            cells_html = "".join([f"<td style='border: 1px solid rgba(255,255,255,0.12); padding: 8px 12px;'>{c}</td>" for c in cells])
            body_html += f"<table style='width:100%; border-collapse:collapse; margin: 12px 0; font-size: 13.5px; background: rgba(0,0,0,0.2);'><tr>{cells_html}</tr></table>"
        else:
            body_html += f"<p style='margin-bottom: 12px; line-height: 1.8; font-size: 15px; color: #e4e4e7;'>{p_str}</p>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BU Prepz Reader - {html.escape(title)}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #09090b;
            color: #f4f4f5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .reader-header {{
            background: #0f172a;
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .doc-info {{ display: flex; align-items: center; gap: 12px; }}
        .doc-title {{ font-size: 16px; font-weight: 700; color: #ffffff; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11.5px;
            font-weight: 600;
        }}
        .badge-type {{ background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }}
        .badge-sem {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .btn-download {{
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: white;
            padding: 8px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 13px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .btn-download:hover {{ opacity: 0.9; transform: translateY(-1px); }}
        .reader-container {{
            max-width: 860px;
            width: 92%;
            margin: 32px auto;
            padding: 40px;
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }}
        .uploader-bar {{
            font-size: 12.5px;
            color: #9ca3af;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
    </style>
</head>
<body>
    <header class="reader-header">
        <div class="doc-info">
            <div>
                <h1 class="doc-title">{html.escape(title)}</h1>
                <div style="display: flex; gap: 6px; margin-top: 4px;">
                    <span class="badge badge-type">{html.escape(file_type)}</span>
                    <span class="badge badge-sem">{html.escape(semester)} • {html.escape(subject)}</span>
                </div>
            </div>
        </div>
        <a href="/download/{quote(filename)}?disposition=attachment" class="btn-download" download>
            Download Original File
        </a>
    </header>
    <main class="reader-container">
        <div class="uploader-bar">Uploaded by <strong>{html.escape(uploader)}</strong></div>
        <div class="doc-content">
            {body_html}
        </div>
    </main>
</body>
</html>"""
    return HTMLResponse(content=html_content)

from urllib.parse import unquote, quote
import mimetypes

def get_media_type(filename: str) -> str:
    fn = (filename or "").lower().strip()
    if fn.endswith(".pdf"):
        return "application/pdf"
    if fn.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fn.endswith(".doc"):
        return "application/msword"
    if fn.endswith(".png"):
        return "image/png"
    if fn.endswith(".jpg") or fn.endswith(".jpeg"):
        return "image/jpeg"
    if fn.endswith(".txt"):
        return "text/plain; charset=utf-8"
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"

def get_sanitized_upload_file_path(raw_filename: str, user_email: Optional[str] = None, is_private: Optional[int] = None) -> tuple[str, str]:
    from urllib.parse import unquote
    unquoted = unquote(raw_filename or "").strip()
    clean_name = os.path.basename(unquoted)
    alt_name = os.path.basename(raw_filename or "")
    
    # 1. First check if DB knows exact file_path for this scope/user
    meta = get_upload_by_filename(clean_name, user_email=user_email, is_private=is_private) or \
           get_upload_by_filename(alt_name, user_email=user_email, is_private=is_private) or \
           get_upload_by_filename(clean_name) or \
           get_upload_by_filename(alt_name)
    if meta and meta.get("file_path") and os.path.exists(meta["file_path"]):
        return clean_name, meta["file_path"]

    # 2. Check workspace path
    if user_email:
        import re
        safe_user = re.sub(r'[^a-zA-Z0-9_.-]', '_', user_email.strip().lower())
        ws_path = os.path.join(UPLOADS_DIR, "workspace", safe_user, clean_name)
        if os.path.exists(ws_path):
            return clean_name, ws_path
        ws_alt = os.path.join(UPLOADS_DIR, "workspace", safe_user, alt_name)
        if os.path.exists(ws_alt):
            return alt_name, ws_alt

    # 3. Check course repo path
    repo_path = os.path.join(UPLOADS_DIR, "course_repo", clean_name)
    if os.path.exists(repo_path):
        return clean_name, repo_path
    repo_alt = os.path.join(UPLOADS_DIR, "course_repo", alt_name)
    if os.path.exists(repo_alt):
        return alt_name, repo_alt

    # 4. Check root uploads/ path
    root_path = os.path.join(UPLOADS_DIR, clean_name)
    if os.path.exists(root_path):
        return clean_name, root_path
    root_alt = os.path.join(UPLOADS_DIR, alt_name)
    if os.path.exists(root_alt):
        return alt_name, root_alt

    # 5. Recursive deep scan across uploads/ directory for exact or case-insensitive match
    if os.path.exists(UPLOADS_DIR):
        for root, _, files in os.walk(UPLOADS_DIR):
            for f in files:
                if f.lower() == clean_name.lower() or f.lower() == alt_name.lower():
                    matched = os.path.join(root, f)
                    return f, matched

    return clean_name, root_path

@app.get("/view/{filename:path}")
def view_file_route(filename: str, user_email: Optional[str] = None, is_private: Optional[int] = None):
    clean_name, file_path = get_sanitized_upload_file_path(filename, user_email=user_email, is_private=is_private)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found on server.")
    
    meta = get_upload_by_filename(clean_name, user_email=user_email, is_private=is_private) or \
           get_upload_by_filename(filename, user_email=user_email, is_private=is_private) or \
           get_upload_by_filename(clean_name)
    if meta and meta.get("user_email"):
        uploader_email = meta["user_email"]
        if uploader_email and uploader_email != "anonymous@college.edu":
            add_contribution_points(uploader_email, 2)

    fn_lower = clean_name.lower()
    if fn_lower.endswith(".docx") or fn_lower.endswith(".doc"):
        from rag import extract_text_from_file
        docs = extract_text_from_file(file_path)
        return render_docx_viewer_html(clean_name, meta or {}, docs)

    return FileResponse(
        file_path,
        media_type="application/pdf" if fn_lower.endswith(".pdf") else get_media_type(clean_name),
        headers={"Content-Disposition": f'inline; filename="{quote(clean_name)}"'}
    )

@app.get("/files/{filename:path}")
def get_file(filename: str, user_email: Optional[str] = None, is_private: Optional[int] = None):
    clean_name, file_path = get_sanitized_upload_file_path(filename, user_email=user_email, is_private=is_private)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found on server.")
    
    meta = get_upload_by_filename(clean_name, user_email=user_email, is_private=is_private) or \
           get_upload_by_filename(clean_name)
    if meta and meta.get("user_email"):
        uploader_email = meta["user_email"]
        if uploader_email and uploader_email != "anonymous@college.edu":
            add_contribution_points(uploader_email, 2)

    return FileResponse(
        file_path,
        media_type=get_media_type(clean_name),
        headers={"Content-Disposition": f'inline; filename="{quote(clean_name)}"'}
    )

@app.get("/download/{filename:path}")
@app.get("/api/download/{filename:path}")
def download_file_route(filename: str, disposition: Optional[str] = "attachment", user_email: Optional[str] = None, is_private: Optional[int] = None):
    try:
        clean_filename, file_path = get_sanitized_upload_file_path(filename, user_email=user_email, is_private=is_private)
        if not os.path.exists(file_path):
            print(f"[DOWNLOAD] File not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found on server.")

        # Award contribution points (non-blocking)
        try:
            meta = get_upload_by_filename(clean_filename, user_email=user_email, is_private=is_private) or \
                   get_upload_by_filename(clean_filename)
            if meta and meta.get("user_email"):
                uploader_email = meta["user_email"]
                if uploader_email and uploader_email not in ("anonymous@college.edu", "student@college.edu"):
                    add_contribution_points(uploader_email, 2)
        except Exception as cp_err:
            print(f"[DOWNLOAD] Contribution points error (ignored): {cp_err}")

        disp = "attachment" if disposition == "attachment" else "inline"
        print(f"[DOWNLOAD] Serving: {file_path} as {disp}")
        return FileResponse(
            file_path,
            media_type="application/pdf" if clean_filename.lower().endswith(".pdf") else get_media_type(clean_filename),
            headers={
                "Content-Disposition": f'{disp}; filename="{quote(clean_filename)}"',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Unexpected error for '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/files")
def list_files(user_email: Optional[str] = None):
    try:
        from database import get_all_uploads
        db_files = get_all_uploads(user_email=user_email)
        
        # Verify sizes and existence
        result_files = []
        known_set = set()
        for f in db_files:
            file_p = f.get("file_path") or os.path.join(UPLOADS_DIR, f["filename"])
            actual_size = os.path.getsize(file_p) if (file_p and os.path.exists(file_p)) else f.get("size_bytes", 0)
            f_copy = dict(f)
            f_copy["size_bytes"] = actual_size
            result_files.append(f_copy)
            known_set.add((f["filename"].lower(), f["is_private"]))

        # Also incorporate any legacy unrecorded files directly in uploads/ as public Course Repo files
        from backend_rag import get_uploaded_files
        raw_filenames = get_uploaded_files()
        for fname in raw_filenames:
            if (fname.lower(), 0) not in known_set:
                file_p = os.path.join(UPLOADS_DIR, fname)
                size_b = os.path.getsize(file_p) if os.path.exists(file_p) else 0
                result_files.append({
                    "id": None,
                    "filename": fname,
                    "user_email": "system@prepz.edu",
                    "user_name": "Faculty Contributor",
                    "uploaded_at": None,
                    "size_bytes": size_b,
                    "subject": "General Engineering",
                    "semester": "Semester 1",
                    "file_type": "Notes",
                    "exam_type": "Other",
                    "is_private": 0,
                    "file_path": file_p
                })
                known_set.add((fname.lower(), 0))
                
        return {"files": result_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{filename}")
def delete_file(filename: str, user_email: Optional[str] = None, user_name: Optional[str] = None, is_private: Optional[int] = None):
    try:
        clean_filename = os.path.basename(unquote(filename or "")).strip()
        raw_name = os.path.basename(filename or "").strip()
        
        # Ownership verification
        existing_meta = get_upload_by_filename(clean_filename, user_email=user_email, is_private=is_private) or \
                        get_upload_by_filename(raw_name, user_email=user_email, is_private=is_private)
        
        if existing_meta:
            uploader_email = (existing_meta.get("user_email") or "").lower().strip()
            uploader_name = (existing_meta.get("user_name") or "").lower().strip()
            req_email = (user_email or "").lower().strip()
            req_name = (user_name or "").lower().strip()

            # Allow if requester matches email or name or if uploaded anonymously
            if req_email and uploader_email and uploader_email not in ("anonymous@college.edu", "student@college.edu", ""):
                if req_email != uploader_email and (not req_name or req_name != uploader_name):
                    raise HTTPException(status_code=403, detail="Permission denied. You can only delete files that you uploaded.")

        # Determine exact file path
        _, file_path = get_sanitized_upload_file_path(clean_filename, user_email=user_email, is_private=is_private)
        if existing_meta and existing_meta.get("file_path") and os.path.exists(existing_meta["file_path"]):
            file_path = existing_meta["file_path"]

        # Delete from disk only if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as fe:
                print(f"[DELETE FILE DISK ERROR] {fe}")
            
        try:
            from rag import delete_pdf_from_vectordb
            delete_pdf_from_vectordb(file_path)
        except Exception as ve:
            print(f"[DELETE VECTOR ERROR (IGNORED)] {ve}")

        try:
            from backend_rag import reset_bm25_cache
            reset_bm25_cache()
        except Exception as be:
            print(f"[RESET BM25 ERROR (IGNORED)] {be}")

        delete_upload_record(clean_filename, user_email=user_email, is_private=is_private)
        delete_upload_record(raw_name, user_email=user_email, is_private=is_private)
        
        return {"status": "success", "message": f"{clean_filename} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE ROUTE ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ToggleFilePrivacyRequest(BaseModel):
    is_private: int
    user_email: Optional[str] = None

@app.post("/files/{filename}/toggle-privacy")
def toggle_file_privacy_endpoint(filename: str, req: ToggleFilePrivacyRequest, request: Request):
    filename = os.path.basename(filename)
    user_email = req.user_email or request.headers.get("X-User-Email") or request.query_params.get("user_email")
    existing_meta = get_upload_by_filename(filename, user_email=user_email)
    if not existing_meta:
        raise HTTPException(status_code=404, detail="File metadata not found.")
    
    uploader_email = (existing_meta.get("user_email") or "").lower().strip()
    req_email = (user_email or "").lower().strip()
    
    if req_email and uploader_email and req_email != uploader_email:
        raise HTTPException(status_code=403, detail="Permission denied. You can only change privacy for files you uploaded.")
    
    new_priv = 1 if req.is_private else 0
    doc_id = existing_meta.get("id")
    def _do():
        with get_db() as c:
            if doc_id:
                c.execute("UPDATE user_uploads SET is_private = ? WHERE id = ?", (new_priv, doc_id))
            else:
                c.execute("UPDATE user_uploads SET is_private = ? WHERE lower(filename) = lower(?) AND lower(user_email) = lower(?)", (new_priv, filename, uploader_email))
            c.commit()
    db_retry(_do)
    return {"status": "success", "filename": filename, "is_private": new_priv}

# ----------------------------------------------------
# Private & Shared Document Library API Endpoints
# ----------------------------------------------------

class DocumentCreateRequest(BaseModel):
    title: str
    content: Optional[str] = ""
    is_shared: Optional[bool] = False

class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_shared: Optional[bool] = None

class DocumentShareRequest(BaseModel):
    is_shared: bool

def get_current_user_from_req(request: Request) -> dict:
    user_email = request.headers.get("X-User-Email") or request.query_params.get("user_email")
    if not user_email:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            user_email = auth_hdr.replace("Bearer ", "").strip()
    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
    user = get_user_by_email(user_email)
    if not user:
        user = create_user(name=user_email.split("@")[0].title(), email=user_email, provider="local")
    return user

@app.get("/api/my-library")
def get_my_library_endpoint(request: Request):
    user = get_current_user_from_req(request)
    docs = get_user_documents(user["email"])
    return {"documents": docs}

@app.get("/api/shared-library")
def get_shared_library_endpoint(owner_id: Optional[int] = None, category: Optional[str] = None):
    docs = get_shared_documents()
    if owner_id:
        docs = [d for d in docs if d.get("user_id") == owner_id]
    return {"documents": docs}

@app.post("/api/documents")
def create_document_endpoint(req: DocumentCreateRequest, request: Request):
    user = get_current_user_from_req(request)
    doc = create_document(user_id=user["id"], user_email=user["email"], title=req.title, content=req.content, is_shared=bool(req.is_shared))
    return {"status": "success", "document": doc}

@app.get("/api/documents/{doc_id}")
def get_document_endpoint(doc_id: int, request: Request):
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc["is_shared"]:
        return {"document": doc}
    # Private doc: verify ownership
    user_email = request.headers.get("X-User-Email") or request.query_params.get("user_email")
    if not user_email or user_email.lower() != doc["user_email"].lower():
        raise HTTPException(status_code=403, detail="You do not have permission to view this document.")
    return {"document": doc}

@app.put("/api/documents/{doc_id}")
def update_document_endpoint(doc_id: int, req: DocumentUpdateRequest, request: Request):
    user = get_current_user_from_req(request)
    existing = get_document_by_id(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found.")
    if existing["user_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="You don't have permission to edit this document.")
    
    title = req.title if req.title is not None else existing["title"]
    content = req.content if req.content is not None else existing["content"]
    is_shared = req.is_shared if req.is_shared is not None else existing["is_shared"]
    
    updated = update_document_record(doc_id=doc_id, user_email=user["email"], title=title, content=content, is_shared=is_shared)
    return {"status": "success", "document": updated}

@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(doc_id: int, request: Request):
    user = get_current_user_from_req(request)
    existing = get_document_by_id(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found.")
    if existing["user_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="You don't have permission to delete this document.")
    
    delete_document_record(doc_id=doc_id, user_email=user["email"])
    return {"status": "success", "message": "Document deleted successfully."}

@app.post("/api/documents/{doc_id}/share")
def share_document_endpoint(doc_id: int, req: DocumentShareRequest, request: Request):
    user = get_current_user_from_req(request)
    existing = get_document_by_id(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found.")
    if existing["user_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="You don't have permission to share this document.")
    
    updated = toggle_document_share_record(doc_id=doc_id, user_email=user["email"], is_shared=req.is_shared)
    return {"status": "success", "document": updated}

class ReportFileRequest(BaseModel):
    filename: str
    reason: str
    notes: Optional[str] = ""
    reporter_email: Optional[str] = "anonymous@college.edu"
    reporter_name: Optional[str] = "Anonymous Student"

@app.post("/report")
def report_document(req: ReportFileRequest):
    if not req.filename or not req.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")
    if not req.reason or not req.reason.strip():
        raise HTTPException(status_code=400, detail="Reason for report is required.")

    record_report(
        filename=req.filename.strip(),
        reporter_email=req.reporter_email or "anonymous@college.edu",
        reporter_name=req.reporter_name or "Anonymous Student",
        reason=req.reason.strip(),
        notes=req.notes.strip() if req.notes else ""
    )
    return {
        "status": "success",
        "message": f"Thank you for reporting '{req.filename}'. Our moderation team will review this document."
    }

@app.get("/reports")
def list_reports():
    return {"reports": get_reported_files()}

class PredictPaperRequest(BaseModel):
    subject: str
    semester: str
    exam_type: Optional[str] = "Mid-Sem"
    user_email: Optional[str] = None

@app.post("/api/predict-paper")
async def predict_paper(req: PredictPaperRequest):
    subject = (req.subject or "").strip()
    semester = (req.semester or "").strip()
    exam_type = (req.exam_type or "Mid-Sem").strip()

    if not subject or not semester:
        raise HTTPException(status_code=400, detail="Subject and Semester are required.")

    # Helper function to normalize subject strings for comparison
    def norm_text(s: str) -> str:
        if not s:
            return ""
        s = s.lower().replace("&", "and").replace("-", " ").replace("_", " ")
        import re
        return re.sub(r'\s+', ' ', s).strip()

    norm_target_sub = norm_text(subject)
    
    # Extract numeric semester identifier (e.g. '3' from 'Semester 3' or 'Sem 3')
    import re
    sem_digits = re.findall(r'\d+', semester)
    target_sem_num = sem_digits[0] if sem_digits else semester.lower().strip()

    # 1. Fetch all uploads from database
    all_uploads = get_all_uploads(req.user_email)
    
    # Helper to resolve physical file path on disk across directories
    def resolve_physical_file_path(filename: str, meta: Optional[dict] = None) -> Optional[str]:
        if not filename:
            return None
        from urllib.parse import unquote
        variants = list(dict.fromkeys([
            filename,
            unquote(filename),
            filename.replace("+", " "),
            filename.replace(" ", "+"),
            unquote(filename).replace("+", " ")
        ]))

        # 1. Check meta file_path
        if meta and meta.get("file_path") and os.path.exists(meta["file_path"]):
            return meta["file_path"]

        # 2. Check each variant in known directories
        is_priv = meta.get("is_private", 0) if meta else 0
        u_email = meta.get("user_email") if meta else None

        for v in variants:
            v_clean = os.path.basename(v)
            # Course repo path
            cr_path = os.path.join(UPLOADS_DIR, "course_repo", v_clean)
            if os.path.exists(cr_path):
                return cr_path
            # Direct uploads root path
            root_path = os.path.join(UPLOADS_DIR, v_clean)
            if os.path.exists(root_path):
                return root_path
            # Workspace path
            if u_email:
                import re as _re
                safe_user = _re.sub(r'[^a-zA-Z0-9_.-]', '_', u_email.strip().lower())
                ws_path = os.path.join(UPLOADS_DIR, "workspace", safe_user, v_clean)
                if os.path.exists(ws_path):
                    return ws_path
            # Sanitized helper
            try:
                _, san_path = get_sanitized_upload_file_path(v_clean, user_email=u_email, is_private=is_priv)
                if san_path and os.path.exists(san_path):
                    return san_path
            except Exception:
                pass

        # 3. Recursive case-insensitive walk in uploads
        if os.path.exists(UPLOADS_DIR):
            v_lowers = [v.lower() for v in variants]
            for root_dir, _, file_list in os.walk(UPLOADS_DIR):
                for disk_file in file_list:
                    if disk_file.lower() in v_lowers:
                        return os.path.join(root_dir, disk_file)
        return None

    # Filter matching files from DB with flexible subject & semester matching
    matching_pyqs = []
    other_subject_docs = []

    target_tokens = set([w for w in norm_target_sub.split() if len(w) > 3 and w not in ('engineering', 'introduction', 'using', 'structure', 'management', 'development', 'system', 'systems')])

    for u in all_uploads:
        m_fname = u.get("filename", "")
        m_sub = norm_text(u.get("subject", ""))
        m_sem = u.get("semester", "")
        m_sem_num = re.findall(r'\d+', m_sem)
        m_sem_digit = m_sem_num[0] if m_sem_num else m_sem.lower().strip()
        m_type = (u.get("file_type") or "").strip().upper()
        m_exam = (u.get("exam_type") or "Other").strip().lower()

        # Subject match check (exact, substring, or token overlap)
        is_sub_match = (m_sub == norm_target_sub) or (norm_target_sub in m_sub) or (m_sub in norm_target_sub)
        if not is_sub_match and target_tokens:
            m_sub_tokens = set([w for w in m_sub.split() if len(w) > 3])
            fname_tokens = set([w for w in norm_text(m_fname).split() if len(w) > 3])
            if (target_tokens & m_sub_tokens) or (target_tokens & fname_tokens):
                is_sub_match = True

        is_sem_match = (m_sem_digit == target_sem_num) if (target_sem_num and m_sem_digit) else True
        is_pyq_type = (m_type == "PYQ") or ("pyq" in m_fname.lower()) or ("question" in m_fname.lower()) or ("paper" in m_fname.lower())

        if is_sub_match:
            if is_pyq_type:
                is_exact_exam = (m_exam == exam_type.lower()) or (m_exam == "other")
                matching_pyqs.append((u, is_exact_exam, is_sem_match))
            else:
                other_subject_docs.append(u)

    # Sort matching PYQs: prioritize exact exam type and semester match
    matching_pyqs.sort(key=lambda item: (1 if item[1] else 0, 1 if item[2] else 0), reverse=True)
    selected_pyq_metas = [item[0] for item in matching_pyqs]

    # If no explicit PYQs found, use subject study materials as candidate pool
    if not selected_pyq_metas and other_subject_docs:
        selected_pyq_metas = other_subject_docs[:5]

    from rag import extract_text_from_file, clean_spaced_text, is_spaced_out, llm, vectorstore

    combined_text = ""
    extracted_filenames = []

    for idx, meta in enumerate(selected_pyq_metas, 1):
        fname = meta.get("filename", "")
        fpath = resolve_physical_file_path(fname, meta)
        file_text = ""
        if fpath and os.path.exists(fpath):
            try:
                docs = extract_text_from_file(fpath)
                for doc in docs:
                    pcontent = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    if is_spaced_out(pcontent):
                        pcontent = clean_spaced_text(pcontent)
                    file_text += f"\n{pcontent}"
            except Exception as e:
                print(f"[PREDICTOR NOTICE] Extraction parser warning for {fname}: {e}")

        # If extracted text is meaningful, append it
        if len(file_text.strip()) > 30:
            if len(file_text) > 8000:
                file_text = file_text[:8000] + "\n...[truncated]..."
            combined_text += f"\n\n=== PAST YEAR QUESTION PAPER #{idx} ({fname}) ===\n{file_text}"
            extracted_filenames.append(fname)
        else:
            # Still record file presence and context
            combined_text += f"\n\n=== PAST YEAR QUESTION PAPER #{idx} ({fname}) ===\n[Document verified in Course Repository: {fname} for {subject} {semester}]"
            extracted_filenames.append(fname)

    # Fallback to ChromaDB semantic search if text from files is short
    if len(combined_text.strip()) < 200:
        try:
            if vectorstore:
                query_str = f"{subject} {semester} {exam_type} PYQ previous year questions mid-sem end-sem syllabus numericals"
                sim_docs = vectorstore.similarity_search(query_str, k=8)
                chroma_text = ""
                for sdoc in sim_docs:
                    c_src = sdoc.metadata.get("source", "Indexed Repository Material")
                    chroma_text += f"\n[Source: {os.path.basename(c_src)}]\n{sdoc.page_content}\n"
                if chroma_text.strip():
                    combined_text += f"\n\n=== REPOSITORY INDEXED KNOWLEDGE ({subject}) ===\n{chroma_text}"
                    if not extracted_filenames:
                        extracted_filenames = ["Course Repository Knowledge Base"]
        except Exception as ve:
            print(f"[PREDICTOR NOTICE] ChromaDB retrieval fallback: {ve}")

    # If no files or text found anywhere for this subject
    if not selected_pyq_metas and not other_subject_docs and not combined_text.strip():
        return {
            "success": False,
            "pyq_count": 0,
            "message": f"No PYQ question papers or documents found for {subject} ({semester}) in the Course Repository yet. Please upload at least 1 PYQ document under {subject} to generate paper predictions."
        }

    # Ensure we have context for the LLM prompt
    if not combined_text.strip():
        combined_text = f"=== VERIFIED COURSE REPOSITORY CONTEXT ===\nSubject: {subject}\nSemester: {semester}\nExam Type: {exam_type}\nVerified PYQ Papers in Repository: {', '.join(extracted_filenames) if extracted_filenames else 'Core Subject Syllabus'}"

    # Search for course code or course abbreviations in extracted content
    import re
    extracted_course_code = None
    code_match = re.search(r'\b([A-Z]{2,4}\s*[-–]?\s*\d{3,4})\b', combined_text)
    if code_match:
        extracted_course_code = code_match.group(1).replace(" ", "-")

    COURSE_CODE_MAP = {
        "Computational Thinking & Programming": "CS-101",
        "Engineering Calculus": "MA-101",
        "Introduction to Electricals & Electronics": "EE-101",
        "Electromagnetism & Mechanics": "PH-101",
        "Linear Algebra & Ordinary Differential Equation": "MA-102",
        "Digital Design": "CS-102",
        "Discrete Mathematical Structure": "CS-201",
        "OOPS using Java": "CS-202",
        "Probability & Statistics": "MA-201",
        "Statistical Machine Learning": "AI-201",
        "Information Management System": "CS-203",
        "DSA using C++": "CS-204",
        "Computer Networks": "CS-301",
        "Operating Systems": "CS-302",
        "DAA": "CS-303",
        "Microprocessor": "EC-301",
        "Artificial Intelligence": "AI-301",
        "Fullstack Development": "CS-304",
        "Cyber Security": "CS-401",
        "Quantum Computing": "PH-401",
        "UI/UX Design": "CS-402",
        "Cloud Computing": "CS-403",
        "Blockchain": "CS-404",
        "DevOps": "CS-405"
    }

    course_code = extracted_course_code or COURSE_CODE_MAP.get(subject, f"BU-{subject[:3].upper()}-{exam_type[:3].upper()}")

    # Sanitize combined_text to strictly remove any raw PDF binary or stream artifacts
    import re
    cleaned_lines = []
    for line in combined_text.splitlines():
        l_str = line.strip()
        if not l_str:
            continue
        if l_str.startswith("%PDF") or "FlateDecode" in l_str or "DCTDecode" in l_str or "/MediaBox" in l_str or "/XObject" in l_str or "endobj" in l_str or "endstream" in l_str or "startxref" in l_str:
            continue
        cleaned_lines.append(line)
    combined_text = "\n".join(cleaned_lines).strip()

    # If text from files is minimal (e.g. scanned photocopy), supply core syllabus and past pattern blueprint
    if len(combined_text) < 150:
        combined_text = f"""=== VERIFIED COURSE SYLLABUS & PAST EXAM PATTERNS ===
Subject: {subject} ({semester})
Exam Type: {exam_type}
Verified PYQ Resources: {', '.join(extracted_filenames) if extracted_filenames else 'Bennett University Examination Archives'}
Core Syllabus Domains:
- Unit 1: Foundational Concepts, Definitions, Axioms, Core Equations
- Unit 2: Intermediate Analytical Principles, System Models & Theorems
- Unit 3: Applied Methodologies, State Machines, Algorithmic Analysis & Distributions
- Unit 4: High-Yield Problem Solving, Numerical Case Studies & Boundary Conditions
- Unit 5: Advanced Comprehensive Derivations, Synthesis & System Design Calculations"""

    prompt = f"""You are the Chief University Examiner for Bennett University (Times of India Group) for {subject} ({semester}).
You are provided with real verified past year question papers (PYQs) and syllabus repository materials:

{combined_text[:25000]}

EXAMINATION PAPER CREATION MANDATE:
You must construct a complete, rigorous, official-standard Bennett University Examination Paper for {subject} ({semester} - {exam_type}).
DO NOT explain your thinking or write meta commentary. Output ONLY the structured question paper and insights in clean Markdown.

Structure your output EXACTLY as follows:

# BENNETT UNIVERSITY, GREATER NOIDA
## SCHOOL OF COMPUTER SCIENCE ENGINEERING & TECHNOLOGY
### {exam_type.upper()} EXAMINATION — ACADEMIC SESSION 2025–2026
**Course Name**: {subject} | **Course Code**: {course_code} | **Semester**: {semester}  
**Time Allowed**: 3 Hours | **Maximum Marks**: 70 Marks  

---

### GENERAL INSTRUCTIONS TO CANDIDATES:
1. **Section A** is **MANDATORY** (All 7 questions must be attempted).
2. In **Section B**, answer any **4 out of 5** questions.
3. In **Section C**, answer any **2 out of 3** questions.
4. Assume suitable data wherever necessary and state your assumptions clearly.
5. Neat sketches and diagrams must be drawn wherever relevant.

---

## 📊 TOP HIGH-YIELD RECURRING TOPICS & INSIGHTS
| Topic Domain | Historical Frequency | Predicted Probability | Examiner Advice & Focus Area |
|:---|:---:|:---:|:---|
(Provide 5 detailed rows analyzing top recurring concepts across past years)

---

## SECTION A (Short Answer & Conceptual Questions)
*(Answer all questions. 7 Questions × 2 Marks = 14 Marks | Mandatory)*

1. **[Q1]** [Clear conceptual/definition question with specific context]. `[2 Marks]`  
   **[Frequency: Appeared in 3 of 4 past exams | 92% Probability | Type: Conceptual]**

2. **[Q2]** [Short differentiation, principle, or formula statement question]. `[2 Marks]`  
   **[Frequency: Appeared in 2 of 3 past exams | 88% Probability | Type: Theory]**

3. **[Q3]** [Short mathematical/algorithmic/boundary condition question]. `[2 Marks]`  
   **[Frequency: High Yield Core Topic | 85% Probability | Type: Short Problem]**

4. **[Q4]** [Definition and significance question]. `[2 Marks]`  
   **[Frequency: Repeated in 2023, 2024 | 90% Probability | Type: Conceptual]**

5. **[Q5]** [Direct property or theorem application question]. `[2 Marks]`  
   **[Frequency: Standard Exam Opener | 86% Probability | Type: Theory]**

6. **[Q6]** [Short calculation or condition verification question]. `[2 Marks]`  
   **[Frequency: High Yield Numerical | 84% Probability | Type: Calculation]**

7. **[Q7]** [Real-world application or architectural role question]. `[2 Marks]`  
   **[Frequency: Essential Course Outcome | 89% Probability | Type: Application]**

---

## SECTION B (Medium Analytical & Problem-Solving Questions)
*(Answer any 4 out of 5 questions. 4 Questions × 7 Marks = 28 Marks)*

8. **[Q8]**
   - **(a)** [Analytical theory / mechanism explanation with diagram]. `[4 Marks]`
   - **(b)** [Step-by-step numerical or scenario problem solving]. `[3 Marks]`  
   **[Frequency: Appeared in 3 of last 4 years | 94% Probability | Type: Analytical & Numerical]**

9. **[Q9]**
   - **(a)** [Theorem derivation or architectural comparison with neat diagram]. `[4 Marks]`
   - **(b)** [Practical computation or edge-case analysis]. `[3 Marks]`  
   **[Frequency: Recurring Question Pattern | 89% Probability | Type: Derivation]**

10. **[Q10]**
    - **(a)** [Detailed algorithm / workflow analysis or mathematical distribution]. `[4 Marks]`
    - **(b)** [Numerical computation with exact parameter values]. `[3 Marks]`  
    **[Frequency: High Probability Core Unit | 91% Probability | Type: Numerical Problem]**

11. **[Q11]**
    - **(a)** [Comprehensive concept comparison with structured table / criteria]. `[4 Marks]`
    - **(b)** [Scenario-based problem or troubleshooting solution]. `[3 Marks]`  
    **[Frequency: Appeared in 2 of last 3 Mid/End-Sems | 87% Probability | Type: Design Problem]**

12. **[Q12]**
    - **(a)** [Mathematical proof or systematic evaluation]. `[4 Marks]`
    - **(b)** [Concrete numerical example solving for required output]. `[3 Marks]`  
    **[Frequency: Core Examiner Favorite | 93% Probability | Type: Proof & Calculation]**

---

## SECTION C (Long Answer, Comprehensive Derivations & Advanced Numericals)
*(Answer any 2 out of 3 questions. 2 Questions × 14 Marks = 28 Marks)*

13. **[Q13]**
    - **(a)** [In-depth complete mathematical derivation from first principles or end-to-end architecture breakdown]. `[7 Marks]`
    - **(b)** [Full-scale numerical problem with multi-part calculations and final verification]. `[7 Marks]`  
    **[Frequency: 100% Core End-Sem Topic | 96% Probability | Type: Comprehensive Numerical]**

14. **[Q14]**
    - **(a)** [Major systemic derivation, state analysis, or algorithm walkthrough with complexity proofs]. `[8 Marks]`
    - **(b)** [Complex analytical application or case study with calculations]. `[6 Marks]`  
    **[Frequency: Appeared across 4 consecutive exam cycles | 95% Probability | Type: Long Derivation]**

15. **[Q15]**
    - **(a)** [Advanced multi-stage problem solving or comprehensive protocol/distribution synthesis]. `[7 Marks]`
    - **(b)** [Comparative deep dive with mathematical/system proof of correctness]. `[7 Marks]`  
    **[Frequency: High-Yield Final Section Question | 92% Probability | Type: Advanced Synthesis]**

---
*End of Question Paper — BU Prepz Academic AI Examiner*
"""

    try:
        response = await run_in_threadpool(llm.invoke, prompt)
        paper_content = response.content if hasattr(response, 'content') else str(response)

        # Strip any <think>...</think> reasoning traces from DeepSeek/Gemini/Groq models
        clean_paper = re.sub(r'<think>[\s\S]*?</think>', '', paper_content, flags=re.IGNORECASE).strip()
        if clean_paper.startswith("```markdown"):
            clean_paper = clean_paper[len("```markdown"):].strip()
        if clean_paper.startswith("```"):
            clean_paper = clean_paper[len("```"):].strip()
        if clean_paper.endswith("```"):
            clean_paper = clean_paper[:-3].strip()

        if req.user_email and req.user_email != "anonymous@college.edu":
            add_contribution_points(req.user_email, 5)
            update_user_activity(req.user_email)

        if req.user_email:
            log_user_activity(
                user_email=req.user_email,
                user_name="",
                action_type="PREDICT_PAPER",
                action_details=f"Generated Predicted Paper for {subject} ({semester}) [{exam_type}]"
            )

        return {
            "success": True,
            "subject": subject,
            "semester": semester,
            "exam_type": exam_type,
            "pyq_count": max(len(extracted_filenames), 1),
            "pyq_filenames": extracted_filenames,
            "paper_markdown": clean_paper
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Paper Generation failed: {str(e)}")

# Mount uploads folder
os.makedirs(UPLOADS_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Starting server on http://{host}:{port}...")
    uvicorn.run("app:app", host=host, port=port)



