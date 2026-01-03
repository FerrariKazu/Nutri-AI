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

@app.get("/nutri/chat")
@app.post("/nutri/chat")
async def chat_endpoint(request: Request):
    """
    Unified chat endpoint for Nutri. Supports streaming responses via SSE.
    Accepts POST (JSON body) or GET (Query parameters) for EventSource compatibility.
    """
    # 1. Extract inputs based on method
    if request.method == "POST":
        try:
            body = await request.json()
            message = body.get("message")
            session_id = body.get("session_id")
            preferences = body.get("preferences", {})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        # GET (Native EventSource)
        message = request.query_params.get("message")
        session_id = request.query_params.get("session_id")
        # Support optional preferences as individual flags or JSON string
        verbosity = request.query_params.get("verbosity", "medium")
        preferences = {"verbosity": verbosity, "explanations": True, "streaming": True}

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    session_id = session_id or str(uuid.uuid4())
    logger.info(f"Received {request.method} chat request for session: {session_id}")

    async def event_generator():
        async for chunk in orchestrator.execute_streamed(session_id, message, preferences):
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
