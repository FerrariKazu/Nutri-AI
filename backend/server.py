"""
Nutri Unified API Server
FastAPI backend with SSE streaming for the 13-phase Nutri pipeline.
"""

import uuid
import logging
import asyncio
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

# CORS Configuration - Explicit domains for production SSE stability
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nutri-ai-ochre.vercel.app",
        "https://nutri-qte326vny-ferrarikazus-projects.vercel.app",
        "http://localhost:5173",  # Local development
        "http://localhost:3000",  # Alternative local port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,  # Cache preflight for 10 minutes
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
    execution_mode: Optional[str] = None  # "fast", "sensory", "optimize", "research"

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
        # CRITICAL: Send immediate heartbeat to prevent browser timeout
        yield "event: status\ndata: {\"phase\": \"initializing\", \"message\": \"Connecting to Nutri backend...\"}\n\n"
        
        last_heartbeat = asyncio.get_event_loop().time()
        
        # Execute streamed with execution_mode
        async for event_dict in orchestrator.execute_streamed(
            session_id, 
            request.message, 
            pref_dict,
            execution_mode=request.execution_mode
        ):
            try:
                event_type = event_dict.get("type")
                content = event_dict.get("content")
                
                if event_type == "status":
                    # Status update (phase progress)
                    yield f"event: status\ndata: {json.dumps(content)}\n\n"
                    
                elif event_type == "reasoning":
                    # Legacy reasoning event
                    yield f"event: reasoning\ndata: {content}\n\n"
                    
                elif event_type == "token":
                    # LLM token stream
                    yield f"event: token\ndata: {content}\n\n"
                    
                elif event_type == "intermediate":
                    # Intermediate result (for OPTIMIZE profile)
                    yield f"event: intermediate\ndata: {json.dumps(content)}\n\n"
                    
                elif event_type == "final":
                    # Final result
                    yield f"event: final\ndata: {json.dumps(content)}\n\n"
                    
                elif event_type == "error":
                    # Error
                    yield f"event: error\ndata: {json.dumps({'error': content})}\n\n"
                    
                last_heartbeat = asyncio.get_event_loop().time()
                    
            except Exception as e:
                logger.error(f"Event formatting error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        # Send heartbeat if needed (every 15s)
        current_time = asyncio.get_event_loop().time()
        if current_time - last_heartbeat > 15:
            yield ":heartbeat\n\n"
            last_heartbeat = current_time
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nutri-backend", "version": "1.2.0"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
