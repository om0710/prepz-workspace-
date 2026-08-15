import os
import json
import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, Response, RedirectResponse
import base64
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import LangGraph workflow and config
from backend_rag import workflow, active_streams
from rag import add_pdf_to_vectordb
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="LangGraph Chatbot Client API")

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

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    
    if path == "/chat" and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "chat", max_requests=30, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"error": "Rate limit exceeded. Maximum 30 chat queries per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path == "/upload" and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "upload", max_requests=10, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded. Maximum 10 file uploads per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path.startswith("/api/login") and request.method == "POST":
        if not check_ip_rate_limit(client_ip, "login", max_requests=5, window_seconds=60):
            return StreamingResponse(
                iter([json.dumps({"detail": "Rate limit exceeded. Maximum 5 login attempts per minute allowed."}).encode()]),
                status_code=429,
                media_type="application/json"
            )
            
    elif path.startswith("/api/") and not check_ip_rate_limit(client_ip, "api_general", max_requests=120, window_seconds=60):
        return StreamingResponse(
            iter([json.dumps({"detail": "Too many requests. API rate limit exceeded (120 requests/min)."}).encode()]),
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://apis.google.com https://www.gstatic.com https://cdnjs.cloudflare.com; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://youtube.com https://*.youtube.com https://prepz-workspace.firebaseapp.com https://accounts.google.com https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' https: blob: data:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://www.googleapis.com https://accounts.google.com https://api.dicebear.com https://*.firebaseio.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com; "
        "frame-ancestors *;"
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

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        self.in_tool_call = False

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
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
        if self.in_tool_call:
            return
        self.loop.call_soon_threadsafe(self.queue.put_nowait, token)

    def clear_queue(self) -> None:
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

class RatePlaylistRequest(BaseModel):
    user_id: Optional[int] = 1
    rating: int
    was_helpful: bool
    watched_percentage: Optional[int] = 30

@app.post("/chat")
async def chat_stream(request: ChatRequest):
    if request.user_email:
        add_contribution_points(request.user_email, 1)
        update_user_activity(request.user_email)

    thread_id = request.thread_id or "default_thread"
    config = {"configurable": {"thread_id": thread_id}}

    # ── Intent Understanding & Conversation Context ────────────────────────────
    try:
        conv = get_or_create_conversation(user_id=1, session_id=thread_id, subject="General")
        history = conv.get("messages", [])
        last_topic = conv.get("topics_discussed", [""])[-1] if conv.get("topics_discussed") else ""
        detected_topic = extract_topic_from_query(request.query, last_topic=last_topic)
        topic_attempts = conv.get("topic_attempts", {}).get(detected_topic, 0)

        intent_result = analyze_user_intent(
            current_message=request.query,
            conversation_history=history,
            topic=detected_topic,
            topic_attempts=topic_attempts
        )
        print(f"[INTENT] topic='{detected_topic}' attempts={topic_attempts} intent={intent_result.get('intent')} strength={intent_result.get('recommendation_strength')}")
    except Exception as ie:
        print(f"[INTENT] Analysis failed (ignored): {ie}")
        detected_topic = "general"
        topic_attempts = 0
        intent_result = {
            "should_recommend_videos": False,
            "recommendation_strength": "none",
            "intent": "initial",
            "explanation_style": "normal",
            "reason": ""
        }

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
            res = await run_in_threadpool(workflow.invoke, state, config=config)
            
            # Save message & update context
            try:
                ai_text = ""
                if res and "messages" in res and res["messages"]:
                    ai_text = str(res["messages"][-1].content)
                
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

            # Emit video recommendation if needed
            print(f"[STREAM] Checking video rec: should={intent_result.get('should_recommend_videos')} strength={intent_result.get('recommendation_strength')} topic='{detected_topic}'")
            if intent_result.get("should_recommend_videos"):
                videos = get_recommended_videos(
                    subject="",
                    topic=detected_topic,
                    difficulty_level=intent_result.get("video_difficulty", "Beginner"),
                    mode="exam",
                    limit=3
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
        res = await run_in_threadpool(workflow.invoke, state, config=config)
        explanation = str(res["messages"][-1].content) if (res and "messages" in res and res["messages"]) else f"Explanation for {topic}."

        # Video recommendations
        recommended_videos = []
        recommendation_message = ""
        if intent_analysis["should_recommend_videos"]:
            recommended_videos = get_recommended_videos(
                subject=request.subject or "Introduction to Electrical & Electronics",
                topic=topic,
                difficulty_level=intent_analysis["video_difficulty"],
                mode=request.mode or "exam",
                limit=3
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

        return {
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

# ── Part 5: Seed Channels Endpoint (/api/admin/seed-channels) ─────────────────
@app.post("/api/admin/seed-channels")
async def seed_channels_endpoint(admin_token: Optional[str] = None):
    """Populate database with Bennett University recommended channels"""
    try:
        seed_bennett_channels_if_needed()
        return {"status": "success", "message": f"Seeded {len(BENNETT_CHANNELS)} Bennett University channels."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from database import (
    create_user, get_user_by_email, verify_password,
    record_upload, get_file_uploads_metadata, delete_upload_record,
    get_upload_by_filename, record_report, get_reported_files,
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
    update_conversation_context_record
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
GOOGLE_CLIENT_ID_OAUTH = "585299422541-edqtcaaoljev3op2cffl98jfvr8asn56.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET_OAUTH = "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"
GOOGLE_REDIRECT_URI = "https://om123bansal-prepz-app.hf.space/api/auth/google/callback"

@app.get("/api/auth/google")
def google_auth_start():
    from urllib.parse import urlencode
    params = {
        "client_id": GOOGLE_CLIENT_ID_OAUTH,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    print(f"[GOOGLE OAUTH] Redirecting to Google: {url[:80]}...")
    return RedirectResponse(url)

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request, code: str = None, error: str = None):
    if error or not code:
        print(f"[GOOGLE OAUTH] Error/cancelled: {error}")
        return RedirectResponse("/?auth_error=" + (error or "cancelled"))
    # Exchange code for access token
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID_OAUTH,
            "client_secret": GOOGLE_CLIENT_SECRET_OAUTH,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        })
    tokens = token_resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        print(f"[GOOGLE OAUTH] Token exchange failed: {tokens}")
        return RedirectResponse("/?auth_error=token_failed")
    # Get user info
    async with httpx.AsyncClient(timeout=8) as client:
        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    info = info_resp.json()
    email = info.get("email", "").strip().lower()
    if not email:
        return RedirectResponse("/?auth_error=no_email")
    name = info.get("name") or email.split("@")[0].title()
    avatar_url = info.get("picture") or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    print(f"[GOOGLE OAUTH] Authenticated: {email}")
    user = get_user_by_email(email)
    if not user:
        user = create_user(name=name, email=email, password=None, provider="google", avatar_url=avatar_url, is_verified=True)
    user = update_user_activity(email) or user
    user_payload = {"id": user["id"], "name": user["name"], "email": user["email"], "provider": "google", "avatar_url": user["avatar_url"]}
    encoded = base64.b64encode(json.dumps(user_payload).encode()).decode()
    return RedirectResponse(f"/?auth_data={encoded}")
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
def get_leaderboard():
    leaderboard = get_top_contributors(10)
    return {
        "status": "success",
        "leaderboard": leaderboard
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

    # Check for existing duplicate file under same subject & semester
    if not confirm_overwrite:
        existing = get_upload_by_filename(filename_clean)
        if existing and existing["subject"] == subject and existing["semester"] == semester:
            raise HTTPException(
                status_code=409,
                detail=f"A similar file named '{filename_clean}' for {subject} ({semester}) already exists. Do you still want to upload?"
            )

    # Check headers / size if provided by client
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        size_mb = round(file.size / (1024 * 1024), 2)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 20MB limit ({size_mb} MB). Please select a smaller PDF."
        )

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
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
        
        # Record file uploader info and subject/semester/file_type/exam_type/is_private in database
        record_upload(
            filename=file.filename,
            user_email=user_email,
            user_name=user_name,
            file_path=file_path,
            size_bytes=size_bytes,
            subject=subject,
            semester=semester,
            file_type=file_type,
            exam_type=exam_type,
            is_private=int(is_private)
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

        return {
            "status": "success",
            "filename": file.filename,
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

def get_sanitized_upload_file_path(raw_filename: str) -> tuple[str, str]:
    unquoted = unquote(raw_filename or "").strip()
    clean_name = os.path.basename(unquoted)
    file_path = os.path.join("uploads", clean_name)
    if not os.path.exists(file_path):
        alt_name = os.path.basename(raw_filename or "")
        alt_path = os.path.join("uploads", alt_name)
        if os.path.exists(alt_path):
            file_path = alt_path
            clean_name = alt_name
    return clean_name, file_path

@app.get("/view/{filename}")
def view_file_route(filename: str):
    filename, file_path = get_sanitized_upload_file_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    
    meta = get_upload_by_filename(filename) or get_upload_by_filename(unquote(filename))
    if meta and meta.get("user_email"):
        uploader_email = meta["user_email"]
        if uploader_email and uploader_email != "anonymous@college.edu":
            add_contribution_points(uploader_email, 2)

    fn_lower = filename.lower()
    if fn_lower.endswith(".docx") or fn_lower.endswith(".doc"):
        from rag import extract_text_from_file
        docs = extract_text_from_file(file_path)
        return render_docx_viewer_html(filename, meta or {}, docs)

    return FileResponse(
        file_path,
        media_type="application/pdf" if fn_lower.endswith(".pdf") else get_media_type(filename),
        headers={"Content-Disposition": f'inline; filename="{quote(filename)}"'}
    )

@app.get("/files/{filename}")
def get_file(filename: str):
    filename, file_path = get_sanitized_upload_file_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    # Award +2 contribution points to original uploader
    meta = get_upload_by_filename(filename)
    if meta and meta.get("user_email"):
        uploader_email = meta["user_email"]
        if uploader_email and uploader_email != "anonymous@college.edu":
            add_contribution_points(uploader_email, 2)

    return FileResponse(
        file_path,
        media_type=get_media_type(filename),
        headers={"Content-Disposition": f'inline; filename="{quote(filename)}"'}
    )

@app.get("/download/{filename}")
@app.get("/api/download/{filename}")
def download_file_route(filename: str, disposition: Optional[str] = "inline"):
    try:
        filename, file_path = get_sanitized_upload_file_path(filename)
        if not os.path.exists(file_path):
            # Try absolute path fallback
            abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", filename)
            if os.path.exists(abs_path):
                file_path = abs_path
            else:
                print(f"[DOWNLOAD] File not found: {file_path}")
                raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

        # Award contribution points (non-blocking)
        try:
            meta = get_upload_by_filename(filename)
            if meta and meta.get("user_email"):
                uploader_email = meta["user_email"]
                if uploader_email and uploader_email != "anonymous@college.edu":
                    add_contribution_points(uploader_email, 2)
        except Exception as cp_err:
            print(f"[DOWNLOAD] Contribution points error (ignored): {cp_err}")

        disp = "attachment" if disposition == "attachment" else "inline"
        print(f"[DOWNLOAD] Serving: {file_path} as {disp}")
        return FileResponse(
            file_path,
            media_type=get_media_type(filename),
            headers={"Content-Disposition": f'{disp}; filename="{quote(filename)}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Unexpected error for '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/files")
def list_files(user_email: Optional[str] = None):
    try:
        from backend_rag import get_uploaded_files
        raw_filenames = get_uploaded_files()
        metadata_map = get_file_uploads_metadata()
        
        files_with_meta = []
        for filename in raw_filenames:
            meta = metadata_map.get(filename, {})
            f_email = meta.get("user_email", "anonymous@college.edu")
            is_priv = meta.get("is_private", 0)

            # Privacy Filter: If private document, show ONLY to its owner
            if is_priv == 1 and user_email and f_email.lower() != user_email.lower():
                continue

            files_with_meta.append({
                "filename": filename,
                "user_email": f_email,
                "user_name": meta.get("user_name", "Anonymous Student"),
                "uploaded_at": meta.get("uploaded_at", None),
                "size_bytes": meta.get("size_bytes", 0),
                "subject": meta.get("subject", "General Engineering"),
                "semester": meta.get("semester", "Semester 1"),
                "file_type": meta.get("file_type", "Notes"),
                "exam_type": meta.get("exam_type", "Other"),
                "is_private": is_priv
            })
        return {"files": files_with_meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{filename}")
def delete_file(filename: str, user_email: Optional[str] = None, user_name: Optional[str] = None):
    try:
        filename = os.path.basename(filename)
        import os
        from rag import delete_pdf_from_vectordb
        from backend_rag import reset_bm25_cache
        
        # Ownership verification
        existing_meta = get_upload_by_filename(filename)
        if existing_meta:
            uploader_email = (existing_meta.get("user_email") or "").lower().strip()
            uploader_name = (existing_meta.get("user_name") or "").lower().strip()
            req_email = (user_email or "").lower().strip()
            req_name = (user_name or "").lower().strip()

            if req_email and uploader_email and req_email != uploader_email:
                raise HTTPException(status_code=403, detail="Permission denied. You can only delete files that you uploaded.")
            if req_name and uploader_name and req_name != uploader_name and not req_email:
                raise HTTPException(status_code=403, detail="Permission denied. You can only delete files that you uploaded.")

        file_path = os.path.join("uploads", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        delete_pdf_from_vectordb(file_path)
        reset_bm25_cache()
        delete_upload_record(filename)
        
        return {"status": "success", "message": f"{filename} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ToggleFilePrivacyRequest(BaseModel):
    is_private: int
    user_email: Optional[str] = None

@app.post("/files/{filename}/toggle-privacy")
def toggle_file_privacy_endpoint(filename: str, req: ToggleFilePrivacyRequest, request: Request):
    filename = os.path.basename(filename)
    user_email = req.user_email or request.headers.get("X-User-Email") or request.query_params.get("user_email")
    existing_meta = get_upload_by_filename(filename)
    if not existing_meta:
        raise HTTPException(status_code=404, detail="File metadata not found.")
    
    uploader_email = (existing_meta.get("user_email") or "").lower().strip()
    req_email = (user_email or "").lower().strip()
    
    if req_email and uploader_email and req_email != uploader_email:
        raise HTTPException(status_code=403, detail="Permission denied. You can only change privacy for files you uploaded.")
    
    new_priv = 1 if req.is_private else 0
    def _do():
        with get_db() as c:
            c.execute("UPDATE user_uploads SET is_private = ? WHERE lower(filename) = lower(?)", (new_priv, filename))
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

@app.post("/api/predict-paper")
async def predict_paper(req: PredictPaperRequest):
    subject = req.subject.strip()
    semester = req.semester.strip()
    exam_type = req.exam_type.strip() if req.exam_type else "Mid-Sem"

    if not subject or not semester or not exam_type:
        raise HTTPException(status_code=400, detail="Subject, Semester, and Exam Type are required.")

    # Fetch metadata for all uploaded files
    metadata_map = get_file_uploads_metadata()
    
    # Filter files that match subject, semester, file_type == 'PYQ', AND exam_type
    pyq_files = []
    for filename, meta in metadata_map.items():
        m_sub = (meta.get("subject") or "").strip()
        m_sem = (meta.get("semester") or "").strip()
        m_type = (meta.get("file_type") or "").strip().upper()
        m_exam = (meta.get("exam_type") or "Other").strip()

        if (m_sub.lower() == subject.lower() and 
            m_sem.lower() == semester.lower() and 
            m_type == "PYQ" and 
            m_exam.lower() == exam_type.lower()):
            pyq_files.append(filename)

    # Check requirement: At least 2 PYQs needed for the selected exam type
    if len(pyq_files) < 2:
        return {
            "success": False,
            "pyq_count": len(pyq_files),
            "message": f"Not enough {exam_type} PYQs uploaded yet for {subject} ({semester}). ({len(pyq_files)} found). Please upload at least 2 {exam_type} PYQ papers to generate an accurate paper prediction."
        }

    # Extract text from the matching PYQ files
    from langchain_community.document_loaders import PyPDFLoader
    from rag import clean_spaced_text, is_spaced_out, llm

    combined_text = ""
    extracted_count = 0

    for idx, fname in enumerate(pyq_files, 1):
        file_path = os.path.join("uploads", fname)
        if os.path.exists(file_path):
            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                file_text = ""
                for doc in docs:
                    pcontent = doc.page_content or ""
                    if is_spaced_out(pcontent):
                        pcontent = clean_spaced_text(pcontent)
                    file_text += f"\n{pcontent}"
                
                if len(file_text) > 8000:
                    file_text = file_text[:8000] + "\n...[truncated]..."

                combined_text += f"\n\n=== PAST YEAR QUESTION PAPER #{idx} ({fname}) ===\n{file_text}"
                extracted_count += 1
            except Exception as e:
                print(f"Error extracting text from {fname}: {e}")

    if not combined_text.strip():
        return {
            "success": False,
            "pyq_count": len(pyq_files),
            "message": f"Could not extract text content from the uploaded PYQ files for {subject}."
        }

    import re
    # Search for actual course code in extracted PYQ text (e.g. CS-301, KCS401, EE-101)
    extracted_course_code = None
    code_match = re.search(r'\b([A-Z]{2,4}\s*[-–]?\s*\d{3,4})\b', combined_text)
    if code_match:
        extracted_course_code = code_match.group(1).replace(" ", "-")

    COURSE_CODE_MAP = {
        "Computer Science & Programming": "CS-101",
        "Engineering Mathematics": "MA-101",
        "Engineering Physics": "PH-101",
        "Basic Electrical & Electronics": "EE-101",
        "Environmental Studies": "EV-101",
        "Data Structures & Algorithms": "CS-201",
        "Engineering Chemistry": "CH-101",
        "Digital Logic Design": "CS-202",
        "Discrete Mathematics": "MA-202",
        "Object Oriented Programming": "CS-203",
        "Computer Organization & Architecture": "CS-301",
        "Database Management Systems": "CS-302",
        "Theory of Computation": "CS-303",
        "Operating Systems": "CS-304",
        "Software Engineering": "CS-305",
        "Design & Analysis of Algorithms": "CS-401",
        "Computer Networks": "CS-402",
        "Microprocessors & Microcontrollers": "EC-403",
        "Artificial Intelligence": "CS-404",
        "Signals & Systems": "EC-405",
        "Machine Learning": "CS-501",
        "Web Technologies & Frameworks": "CS-502",
        "Compiler Design": "CS-503",
        "Information Security": "CS-504",
        "Computer Graphics": "CS-505",
        "Cloud Computing": "CS-601",
        "Big Data Analytics": "CS-602",
        "Cyber Security & Cryptography": "CS-603",
        "Mobile Application Development": "CS-604",
        "Deep Learning": "CS-605",
        "Data Science": "CS-701",
        "Internet of Things (IoT)": "CS-702",
        "Blockchain Technologies": "CS-703",
        "Natural Language Processing": "CS-704",
        "Software Testing": "CS-705",
        "Major Capstone Project": "CS-801",
        "Distributed Systems": "CS-802",
        "High Performance Computing": "CS-803",
        "Neural Networks": "CS-804",
        "Advanced AI": "CS-805"
    }

    course_code = extracted_course_code or COURSE_CODE_MAP.get(subject, f"ENG-{subject[:3].upper()}-2026")

    prompt = f"""You are a senior engineering university examiner and question paper creator for {subject} ({semester}).
You are provided with text extracted from {extracted_count} past year question papers (PYQs) for {subject} ({semester}):

{combined_text[:25000]}

INSTRUCTIONS & EXAM PAPER CREATION RULES:
1. Analyze the provided PYQ texts carefully. Identify recurring topics, repeated numericals, essential core concepts, and high-frequency question patterns across the different exam years.
2. Generate an explicit TOP HIGH-YIELD RECURRING TOPICS & INSIGHTS section followed by a complete PREDICTED QUESTION PAPER for the upcoming examination in {subject} ({semester}).
3. Structure the entire output in clean Markdown as follows:

## TOP HIGH-YIELD RECURRING TOPICS & INSIGHTS
- Provide 4 to 6 bullet points listing the top repeated topics identified across the PYQs.
- For each topic, include its repetition frequency tag and key exam preparation advice, e.g.:
  `**Topic Name**: Appeared in X of Y past years (Z% Probability) — Focus on [specific derivation/numerical/concept].`

---

# BUBU PREPZ ACADEMIC EXAMINATION
- Header: Subject: {subject} | {semester}
- Exam Info: Time Allowed: 3 Hours | Maximum Marks: 70 Marks | Course Code: {course_code}
- Instructions to Candidates (4 bullet points)
- SECTION A (Short Answer Questions | 7 Questions x 2 Marks = 14 Marks | Mandatory)
- SECTION B (Medium / Analytical / Problem-Solving Questions | Answer 4 out of 5 Questions x 7 Marks = 28 Marks)
- SECTION C (Long Answer / Comprehensive / Numerical Questions | Answer 2 out of 3 Questions x 14 Marks = 28 Marks)

4. CRITICAL MANDATORY REQUIREMENT: For EVERY single question in Section A, Section B, and Section C, you MUST append a frequency probability tag and question type tag at the very end in bold brackets, e.g.:
   `**[Frequency: Appeared in 3 of the last 4 years | 90% Probability | Type: Theory]**` or `**[Frequency: Appeared in 2 of last 3 years | 85% Probability | Type: Numerical]**`

Format the entire output in clean, professional Markdown with clear section headings, bolding, and numbered questions. Do NOT wrap your output in code block backticks (no ``` markdown). Output only the document content."""

    try:
        response = await run_in_threadpool(llm.invoke, prompt)
        paper_content = response.content if hasattr(response, 'content') else str(response)

        return {
            "success": True,
            "subject": subject,
            "semester": semester,
            "exam_type": exam_type,
            "pyq_count": len(pyq_files),
            "pyq_filenames": pyq_files,
            "paper_markdown": paper_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Paper Generation failed: {str(e)}")

# Mount uploads folder
os.makedirs("uploads", exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Starting server on http://{host}:{port}...")
    uvicorn.run("app:app", host=host, port=port)



