"""
Nutri Unified API Server
FastAPI backend with SSE streaming for the 13-phase Nutri pipeline.
"""

import uuid
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nutri Unified API", description="Integrated 13-Phase Food Synthesis Engine")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For debugging, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Components
memory_store = SessionMemoryStore()
orchestrator = NutriOrchestrator(memory_store)

class ChatPreferences(BaseModel):
    audience_mode: str = "casual"  # culinary | scientific | casual | technical
    optimization_goal: str = "comfort" # comfort | indulgent | performance
    verbosity: str = "medium" # low | medium | high

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    preferences: Optional[ChatPreferences] = Field(default_factory=ChatPreferences)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Unified production chat endpoint for Nutri.
    Supports persistent session memory and typed SSE streaming.
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Production chat request: {session_id}")

    # Inject memory context into preferences for the orchestrator
    pref_dict = request.preferences.dict()
    
    async def event_generator():
        # 1. Start Reasoning Phase
        yield "event: reasoning\ndata: Initializing Nutri scientific pipeline...\n\n"
        
        # 2. Execute Streamed
        async for chunk in orchestrator.execute_streamed(session_id, request.message, pref_dict):
            # The orchestrator should yield JSON strings
            # We wrap them in SSE events
            try:
                data = json.loads(chunk)
                if "stream" in data:
                    yield f"event: token\ndata: {data['stream']}\n\n"
                elif "phase" in data:
                    yield f"event: reasoning\ndata: {data.get('title', 'Processing...')}\n\n"
                elif "final" in data or "output" in data:
                    # Final result
                    output = data.get("output", data.get("final"))
                    yield f"event: final\ndata: {json.dumps({'content': output})}\n\n"
                elif "error" in data:
                    yield f"event: error\ndata: {data['error']}\n\n"
            except:
                # Fallback for raw strings (if any)
                yield f"data: {chunk}\n\n"
        
        # 3. Heartbeat logic is handled by the orchestrator or here?
        # Better handled by a background task if needed, but for now we rely on orchestrator.

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nutri-backend", "version": "1.1.0"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
