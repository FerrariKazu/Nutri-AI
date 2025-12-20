from __future__ import annotations

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*torch.utils._pytree.*')

from datetime import datetime
from pathlib import Path
import json
import uuid
import threading
from typing import Literal, List, Optional
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import psutil
import traceback

from llm import generate, build_prompt, generate_with_reflection
from prompts import SYSTEM_PROMPT
from topic_filter import is_food_related
from ingredient_constraints import analyze_ingredients, BASIC_PANTRY_ITEMS

from backend import data_loader, conversation_store
from backend.vector_store import index_builder, search as vector_search
from backend.routes import rag_api
from backend.agentic_rag import AgenticRAG
from backend.utils.response_formatter import ResponseFormatter

agent: Optional[AgenticRAG] = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
import re
logger = logging.getLogger(__name__)


class LoadingState:
    """Thread-safe loading state tracker for async resource initialization."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._states = {
            'recipes': False,
            'faiss_index': False,
            'agent': False,
            'llm': False,
            'background_indexes': False,
        }
        self._errors = {}
        self._progress = {}
    
    def set_loaded(self, resource: str, loaded: bool = True, error: str = None):
        with self._lock:
            self._states[resource] = loaded
            if error:
                self._errors[resource] = error
            elif resource in self._errors:
                del self._errors[resource]
            logger.info(f"📊 Resource '{resource}' loaded: {loaded}" + (f" (error: {error})" if error else ""))
    
    def is_loaded(self, resource: str) -> bool:
        with self._lock:
            return self._states.get(resource, False)
    
    def get_error(self, resource: str) -> Optional[str]:
        with self._lock:
            return self._errors.get(resource)
    
    def set_progress(self, resource: str, progress: float, message: str = ""):
        with self._lock:
            self._progress[resource] = {"progress": progress, "message": message}
    
    def get_status(self) -> dict:
        with self._lock:
            return {
                "loaded": dict(self._states),
                "errors": dict(self._errors),
                "progress": dict(self._progress),
                "ready": all(self._states.get(k, False) for k in ['recipes', 'llm']),
                "fully_ready": all(self._states.values())
            }


loading_state = LoadingState()


def filter_conversation_for_frontend(messages):
    if not messages:
        return []
    
    safe_messages = [
        msg for msg in messages 
        if msg.get('role') != 'system'
    ]
    return safe_messages


def extract_final_answer(text):
    if not text:
        return ""

    system_patterns = [
        "I am NUTRI-CHEM GPT",
        "My capabilities include",
        "Would you like to begin?",
        "Please specify your query",
        "System Prompt:",
        "CRITICAL OUTPUT INSTRUCTION:",
        "PRIORITY HIERARCHY",
        "CHEMISTRY MODE REQUIREMENTS",
        "MULTI-PASS INTERNAL REASONING",
        "RESPONSE PERSONALITY & STYLE",
        "RECIPE / COOKING INTEGRATION",
        "TOOLS AVAILABLE",
        "CITATION RULES",
        "OUTPUT FORMAT & USER-FRIENDLINESS",
        "SELF-CORRECTION LOOP",
        "FINAL MANDATE"
    ]
    
    for pattern in system_patterns:
        if pattern in text:
            parts = text.split(pattern)
            text = parts[-1]

    text = re.sub(r'<[/]?think>.*?</?think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[/]?thinking>.*?</?thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    text = re.sub(r'Thought:.*?(?=\n(?:Action:|Observation:|Final Answer:)|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'Action:.*?(?=\n(?:Thought:|Observation:|Final Answer:)|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'Observation:.*?(?=\n(?:Thought:|Action:|Final Answer:)|$)', '', text, flags=re.DOTALL)
    
    if "Final Answer:" in text:
        text = text.split("Final Answer:")[-1]
    
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(x) for x in [
            'I am ', 'My capabilities', 'Would you like', 'System Prompt:',
            'CRITICAL:', 'PRIORITY:', 'CHEMISTRY MODE:', 'MULTI-PASS:',
            'RESPONSE PERSONALITY:', 'RECIPE / COOKING:', 'TOOLS AVAILABLE:',
            'CITATION RULES:', 'OUTPUT FORMAT:', 'SELF-CORRECTION:', 'FINAL MANDATE:'
        ]):
            continue
        if stripped in ['Thought:', 'Action:', 'Observation:', 'Begin!', '...']:
            continue
            
        filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines)

    text = text.strip()
    text = re.sub(r'^[\s\.:\?]+', '', text)
    
    return text.strip()


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "web_recipes.jsonl"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def append_log(entry: dict) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        logger.warning(f"Failed to append log: {e}")


class RecipeRequest(BaseModel):
    ingredients: str = Field(..., description="Comma-separated list or free text describing ingredients on hand.")
    dislikes: str = Field("none", description="Comma-separated dislikes/allergies, or 'none'.")
    dietary_constraints: str = Field("none", description="Dietary constraints, e.g. vegetarian, halal, low-carb, or 'none'.")
    goal: str = Field(..., description="High-level goal, e.g. 'high-protein dinner', 'light lunch', 'dessert'.")
    innovation_level: int = Field(
        1,
        ge=1,
        le=3,
        description="Innovation level: 1 = safe, 2 = adventurous, 3 = experimental/wild.",
    )
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory")


class RecipeResponse(BaseModel):
    success: bool
    filter_refused: bool
    refusal_message: str | None = None
    reply: str | None = None
    error: str | None = None
    
    corrected: bool = False
    extras_removed: list[str] | None = None
    
    retrieved_recipes: Optional[List[dict]] = None
    rag_used: bool = False
    why_this: Optional[str] = None
    
    memory_used: bool = False
    session_id: Optional[str] = None
    loading_status: Optional[dict] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    message: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    filter_refused: bool
    refusal_message: str | None = None
    reply: str | None = None
    error: str | None = None
    session_id: Optional[str] = None
    loading_status: Optional[dict] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query, e.g. 'chicken dinner' or 'vegan dessert'")
    k: int = Field(5, ge=1, le=20, description="Number of results to return")


class SearchResponse(BaseModel):
    success: bool
    recipes: List[dict]
    scores: Optional[List[float]] = None
    error: Optional[str] = None
    using_semantic: bool = False
    loading_status: Optional[dict] = None


# ============================================================================
# EXTREME LOGGING MIDDLEWARE - Logs EVERY request with full details
# ============================================================================
class ExtremeLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs EVERY incoming request with extreme detail."""
    
    async def dispatch(self, request: Request, call_next):
        # Log EVERY incoming request
        logger.info("=" * 70)
        logger.info(f"🔵 INCOMING REQUEST: {request.method} {request.url.path}")
        logger.info(f"   Full URL: {request.url}")
        logger.info(f"   Client: {request.client.host if request.client else 'unknown'}")
        logger.info(f"   Headers: {dict(request.headers)}")
        logger.info(f"   Query Params: {dict(request.query_params)}")
        
        # Memory before
        try:
            mem_before = psutil.Process().memory_info().rss / 1024 / 1024
            logger.info(f"   Memory BEFORE: {mem_before:.2f} MB")
        except Exception as e:
            mem_before = 0
            logger.warning(f"   Memory check failed: {e}")
        
        try:
            response = await call_next(request)
            logger.info(f"🟢 RESPONSE: {response.status_code} for {request.method} {request.url.path}")
            return response
        except Exception as e:
            logger.exception(f"🔴 REQUEST FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise  # Crash loudly, don't recover silently
        finally:
            try:
                mem_after = psutil.Process().memory_info().rss / 1024 / 1024
                logger.info(f"   Memory AFTER: {mem_after:.2f} MB (Δ {mem_after - mem_before:+.2f} MB)")
            except:
                pass
            logger.info("=" * 70)


app = FastAPI(
    title="Nutri API",
    description="Backend API for the Nutri recipe inventor with RAG.",
    version="0.2.1",
)

# Add CORS middleware first (innermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add extreme logging middleware (outermost - runs first)
app.add_middleware(ExtremeLoggingMiddleware)

app.include_router(rag_api.router, prefix="/api", tags=["rag"])


@app.get("/")
async def read_root():
    status = loading_state.get_status()
    return {
        "message": "Nutri-AI Backend Online. For UI, please run the frontend separately.",
        "status": status
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint with loading status."""
    status = loading_state.get_status()
    return {
        "healthy": status["ready"],
        "fully_ready": status["fully_ready"],
        "status": status
    }


@app.on_event("startup")
async def startup_event():
    global agent
    logger.info("="*70)
    logger.info("🚀 Starting Nutri API (Fast-Start Mode)")
    logger.info("="*70)
    
    try:
        logger.info("📚 Loading recipe metadata...")
        data_loader.load_recipes()
        loading_state.set_loaded('recipes', True)
    except Exception as e:
        logger.error(f"❌ Failed to load recipes: {e}")
        loading_state.set_loaded('recipes', False, str(e))
    
    try:
        if not index_builder.index_exists():
            logger.warning("⚠️ FAISS index not found. Semantic search may be limited.")
            loading_state.set_loaded('faiss_index', False, "Index not found")
        else:
            logger.info("🔍 Loading legacy FAISS index (Sync)...")
            if vector_search.load_index():
                loading_state.set_loaded('faiss_index', True)
            else:
                loading_state.set_loaded('faiss_index', False, "Failed to load")
    except Exception as e:
        logger.error(f"❌ Failed to load FAISS index: {e}")
        loading_state.set_loaded('faiss_index', False, str(e))
    
    try:
        logger.info("🤖 Initializing Agentic RAG & Small Indexes...")
        agent = AgenticRAG()
        loading_state.set_loaded('agent', True)
        logger.info("✅ Agent initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Agent: {e}")
        loading_state.set_loaded('agent', False, str(e))
    
    try:
        logger.info("🔥 Warming up GPU (Lightweight)...")
        import llm
        llm.get_engine()
        _ = generate([{"role": "user", "content": "Startup"}], max_tokens=1)
        loading_state.set_loaded('llm', True)
        logger.info("✅ GPU warmed and ready")
    except Exception as e:
        logger.warning(f"⚠️ GPU warmup failed (non-critical): {e}")
        loading_state.set_loaded('llm', False, str(e))

    def background_load():
        try:
            if agent and hasattr(agent.tools, 'retriever') and hasattr(agent.tools.retriever, 'start_background_loading'):
                agent.tools.retriever.start_background_loading()
            loading_state.set_loaded('background_indexes', True)
        except Exception as e:
            logger.error(f"Background loading failed: {e}")
            loading_state.set_loaded('background_indexes', False, str(e))
    
    logger.info("⏳ Triggering background index loading...")
    threading.Thread(target=background_load, daemon=True).start()
            
    logger.info("="*70)
    logger.info("✨ Nutri API Ready! (Large indexes loading in background)")
    logger.info("="*70)


REFUSAL_SENTENCE = (
    "I only know about food, cooking, and nutrition. Is there something kitchen-related I can help you with?"
)

LOADING_MESSAGE = (
    "🔄 The system is still warming up. Please try again in a moment. "
    "Core features should be available within 30-60 seconds."
)


def ensure_valid_response(response: str, fallback: str = None) -> str:
    """Ensure a response is never empty or None."""
    if not response or not response.strip():
        return fallback or "I apologize, but I couldn't generate a response. Please try again."
    return response


@app.post("/api/recipe", response_model=RecipeResponse)
def create_recipe(req: RecipeRequest) -> RecipeResponse:
    timestamp = datetime.utcnow().isoformat() + "Z"
    session_id = req.session_id or str(uuid.uuid4())
    
    logger.info(f"📥 Recipe request received - session: {session_id[:8]}...")
    
    status = loading_state.get_status()
    if not status["ready"]:
        logger.warning("LLM not ready, returning loading message")
        return RecipeResponse(
            success=True,
            filter_refused=False,
            reply=LOADING_MESSAGE,
            error=None,
            session_id=session_id,
            loading_status=status
        )
    
    is_related = is_food_related(req.ingredients)
    logger.info(f"Topic Filter Check: '{req.ingredients}' -> {is_related}")
    
    if not is_related:
        append_log({
            "timestamp": timestamp,
            "event": "refused_by_filter",
            "source": "api",
            "request": req.dict(),
            "refusal_message": REFUSAL_SENTENCE,
            "session_id": session_id,
        })
        return RecipeResponse(
            success=True,
            filter_refused=True,
            refusal_message=REFUSAL_SENTENCE,
            reply=None,
            session_id=session_id,
            loading_status=status
        )

    memory_used = False
    memory_block = ""
    try:
        history = conversation_store.get_history(session_id)
        if history:
            memory_used = True
            memory_block = conversation_store.format_history_for_prompt(session_id)
            logger.info(f"Retrieved {len(history)} messages from session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to retrieve conversation history: {e}")

    user_message = f"ingredients: {req.ingredients}, goal: {req.goal}, constraints: {req.dietary_constraints}"
    try:
        conversation_store.append_user(session_id, user_message)
    except Exception as e:
        logger.warning(f"Failed to store user message: {e}")

    retrieved_recipes = []
    rag_used = False
    why_this = None
    
    if loading_state.is_loaded('faiss_index'):
        try:
            search_query = f"{req.ingredients} {req.goal} {req.dietary_constraints}".strip()
            logger.info(f"Searching for similar recipes: '{search_query}'")
            
            use_hybrid = req.innovation_level >= 2
            search_results = vector_search.semantic_search(search_query, k=5, use_hybrid=use_hybrid)
            
            if search_results:
                rag_used = True
                logger.info(f"Retrieved {len(search_results)} similar recipes via RAG")
                
                for recipe, score in search_results:
                    if isinstance(recipe, dict):
                        title = recipe.get('title', 'Unknown')
                        if 'snippet' in recipe or 'text' in recipe:
                            snippet = recipe.get('snippet', recipe.get('text', '')[:200])
                        else:
                            snippet = data_loader.build_context_for_llm(recipe)[:200]
                        
                        confidence = recipe.get('confidence', score)
                    else:
                        title = getattr(recipe, 'title', 'Unknown')
                        snippet = str(recipe)[:200]
                        confidence = score
                    
                    retrieved_recipes.append({
                        "title": title,
                        "snippet": snippet,
                        "context": data_loader.build_context_for_llm(recipe) if not isinstance(recipe, dict) else recipe.get('text', ''),
                        "score": score,
                        "confidence": confidence
                    })
                
                if len(retrieved_recipes) >= 2:
                    titles = [r['title'] for r in retrieved_recipes[:3]]
                    why_this = f"Selected because these recipes ({', '.join(titles[:2])}) match your ingredients and constraints."
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
    else:
        logger.info("FAISS index not loaded, skipping RAG retrieval")

    rag_context_block = ""
    if retrieved_recipes:
        rag_context_block = "=== RELEVANT RECIPES FOR INSPIRATION ===\n\n"
        for i, rec in enumerate(retrieved_recipes[:3], 1):
            rag_context_block += f"[Recipe #{i}]\n{rec['context']}\n\n"
        rag_context_block += "=== END OF REFERENCE RECIPES ==="

    user_context = f"""ingredients_on_hand: {req.ingredients}
dislikes: {req.dislikes}
dietary_constraints: {req.dietary_constraints}
goal: {req.goal}
innovation_level: {req.innovation_level}"""

    task_instruction = "Create a new recipe inspired by the reference recipes (if provided) using the listed ingredients. Follow the mobile-friendly formatting rules."

    user_prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        rag_block=rag_context_block,
        memory_block=memory_block,
        user_context=user_context,
        task_instruction=task_instruction
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        forbidden = [x.strip() for x in req.dislikes.split(',') if x.strip() and x.strip().lower() != 'none']
        constraints = {
            "dietary_constraints": req.dietary_constraints,
            "goal": req.goal
        }
        
        final_reply = generate_with_reflection(
            messages=messages,
            forbidden_ingredients=forbidden,
            constraints=constraints,
            max_retries=2
        )
        
        final_reply = ensure_valid_response(final_reply, f"I'd suggest a simple {req.goal} using {req.ingredients}. Please try again for a detailed recipe.")

        try:
            conversation_store.append_assistant(session_id, final_reply)
        except Exception as e:
            logger.warning(f"Failed to store assistant message: {e}")

        append_log({
            "timestamp": timestamp,
            "event": "recipe",
            "source": "api",
            "request": req.dict(),
            "session_id": session_id,
            "memory_used": memory_used,
            "rag_used": rag_used,
            "retrieved_count": len(retrieved_recipes),
            "final_reply": final_reply[:500],
        })

        logger.info(f"✅ Recipe generated successfully - {len(final_reply)} chars")
        
        return RecipeResponse(
            success=True,
            filter_refused=False,
            reply=final_reply,
            retrieved_recipes=retrieved_recipes if rag_used else None,
            rag_used=rag_used,
            why_this=why_this,
            memory_used=memory_used,
            session_id=session_id,
            loading_status=status
        )

    except Exception as exc:
        error_text = str(exc)
        logger.error(f"❌ Recipe generation failed: {error_text}")
        append_log({
            "timestamp": timestamp,
            "event": "error",
            "source": "api",
            "request": req.dict(),
            "session_id": session_id,
            "error": error_text,
        })
        return RecipeResponse(
            success=False,
            filter_refused=False,
            reply="I apologize, but I encountered an error generating your recipe. Please try again.",
            error=error_text,
            session_id=session_id,
            loading_status=status
        )


@app.post("/api/search", response_model=SearchResponse)
def search_recipes(req: SearchRequest) -> SearchResponse:
    logger.info(f"📥 Search request: '{req.query}' (k={req.k})")
    
    status = loading_state.get_status()
    
    if not loading_state.is_loaded('faiss_index') and not loading_state.is_loaded('recipes'):
        return SearchResponse(
            success=True,
            recipes=[],
            scores=[],
            error="Search index is still loading. Please try again in a moment.",
            using_semantic=False,
            loading_status=status
        )
    
    try:
        search_results = vector_search.semantic_search(req.query, k=req.k)
        
        if not search_results:
            logger.info("No search results found")
            return SearchResponse(
                success=True,
                recipes=[],
                scores=[],
                using_semantic=loading_state.is_loaded('faiss_index'),
                loading_status=status
            )
        
        recipes = []
        scores = []
        
        for recipe, score in search_results:
            title = recipe.get('title', 'Unknown Recipe')
            nutrition = data_loader.get_nutrition_summary(recipe)
            tags = recipe.get('diet_tags', [])
            
            ingredients = recipe.get('ingredients', [])
            ingredient_names = [
                ing.get('normalized', ing.get('raw', 'unknown'))
                for ing in ingredients[:10]
            ]
            
            recipes.append({
                "title": title,
                "ingredients": ingredient_names,
                "nutrition": nutrition,
                "tags": tags,
                "score": score
            })
            scores.append(score)
        
        is_semantic = vector_search.is_loaded()
        logger.info(f"✅ Returning {len(recipes)} results (semantic: {is_semantic})")
        
        return SearchResponse(
            success=True,
            recipes=recipes,
            scores=scores,
            using_semantic=is_semantic,
            loading_status=status
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return SearchResponse(
            success=False,
            recipes=[],
            error=f"Search error: {str(e)}. Please try again.",
            using_semantic=False,
            loading_status=status
        )


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    timestamp = datetime.utcnow().isoformat() + "Z"
    session_id = req.session_id or str(uuid.uuid4())
    
    logger.info(f"📥 Chat request received - session: {session_id[:8]}...")
    
    status = loading_state.get_status()
    if not status["ready"]:
        logger.warning("LLM not ready, returning loading message")
        return ChatResponse(
            success=True,
            filter_refused=False,
            reply=LOADING_MESSAGE,
            session_id=session_id,
            loading_status=status
        )
    
    if req.message:
        user_message = req.message
    elif req.messages:
        last_user = None
        for msg in reversed(req.messages):
            if msg.role == "user":
                last_user = msg
                break
        if not last_user:
            return ChatResponse(
                success=False,
                filter_refused=False,
                error="No user message found",
                reply="Please provide a message.",
                session_id=session_id,
                loading_status=status
            )
        user_message = last_user.content
    else:
        return ChatResponse(
            success=False,
            filter_refused=False,
            error="No message provided",
            reply="Please provide a message.",
            session_id=session_id,
            loading_status=status
        )

    has_history = False
    try:
        history = conversation_store.get_history(session_id)
        has_history = len(history) > 0
    except:
        pass
    
    if not has_history and not is_food_related(user_message):
        refusal = (
            "That's outside my kitchen expertise! But I'd love to help with anything food-related — "
            "recipes, techniques, nutrition, or the science behind cooking. What can I whip up for you?"
        )
        append_log({
            "timestamp": timestamp,
            "event": "chat_refused_by_filter",
            "source": "api",
            "message": user_message,
            "session_id": session_id,
            "refusal_message": refusal,
        })
        return ChatResponse(
            success=True,
            filter_refused=True,
            refusal_message=refusal,
            session_id=session_id,
            loading_status=status
        )

    logger.info(f"🔍 Building messages for LLM")
    llm_messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    if req.messages:
        for msg in req.messages:
            if msg.role in ("user", "assistant"):
                # VALIDATION: Ensure content is a non-empty string
                content = str(msg.content).strip() if msg.content else ""
                if content:
                    llm_messages.append({"role": msg.role, "content": content})
    else:
        # VALIDATION: Ensure user_message is non-empty
        content = str(user_message).strip()
        if content:
            llm_messages.append({"role": "user", "content": content})

    # FINAL VALIDATION: Ensure we have at least one user message
    has_user_message = any(m["role"] == "user" and m["content"].strip() for m in llm_messages)
    if not has_user_message:
         logger.warning("⚠️ No valid user message found after validation. Aborting LLM call.")
         return ChatResponse(
            success=False,
            filter_refused=False,
            error="No valid user message provided",
            reply="Please provide a message to continue.",
            session_id=session_id,
            loading_status=status
        )

    try:
        logger.info(f"🔍 Sending {len(llm_messages)} messages to LLM")
        logger.debug(f"Payload: {json.dumps(llm_messages, ensure_ascii=False)}")
        reply_text = generate(llm_messages, max_tokens=4096)
        
        logger.debug(f"Raw LLM reply: {reply_text[:100]}...")
        
        reply_text = extract_final_answer(reply_text)
        logger.debug(f"Extracted answer: {reply_text[:100]}...")
        
        reply_text = ensure_valid_response(reply_text, "I apologize, but I couldn't generate a proper response. Please try again.")
        
        logger.info(f"✅ Chat response generated - {len(reply_text)} chars")
             
    except Exception as exc:
        error_text = str(exc)
        logger.error(f"❌ Chat generation failed: {error_text}")
        append_log({
            "timestamp": timestamp,
            "event": "chat_error",
            "source": "api",
            "message": user_message,
            "session_id": session_id,
            "error": error_text,
        })
        return ChatResponse(
            success=False,
            filter_refused=False,
            reply="I apologize, but I encountered an error. Please try again.",
            error=error_text,
            session_id=session_id,
            loading_status=status
        )

    append_log({
        "timestamp": timestamp,
        "event": "chat",
        "source": "api",
        "message": user_message,
        "session_id": session_id,
        "reply_length": len(reply_text),
    })

    return ChatResponse(
        success=True,
        filter_refused=False,
        reply=ResponseFormatter.format_response(reply_text),
        session_id=session_id,
        loading_status=status
    )


@app.get("/api/stats")
async def get_stats():
    status = loading_state.get_status()
    return {
        "recipes": 142893,
        "ingredients": "8.5M+",
        "papers": 24109,
        "loading_status": status
    }


class ModeRequest(BaseModel):
    mode: str


@app.post("/api/mode")
async def set_mode(req: ModeRequest):
    logger.info(f"Client switched to mode: {req.mode}")
    return {"success": True, "mode": req.mode}


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    timestamp = datetime.utcnow().isoformat() + "Z"
    session_id = req.session_id or str(uuid.uuid4())
    
    status = loading_state.get_status()
    if not status["ready"]:
        async def loading_gen():
            yield f"data: {json.dumps({'type': 'content', 'token': LOADING_MESSAGE})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(loading_gen(), media_type="text/event-stream")
    
    if req.message:
        user_message = req.message
    elif req.messages:
        user_message = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    else:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'content', 'token': 'Please provide a message.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if req.messages:
        for msg in req.messages:
            if msg.role in ("user", "assistant"):
                llm_messages.append({"role": msg.role, "content": msg.content})
    else:
        llm_messages.append({"role": "user", "content": user_message})

    async def event_generator():
        yielded_any = False
        try:
            from llm import stream
            
            buffer = ""
            in_final_answer = False
            system_phrases = ["I am NUTRI-CHEM GPT", "System Prompt:", "My capabilities include"]
            
            async for chunk in run_in_thread(stream, llm_messages):
                buffer += chunk
                
                if "Final Answer:" in buffer and not in_final_answer:
                    in_final_answer = True
                    pre, post = buffer.split("Final Answer:", 1)
                    buffer = post
                    buffer = re.sub(r'<[/]?think>.*?</?think>', '', buffer, flags=re.DOTALL | re.IGNORECASE)
                    buffer = re.sub(r'<[/]?thinking>.*?</?thinking>', '', buffer, flags=re.DOTALL | re.IGNORECASE)
                    
                if in_final_answer:
                    if buffer:
                        yield f"data: {json.dumps({'type': 'content', 'token': buffer})}\n\n"
                        yielded_any = True
                        buffer = ""
                        
            if not in_final_answer and buffer:
                cleaned = buffer
                for phrase in system_phrases:
                    if phrase in cleaned:
                        cleaned = cleaned.split(phrase)[-1]
                        cleaned = re.sub(r'^[\s\.:\?]+', '', cleaned)
                
                cleaned = re.sub(r'</?think>.*?$', '', cleaned, flags=re.DOTALL)
                cleaned = re.sub(r'Thought:.*?(?=\n|$)', '', cleaned)
                cleaned = re.sub(r'Action:.*?(?=\n|$)', '', cleaned)
                cleaned = re.sub(r'Observation:.*?(?=\n|$)', '', cleaned)
                
                if cleaned.strip():
                    yield f"data: {json.dumps({'type': 'content', 'token': cleaned.strip()})}\n\n"
                    yielded_any = True
            
            if not yielded_any:
                yield f"data: {json.dumps({'type': 'content', 'token': 'I apologize, but I could not generate a response. Please try again.'})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield f"data: {json.dumps({'type': 'content', 'token': f'Error: {str(e)}. Please try again.'})}\n\n"
            yield "data: [DONE]\n\n"

    async def run_in_thread(fn, *args):
        loop = asyncio.get_event_loop()
        import queue
        q = queue.Queue()
        
        def producer():
            try:
                for item in fn(*args):
                    q.put(item)
                q.put(None)
            except Exception as e:
                q.put(e)
        
        loop.run_in_executor(None, producer)
        
        timeout_count = 0
        max_timeout = 3000
        
        while timeout_count < max_timeout:
            try:
                item = q.get_nowait()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
                timeout_count = 0
            except queue.Empty:
                await asyncio.sleep(0.01)
                timeout_count += 1
        
        if timeout_count >= max_timeout:
            logger.warning("Stream timeout reached")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


from scripts.pdr_rag import query_pdr

class PDRQuery(BaseModel):
    query: str

class PDRResponse(BaseModel):
    answer: str
    sources: list[dict]
    context_used: str | None = None
    error: str | None = None

@app.post("/api/pdr", response_model=PDRResponse)
async def pdr_query(body: PDRQuery):
    try:
        result = query_pdr(body.query)
        
        answer = result.get("answer", "")
        if not answer:
            answer = "Unable to find relevant information. Please try a different query."
        
        return PDRResponse(
            answer=answer,
            sources=result.get("sources", []),
            context_used=result.get("context_used"),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"PDR query failed: {e}")
        return PDRResponse(
            answer="Query processing failed. Please try again.",
            sources=[],
            error=str(e)
        )


class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    k: int = Field(5, ge=1, le=20, description="Number of results")
    use_hybrid: bool = Field(False, description="Use hybrid search (semantic + lexical + reranking)")


class EnrichedRecipeResult(BaseModel):
    id: str
    title: str
    text: str
    snippet: str = ""
    source_id: str = ""
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    original_score: float = 0.0
    rerank_score: float = 0.0
    confidence: float = 0.0


class HybridSearchResponse(BaseModel):
    success: bool
    recipes: List[EnrichedRecipeResult]
    using_semantic: bool = False
    error: Optional[str] = None
    why_this: Optional[str] = None
    loading_status: Optional[dict] = None


@app.post("/api/hybrid_search", response_model=HybridSearchResponse)
async def hybrid_search_endpoint(req: HybridSearchRequest):
    status = loading_state.get_status()
    
    try:
        results_raw = vector_search.semantic_search(
            req.query, 
            k=req.k, 
            use_hybrid=req.use_hybrid
        )
        
        if not results_raw:
            return HybridSearchResponse(
                success=True,
                recipes=[],
                using_semantic=loading_state.is_loaded('faiss_index'),
                loading_status=status
            )
        
        recipes = []
        for item, score in results_raw:
            if isinstance(item, dict):
                recipes.append(EnrichedRecipeResult(
                    id=item.get('id', ''),
                    title=item.get('title', 'Untitled'),
                    text=item.get('text', ''),
                    snippet=item.get('snippet', item.get('text', '')[:200] + '...'),
                    source_id=item.get('id', ''),
                    original_score=score,
                    semantic_score=item.get('semantic_score', score if not req.use_hybrid else 0),
                    lexical_score=item.get('lexical_score', 0),
                    rerank_score=item.get('rerank_score', score) if req.use_hybrid else score,
                    confidence=item.get('confidence', score)
                ))
            else:
                recipe_text = item.get('title', '') + '. ' + item.get('instructions', '')
                recipes.append(EnrichedRecipeResult(
                    id=str(item.get('id', '')),
                    title=item.get('title', 'Untitled'),
                    text=recipe_text,
                    snippet=recipe_text[:200] + '...',
                    source_id=str(item.get('id', '')),
                    original_score=score,
                    rerank_score=score,
                    confidence=score
                ))
        
        why_this = None
        if len(recipes) >= 3 and req.use_hybrid:
            top_titles = [r.title for r in recipes[:3]]
            why_this = f"Selected because these recipes mention similar ingredients and cooking methods: {', '.join(top_titles[:2])}"
        
        log_retrieval(req.query, recipes, req.use_hybrid)
        
        return HybridSearchResponse(
            success=True,
            recipes=recipes,
            using_semantic=True,
            why_this=why_this,
            loading_status=status
        )
    
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return HybridSearchResponse(
            success=False,
            recipes=[],
            error=f"Search error: {str(e)}",
            loading_status=status
        )


class FeedbackRequest(BaseModel):
    query: str
    result_id: str
    feedback: str
    comment: Optional[str] = None
    timestamp: Optional[str] = None


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    try:
        feedback_entry = {
            "timestamp": req.timestamp or datetime.utcnow().isoformat() + "Z",
            "query": req.query,
            "result_id": req.result_id,
            "feedback": req.feedback,
            "comment": req.comment
        }
        
        feedback_file = Path("logs/feedback.jsonl")
        feedback_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
        
        logger.info(f"Feedback submitted for query: {req.query[:50]}...")
        return {"status": "success", "message": "Thank you for your feedback!"}
    
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/clear")
async def clear_session(request: dict):
    try:
        session_id = request.get("session_id")
        if session_id:
            if hasattr(conversation_store, 'clear_session'):
                conversation_store.clear_session(session_id)
            logger.info(f"Session cleared: {session_id}")
        
        return {"status": "success", "message": "Session cleared"}
    
    except Exception as e:
        logger.error(f"Session clear error: {e}")
        return {"status": "success", "message": "Session cleared client-side"}


def log_retrieval(query: str, results: List[EnrichedRecipeResult], used_hybrid: bool):
    try:
        retrieval_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": query,
            "used_hybrid": used_hybrid,
            "num_results": len(results),
            "candidates": [
                {
                    "id": r.id,
                    "title": r.title,
                    "rerank_score": r.rerank_score,
                    "confidence": r.confidence
                }
                for r in results[:10]
            ],
            "chosen_sources": [r.id for r in results[:3]]
        }
        
        retrieval_log = LOG_DIR / "retrievals.jsonl"
        with retrieval_log.open("a", encoding="utf-8") as f:
            json.dump(retrieval_entry, f, ensure_ascii=False)
            f.write("\n")
    
    except Exception as e:
        logger.warning(f"Retrieval logging failed: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                request = json.loads(data)
                user_message = request.get('message', '')
                
                if not user_message:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Please provide a message."
                    }))
                    continue
                
                status = loading_state.get_status()
                if not status["ready"]:
                    await websocket.send_text(json.dumps({
                        "type": "response_chunk",
                        "chunk": LOADING_MESSAGE
                    }))
                    await websocket.send_text(json.dumps({"type": "complete"}))
                    continue
                
                await websocket.send_text(json.dumps({
                    "type": "thinking",
                    "message": "🤔 Analyzing your request..."
                }))
                
                global agent
                
                if agent:
                    queue = asyncio.Queue()
                    loop = asyncio.get_event_loop()
                    response_yielded = False
                    
                    def run_agent_in_thread():
                        try:
                            for event in agent.stream_query(user_message):
                                loop.call_soon_threadsafe(queue.put_nowait, event)
                            
                            loop.call_soon_threadsafe(queue.put_nowait, {"type": "complete"})
                            
                        except Exception as e:
                            logger.error(f"Error in agent thread: {e}")
                            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})

                    import threading
                    thread = threading.Thread(target=run_agent_in_thread, daemon=True)
                    thread.start()

                    try:
                        timeout_count = 0
                        max_timeout = 6000
                        
                        while timeout_count < max_timeout:
                            try:
                                event = await asyncio.wait_for(queue.get(), timeout=0.01)
                                timeout_count = 0
                                
                                if event.get('type') == 'complete':
                                    if not response_yielded:
                                        await websocket.send_text(json.dumps({
                                            "type": "response_chunk",
                                            "chunk": "I apologize, but I couldn't generate a response. Please try again."
                                        }))
                                    await websocket.send_text(json.dumps({"type": "complete"}))
                                    break
                                    
                                msg = {}
                                if event.get('type') == 'thinking':
                                    msg = {"type": "thinking", "message": event['content'], "stage": event.get('stage', 'reasoning')}
                                elif event.get('type') == 'thinking_chunk':
                                    msg = {"type": "thinking_chunk", "chunk": event['chunk']}
                                elif event.get('type') == 'token':
                                    msg = {"type": "response_chunk", "chunk": event['content']}
                                    response_yielded = True
                                elif event.get('type') == 'error':
                                    msg = {"type": "error", "message": event.get('content', 'Unknown error')}
                                
                                if msg:
                                    await websocket.send_text(json.dumps(msg))
                            except asyncio.TimeoutError:
                                timeout_count += 1
                        
                        if timeout_count >= max_timeout:
                            logger.warning("WebSocket stream timeout")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "Request timed out. Please try again."
                            }))
                            await websocket.send_text(json.dumps({"type": "complete"}))
                    
                    except WebSocketDisconnect:
                        logger.info("Client disconnected during stream")
                        return
                    except Exception as e:
                        logger.error(f"Error in WebSocket loop: {e}")
                        try:
                            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                            await websocket.send_text(json.dumps({"type": "complete"}))
                        except:
                            pass
                else:
                    await websocket.send_text(json.dumps({
                        "type": "response_chunk", 
                        "chunk": "The AI agent is still initializing. Please try again in a moment."
                    }))
                    await websocket.send_text(json.dumps({"type": "complete"}))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON format"}))
                
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)