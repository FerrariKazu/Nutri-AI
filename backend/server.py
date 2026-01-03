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
    verbosity: str = "medium"
    explanations: bool = True
    streaming: bool = True

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    preferences: Optional[ChatPreferences] = Field(default_factory=ChatPreferences)

@app.post("/nutri/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Unified chat endpoint for Nutri. Supports streaming responses via SSE.
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Received chat request for session: {session_id}")

    async def event_generator():
        async for chunk in orchestrator.execute_streamed(session_id, request.message, request.preferences.dict()):
            # SSE Format: data: <json>\n\n
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Critical for Nginx/Proxies
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
