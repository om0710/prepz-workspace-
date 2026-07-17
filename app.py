import os
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    thread_id: str

def serialize_message(msg):
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    elif isinstance(msg, AIMessage):
        # Only return AIMessages that have content (skipping tool-call triggers)
        if msg.content:
            return {"role": "assistant", "content": msg.content}
    return None

# Serve static frontend folder
os.makedirs("static", exist_ok=True)

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

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

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if token:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, token)

@app.post("/chat")
async def chat_stream(request: ChatRequest):
    thread_id = request.thread_id or "default_thread"
    config = {"configurable": {"thread_id": thread_id}}
    state = {"messages": [HumanMessage(content=request.query)]}
    
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    handler = QueueCallbackHandler(queue, loop)
    
    # Store handler in registry mapped to thread ID
    active_streams[thread_id] = handler
    
    async def run_workflow():
        try:
            await run_in_threadpool(workflow.invoke, state, config=config)
        except Exception as e:
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
            yield f"data: {json.dumps({'text': token})}\n\n"
            
    return StreamingResponse(response_generator(), media_type="text/event-stream")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Add to vector DB with clean text parsing
        add_pdf_to_vectordb(file_path)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
def list_files():
    try:
        from backend_rag import get_uploaded_files
        return {"files": get_uploaded_files()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{filename}")
def delete_file(filename: str):
    try:
        import os
        from rag import delete_pdf_from_vectordb
        from backend_rag import reset_bm25_cache
        
        file_path = os.path.join("uploads", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        delete_pdf_from_vectordb(file_path)
        reset_bm25_cache()
        
        return {"status": "success", "message": f"{filename} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")
