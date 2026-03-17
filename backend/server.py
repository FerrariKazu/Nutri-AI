import uuid
import logging
import asyncio
import json
import time # Added for trace
from fastapi import FastAPI, Request, HTTPException, Response, Query
from backend.auth import get_authenticated_user, create_dev_token, DEV_MODE
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
ALLOWED_ORIGINS = [
    "https://nutri-ai-ochre.vercel.app",
    "https://chatdps.dpdns.org",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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


# Auth is now handled by backend.auth — JWT-based, no client-provided identity

# Components are initialized at startup

@app.get("/api/conversation")
async def get_conversation(request: Request, session_id: Optional[str] = Query(None)):
    """
    Returns the canonical conversation history and state for hydration.
    """
    user_id = get_authenticated_user(request)
    logger.debug(f"GET /api/conversation?session_id={session_id} [user={user_id}]")
    
    if not session_id:
        return JSONResponse({"messages": [], "status": "new_session"})
        
    # Security Gate
    if memory_store.exists(session_id) and not memory_store.check_ownership(session_id, user_id, dev_mode=DEV_MODE):
        # Only 403 if session EXISTS but doesn't belong to player
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        data = memory_store.get_conversation(session_id)
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Failed to fetch conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def list_conversations(request: Request):
    """
    List all available conversation sessions for the authenticated user.
    """
    user_id = get_authenticated_user(request)
    try:
        # 🔒 Filter by user_id
        data = memory_store.list_sessions(user_id=user_id)
        return JSONResponse({"conversations": data})
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation")
async def create_conversation(request: Request):
    """
    Explicitly create a new session ID bound to the user.
    """
    user_id = get_authenticated_user(request)
    new_id = f"sess_{uuid.uuid4().hex[:12]}_{int(uuid.uuid1().time)}"
    
    # Pre-warm the session in DB
    memory_store._update_activity(new_id)
    # 🔒 Bind to user immediately
    memory_store.set_user_id(new_id, user_id)
    
    logger.info(f"Created session {new_id} for user {user_id}")
    
    return JSONResponse({"session_id": new_id, "status": "created"})

@app.post("/api/dev-login")
async def dev_login(request: Request):
    """
    DEV-ONLY: Issues a signed JWT. Gated behind NUTRI_DEV_MODE.
    Accepts optional { user_id } body. Auto-generates if absent.
    """
    if not DEV_MODE:
        raise HTTPException(status_code=403, detail="Forbidden - Dev mode only")
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    user_id = body.get("user_id", None)
    result = create_dev_token(user_id)
    logger.info(f"[DEV-LOGIN] Token issued for {result['user_id']}")
    return JSONResponse(result)

@app.get("/api/chat/stream")
async def chat_stream(
    request: Request,
    message: str = Query(...),
    session_id: Optional[str] = None,
    execution_mode: Optional[str] = None,
    audience_mode: str = "casual",
    optimization_goal: str = "comfort",
    verbosity: str = "medium",
    run_id: Optional[str] = None
):
    """
    GET-based SSE endpoint for EventSource compatibility. Eliminates preflight.
    """
    user_id = get_authenticated_user(request)
    
    if not session_id:
        # If no session provided for stream, we can't really "create" one easily in GET SSE 
        # without client knowing the ID. 
        # Contract says: Client must have created session or provides one.
        raise HTTPException(status_code=400, detail="session_id is required")

    # Security Gate & Lazy Creation
    if not memory_store.ensure_session(session_id, user_id, dev_mode=DEV_MODE):
        logger.warning(f"AUTH FAILED - Access violation: user_id={user_id}, session_id={session_id}")
        raise HTTPException(status_code=403, detail="Access denied")
        
    pref_dict = {
        "audience_mode": audience_mode,
        "optimization_goal": optimization_goal,
        "verbosity": verbosity
    }
    
    return await handle_chat_execution(request, message, session_id, pref_dict, execution_mode, run_id=run_id)

@app.post("/api/chat")
async def chat_post(request: Request, payload: ChatRequest):
    """Standard POST endpoint for rich payloads"""
    user_id = get_authenticated_user(request)
    
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Security Gate & Lazy Creation
    if not memory_store.ensure_session(payload.session_id, user_id, dev_mode=DEV_MODE):
        raise HTTPException(status_code=403, detail="Access denied")
        
    pref_dict = payload.preferences.dict() if payload.preferences else {}
    return await handle_chat_execution(
        request, 
        payload.message, 
        payload.session_id, 
        pref_dict, 
        payload.execution_mode,
        run_id=None # POST payloads can be extended later if needed
    )

from backend.sse_utils import format_sse_event

async def handle_chat_execution(
    request: Request,
    message: str,
    session_id: str,
    preferences: Dict[str, Any],
    execution_mode: Optional[str],
    run_id: Optional[str] = None
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
                execution_mode=execution_mode,
                run_id=run_id
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
                await queue.put({"type": "ping", "content": {}, "ts": time.time(), "stream_id": session_id})
        except asyncio.CancelledError:
            pass

    # Start background tasks
    o_task = asyncio.create_task(run_orchestrator())
    h_task = asyncio.create_task(heartbeat())

    async def event_generator():
        nonlocal first_token_sent, done_sent
        try:
            # 🟢 Immediate READY event for connection verification
            yield format_sse_event("ready", {"content": "ok", "stream_id": session_id})
            
            while True:
                item = await queue.get()
                if item is None:
                    logger.info("[SSE] Sentinel received from orchestrator.")
                    if not done_sent:
                        logger.warning("[SSE] Forcing DONE emission before exit.")
                        yield format_sse_event("done", {"content": {"status": "forced_exit"}, "stream_id": session_id})
                        done_sent = True
                    break
                
                event_type = item.get("type", "token")
                content = item.get("content")
                
                # Log first token for TTT measurement
                if event_type == "token" and not first_token_sent:
                    logger.info("[SSE] First token sent to client.")
                    first_token_sent = True

                if event_type == "done":
                    done_sent = True
                    logger.info(f"[SSE] Emitting DONE event: {content}")

                if isinstance(item, dict) and "stream_id" not in item:
                    item["stream_id"] = session_id

                formatted_chunk = format_sse_event(event_type, item) # Pass whole item (already JSONized in sse_utils)
                
                # MANDATORY DEBUG LOGGING
                data_len = len(str(item.get("content", "")))
                if event_type != "token":
                    logger.debug(f"[SSE] Yielding {event_type} event (len={data_len})")
                
                yield formatted_chunk


                
        except GeneratorExit:
            logger.warning("[SSE] Client disconnected (GeneratorExit).")
            if not done_sent:
                logger.warning("[SSE] Emitting explicit ABORTED terminal event.")
                yield format_sse_event("done", {
                    "content": {"status": "aborted", "reason": "client_disconnect"},
                    "stream_id": session_id
                })
                done_sent = True
            raise
        except Exception as e:
            logger.error(f"[SSE] Critical Stream Error: {e}")
            yield format_sse_event("error_event", {"message": str(e), "stream_id": session_id})
            if not done_sent:
                yield format_sse_event("done", {
                    "content": {"status": "error", "reason": "exception", "message": str(e)},
                    "stream_id": session_id
                })
                done_sent = True
            raise
        finally:
            # The Final Safety Net
            if not done_sent:
                logger.error("[SSE] Loop finished without DONE! This is a regression.")
                try:
                    yield format_sse_event("done", {
                        "content": {"status": "forced", "reason": "sentinel_without_done"},
                        "stream_id": session_id
                    })
                    done_sent = True
                except Exception as final_e:
                    logger.error(f"[SSE] Failed to emit final DONE: {final_e}")
            
            # Dev/Invariants check
            if not done_sent:
                logger.error("🚨 CRITICAL: SSE stream closed without sending any terminal event!")
            
            logger.info("[SSE] Stream closing. Cleaning up tasks...")
            
            # Explicit Drain Guard: Ensure background tasks are dead before closing
            o_task.cancel()
            h_task.cancel()
            
            try:
                # Wait for internal cleanup to finish
                await asyncio.wait_for(
                    asyncio.gather(o_task, h_task, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("[SSE] Tasks failed to finalize within timeout. Forced close.")
            except Exception as e:
                logger.debug(f"Cleanup error (expected): {e}")

            # Final Queue Drain
            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue.task_done()
                except asyncio.QueueEmpty:
                    break

            logger.info("[SSE] All background tasks finalized and queue drained.")

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
    
    # Tuning Headers for Live Streaming
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Content-Type"] = "text/event-stream"
    
    return response


@app.get("/api/health")
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

@app.get("/api/debug/intelligence-schema")
async def debug_intelligence_schema():
    """
    Returns the SSOT schema for the Intelligence Panel to assist frontend development.
    """
    from backend.contracts.intelligence_schema import (
        Domain, EvidenceLevel, Origin, ConfidenceScale, MIN_RENDER_REQUIREMENTS, ONTOLOGY_VERSION
    )
    return JSONResponse({
        "version": ONTOLOGY_VERSION,
        "enums": {
            "domain": [d.value for d in Domain],
            "evidence_level": [el.value for el in EvidenceLevel],
            "origin": [o.value for o in Origin]
        },
        "scales": {
            "confidence": {
                "min": ConfidenceScale.MIN,
                "max": ConfidenceScale.MAX,
                "default_heuristic": ConfidenceScale.DEFAULT_HEURISTIC,
                "default_ontology": ConfidenceScale.DEFAULT_ONTOLOGY
            }
        },
        "min_render_requirements": MIN_RENDER_REQUIREMENTS
    })

@app.get("/api/debug/last-trace")
async def debug_last_trace():
    """
    Returns the absolute last trace emitted by the orchestrator.
    Useful for strict contract verification v1.2.
    """
    if not orchestrator.last_emitted_trace:
        return JSONResponse({"status": "empty", "message": "No trace emitted in this server session yet."})
    return JSONResponse(orchestrator.last_emitted_trace)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
