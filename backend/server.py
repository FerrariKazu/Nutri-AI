import uuid
import logging
import asyncio
import json
from fastapi import FastAPI, Request, HTTPException, Response, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nutri Unified API", description="Integrated 13-Phase Food Synthesis Engine")

# Production CORS Whitelist
ALLOWED_ORIGINS = [
    "https://nutri-ai-ochre.vercel.app",
    "https://nutri-qte326vny-ferrarikazus-projects.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000"
]

def add_cors_headers(response: Response, request: Request) -> Response:
    """Explicitly inject CORS headers based on request origin"""
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"
    return response

# Initialize Components
memory_store = SessionMemoryStore()
orchestrator = NutriOrchestrator(memory_store)

class ChatPreferences(BaseModel):
    audience_mode: str = "casual"
    optimization_goal: str = "comfort"
    verbosity: str = "medium"

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    preferences: Optional[ChatPreferences] = Field(default_factory=ChatPreferences)
    execution_mode: Optional[str] = None

@app.options("/api/chat")
@app.options("/api/chat/stream")
async def chat_preflight(request: Request):
    """Explicit manual preflight handler to bypass middleware limitations"""
    response = Response(status_code=200)
    return add_cors_headers(response, request)

@app.get("/api/chat/stream")
async def chat_stream(
    request: Request,
    message: str = Query(...),
    session_id: Optional[str] = None,
    execution_mode: Optional[str] = None,
    audience_mode: str = "casual",
    optimization_goal: str = "comfort",
    verbosity: str = "medium"
):
    """
    GET-based SSE endpoint for EventSource compatibility. Eliminates preflight.
    """
    session_id = session_id or str(uuid.uuid4())
    pref_dict = {
        "audience_mode": audience_mode,
        "optimization_goal": optimization_goal,
        "verbosity": verbosity
    }
    
    return await handle_chat_execution(request, message, session_id, pref_dict, execution_mode)

@app.post("/api/chat")
async def chat_post(request: Request, payload: ChatRequest):
    """Standard POST endpoint for rich payloads"""
    pref_dict = payload.preferences.dict() if payload.preferences else {}
    return await handle_chat_execution(
        request, 
        payload.message, 
        payload.session_id or str(uuid.uuid4()), 
        pref_dict, 
        payload.execution_mode
    )

from backend.sse_utils import format_sse_event

async def handle_chat_execution(
    request: Request,
    message: str,
    session_id: str,
    preferences: Dict[str, Any],
    execution_mode: Optional[str]
):
    """Core logic with concurrent heartbeat to survive long LLM phases"""
    
    async def event_generator():
        queue = asyncio.Queue()
        
        # Immediate initialization event
        yield format_sse_event("status", {"phase": "initializing", "message": "Connecting to Nutri backend..."})

        async def run_orchestrator():
            try:
                async for event_dict in orchestrator.execute_streamed(
                    session_id, 
                    message, 
                    preferences,
                    execution_mode=execution_mode
                ):
                    await queue.put(event_dict)
                
                # Mandatory done event
                await queue.put({"type": "done", "content": {"status": "completed"}})
            except Exception as e:
                logger.exception("Orchestrator task failed")
                await queue.put({
                    "type": "error_event", 
                    "content": {"message": str(e), "phase": "orchestration", "status": "failed"}
                })
            finally:
                await queue.put(None) # Sentinel

        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(12) # Cloudflare-safe interval
                    await queue.put({"type": "ping", "content": {}})
            except asyncio.CancelledError:
                pass

        # Start background tasks
        o_task = asyncio.create_task(run_orchestrator())
        h_task = asyncio.create_task(heartbeat())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                
                event_type = item.get("type", "token")
                content = item.get("content")
                yield format_sse_event(event_type, content)
        finally:
            h_task.cancel()
            o_task.cancel()
            try:
                await h_task
                await o_task
            except asyncio.CancelledError:
                pass

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
    
    # Cloudflare/Nginx Tuning Headers
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
#    response.headers["Transfer-Encoding"] = "chunked" # StreamingResponse usually handles this
    
    return add_cors_headers(response, request)

@app.get("/health")
async def health_check(request: Request):
    response = JSONResponse({"status": "healthy", "service": "nutri-backend", "version": "1.3.0"})
    return add_cors_headers(response, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
