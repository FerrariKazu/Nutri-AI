import uuid
import logging
import asyncio
import json
import time # Added for trace
from fastapi import FastAPI, Request, HTTPException, Response, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore
from backend.production_audit import run_startup_audit
from backend.resource_budget import ResourceBudget


# 🟢 PHASE 4: Mandatory Startup Audit (Hard Failure)
run_startup_audit()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nutri Unified API", description="Integrated 13-Phase Food Synthesis Engine")

# Explicit CORS for production and development
origins = [
    "https://nutri-ai-ochre.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize Components
memory_store = SessionMemoryStore()
orchestrator = NutriOrchestrator(memory_store)

from backend.llm_qwen3 import LLMQwen3
from backend.nutri_engine import NutriEngine
from backend.mode_classifier import classify_response_mode
from backend.response_modes import ResponseMode

# Initialize Unified NutriEngine (replaces FoodConversationAgent)
llm_client = LLMQwen3()
nutri_engine = NutriEngine(llm_client, memory_store)

class ChatPreferences(BaseModel):
    audience_mode: str = "casual"
    optimization_goal: str = "comfort"
    verbosity: str = "medium"

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    preferences: Optional[ChatPreferences] = Field(default_factory=ChatPreferences)
    execution_mode: Optional[str] = None


@app.get("/api/conversation")
async def get_conversation(request: Request, session_id: Optional[str] = Query(None)):
    """
    Returns the canonical conversation history and state for hydration.
    """
    logger.debug(f"GET /api/conversation?session_id={session_id}")
    if not session_id:
        return JSONResponse({"messages": [], "status": "new_session"})
    try:
        data = memory_store.get_conversation(session_id)
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Failed to fetch conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def list_conversations(request: Request):
    """
    List all available conversation sessions.
    """
    try:
        data = memory_store.list_sessions()
        return JSONResponse({"conversations": data})
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation")
async def create_conversation(request: Request):
    """
    Explicitly create a new session ID.
    """
    new_id = f"sess_{uuid.uuid4().hex[:12]}_{int(uuid.uuid1().time)}"
    # Pre-warm the session in DB
    memory_store._update_activity(new_id)
    
    return JSONResponse({"session_id": new_id, "status": "created"})

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
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
        
    pref_dict = {
        "audience_mode": audience_mode,
        "optimization_goal": optimization_goal,
        "verbosity": verbosity
    }
    
    return await handle_chat_execution(request, message, session_id, pref_dict, execution_mode)

@app.post("/api/chat")
async def chat_post(request: Request, payload: ChatRequest):
    """Standard POST endpoint for rich payloads"""
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
        
    pref_dict = payload.preferences.dict() if payload.preferences else {}
    return await handle_chat_execution(
        request, 
        payload.message, 
        payload.session_id, 
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
    """Core logic with concurrent heartbeat and deterministic termination."""
    queue = asyncio.Queue()
    done_sent = False
    first_token_sent = False
    
    async def run_orchestrator():
        seq_id = 1
        try:
            # 0. Check for decay BEFORE starting
            decayed = memory_store.check_and_reset_decay(session_id)
            if decayed:
                await queue.put({"type": "status", "content": {"phase": "reset", "message": "New environment initialized."}, "seq_id": seq_id, "ts": time.time()})
                seq_id += 1

            async for event_dict in orchestrator.execute_streamed(
                session_id, 
                message, 
                preferences,
                execution_mode=execution_mode
            ):
                # Use orchestrator's sequence if provided, otherwise server seq
                curr_seq = event_dict.get("seq", seq_id)
                # 🟢 Inject Sequence ID and Timestamp
                payload = {
                    **event_dict,
                    "seq_id": curr_seq,
                    "ts": time.time()
                }
                await queue.put(payload)
                if curr_seq >= seq_id:
                    seq_id = curr_seq + 1

            
        except Exception as e:
            logger.exception("Orchestrator task failed")
            await queue.put({
                "type": "error_event", 
                "content": {"message": str(e), "phase": "orchestration", "status": "failed"},
                "seq_id": seq_id,
                "ts": time.time()
            })
            seq_id += 1
            await queue.put({"type": "done", "content": {"status": "error", "message": str(e)}, "seq_id": seq_id, "ts": time.time()})
        finally:
            await queue.put(None) # Sentinel for the queue loop

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(1) # Aggressive heartbeat for proxies
                await queue.put({"type": "ping", "content": {}, "ts": time.time()})
        except asyncio.CancelledError:
            pass

    # Start background tasks
    o_task = asyncio.create_task(run_orchestrator())
    h_task = asyncio.create_task(heartbeat())

    async def event_generator():
        try:
            while True:
                item = await queue.get()
                if item is None:
                    logger.info("[SSE] Sentinel received from orchestrator.")
                    break
                
                event_type = item.get("type", "token")
                content = item.get("content")
                
                # Log first token for TTT measurement
                nonlocal first_token_sent
                if event_type == "token" and not first_token_sent:
                    logger.info("[SSE] First token sent to client.")
                    first_token_sent = True

                nonlocal done_sent
                if event_type == "done":
                    done_sent = True
                    logger.info(f"[SSE] Emitting DONE event: {content}")

                formatted_chunk = format_sse_event(event_type, item) # Pass whole item to preserve seq_id
                logger.debug(f"[SSE] YIELDING: {repr(formatted_chunk)}")
                yield formatted_chunk
                
        except GeneratorExit:
            logger.warning("[SSE] Client disconnected (GeneratorExit).")
            if not done_sent:
                logger.warning("[SSE] Emitting emergency DONE event after disconnect.")
                yield format_sse_event("done", {})
            raise
        except Exception as e:
            logger.error(f"[SSE] Critical Stream Error: {e}")
            yield format_sse_event("error_event", {"message": str(e)})
            if not done_sent:
                yield format_sse_event("done", {"status": "error", "message": str(e)})
            raise
        finally:
            # The Final Safety Net
            if not done_sent:
                logger.warning("[SSE] Loop finished without DONE. Forcing emission.")
                try:
                    yield format_sse_event("done", {})
                except Exception as final_e:
                    logger.error(f"[SSE] Failed to emit final DONE: {final_e}")
            
            logger.info("[SSE] Stream closing. Cleaning up tasks...")
            o_task.cancel()
            h_task.cancel()
            try:
                await asyncio.gather(o_task, h_task, return_exceptions=True)
            except Exception as e:
                logger.debug(f"Cleanup error (expected): {e}")
            logger.info("[SSE] All background tasks finalized.")

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
    
    # Tuning Headers
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    
    return response

@app.get("/health")
async def health_check(request: Request):
    resources = ResourceBudget.get_status()
    # Mask GPU details in non-local environments if necessary, but here we provide it.
    response = JSONResponse({
        "status": "healthy" if resources["healthy"] else "constrained",
        "service": "nutri-backend",
        "version": "1.3.1-hardened",
        "resources": resources
    })
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
