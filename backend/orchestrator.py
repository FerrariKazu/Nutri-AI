import json
import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, List, Callable, Optional

from backend.food_synthesis import NutriPipeline, IntentOutput
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile
from backend.execution_profiles import ExecutionProfile, ExecutionRouter
from backend.utils.response_formatter import ResponseFormatter
from backend.execution_plan import ExecutionPlan
from backend.memory_guard import MemoryGuard

# New Architecture Modules
from backend.meta_learner import MetaLearner, ExecutionPolicy
from backend.execution_dag import DAGScheduler, AgentNode

# Unified Persona Modules
from backend.response_modes import ResponseMode
from backend.mode_classifier import classify_response_mode
from backend.nutri_engine import NutriEngine

logger = logging.getLogger(__name__)

class NutriOrchestrator:
    """
    Orchestrates Nutri reasoning using a specific architecture:
    Meta-Learner Policy -> Speculative Execution -> Parallel DAG -> Progressive Streaming
    """

    def __init__(self, memory_store: SessionMemoryStore):
        self.pipeline = NutriPipeline(use_phase2=True)
        self.memory = memory_store
        self.meta_learner = MetaLearner()
        
        # Unified Response Engine
        self.engine = NutriEngine(self.pipeline.engine.llm, memory_store)
        
    async def execute_streamed(
        self, 
        session_id: str, 
        user_message: str, 
        preferences: Dict[str, Any],
        execution_mode: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the Nutri pipeline with true non-blocking streaming.
        Uses a background task to drive generation while the generator drains an event queue.
        """
        loop = asyncio.get_running_loop()
        event_queue = asyncio.Queue()
        
        def push_event(event_type: str, content: Any):
            logger.debug(f"[ORCH] push_event: {event_type}")
            # Safe way to put into queue from ANY thread
            asyncio.run_coroutine_threadsafe(
                event_queue.put({"type": event_type, "content": content}), 
                loop
            )

        def stream_callback(token: str):
            # This is called from the executor thread
            push_event("token", token)

        async def run_sync(func, *args, **kwargs):
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        async def orchestration_task():
            logger.info("[ORCH] Background task started.")
            done_emitted = False

            def push_done(status: str, message: str = ""):
                nonlocal done_emitted
                if not done_emitted:
                    push_event("done", {"status": status, "message": message})
                    done_emitted = True

            try:
                # 0. Meta-Learner Policy Decision
                policy = self.meta_learner.decide_policy(user_message, execution_mode)
                
                def emit_status(phase: str, msg: str):
                    if phase and msg and msg.strip():
                        logger.debug(f"[ORCH] Status update: {phase}")
                        push_event("status", {"phase": phase, "message": msg})

                logger.info(f"Orchestrating with Policy: {policy.profile.value}")
                emit_status("initializing", "Connecting to Nutri engine...")
                emit_status("starting", f"Thinking ({policy.profile.value})...")

                # 1. Context Preparation
                context = self.memory.get_context_string(session_id)
                augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message

                # 2. Intent Extraction
                emit_status("intent", "Understanding...")
                intent_raw = await run_sync(self.pipeline.intent_agent.extract, augmented_query)
                logger.info("[ORCH] Intent extracted.")
                
                if isinstance(intent_raw, dict):
                    try:
                        intent = IntentOutput(**intent_raw)
                    except Exception:
                        intent = IntentOutput()
                else:
                    intent = intent_raw

                # 3. Unified Mode Classification
                previous_mode = self.memory.get_response_mode(session_id)
                mode = classify_response_mode(user_message, intent, previous_mode)
                logger.info(f"🎯 Response Mode: {mode.value}")

                # 4. Mode-Based Execution
                if mode == ResponseMode.CONVERSATION:
                    emit_status("conversation", "Chatting...")
                    logger.info("[ORCH] Generating conversation response...")
                    await run_sync(self.engine.generate, session_id, user_message, mode, None, stream_callback=stream_callback)
                    logger.info("[ORCH] Generation finished.")
                    push_done("success")
                    return

                # B. DIAGNOSTIC or PROCEDURAL
                emit_status("retrieval", "Researching...")
                docs = await run_sync(self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2)
                
                emit_status("synthesis", "Analyzing..." if mode == ResponseMode.DIAGNOSTIC else "Creating...")
                recipe_result = await run_sync(self.pipeline.engine.synthesize, augmented_query, docs, intent, stream_callback=None)
                
                # 5. Parallel DAG
                dag_results = {}
                if policy.profile != ExecutionProfile.FAST:
                    emit_status("enhancement", "Analyzing & Refining...")
                    dag = DAGScheduler()
                    
                    if "sensory_model" in policy.enabled_agents:
                        dag.add_node(AgentNode(name="sensory", func=run_sync, args=[self.pipeline.predict_sensory, recipe_result]))
                    
                    dag.add_node(AgentNode(name="verification", func=run_sync, args=[self.pipeline.verify, recipe_result]))
                    
                    if "explanation" in policy.enabled_agents:
                        audience = preferences.get("audience_mode", "scientific")
                        dag.add_node(AgentNode(name="explanation", func=run_sync, args=[self.pipeline.explain_sensory, "sensory", audience], depends_on={"sensory"}))
                    
                    if "frontier" in policy.enabled_agents:
                        dag.add_node(AgentNode(name="frontier", func=run_sync, args=[self.pipeline.generate_sensory_frontier, recipe_result], is_luxury=True))
                        goal = preferences.get("optimization_goal", "balanced")
                        dag.add_node(AgentNode(name="selector", func=run_sync, args=[self.pipeline.select_sensory_variant, "frontier", UserPreferences(eating_style=goal)], depends_on={"frontier"}, is_luxury=True))

                    dag_results = await dag.execute()
                    
                    if "sensory" in dag_results:
                        push_event("enhancement", {"sensory_profile": dag_results["sensory"], "message": "Sensory profile modeled."})
                    if "explanation" in dag_results:
                        push_event("enhancement", {"explanation": dag_results["explanation"], "message": "Scientific explanation added."})

                # 6. Final Presentation
                emit_status("presentation", "Polishing...")
                final_data = {
                    "recipe": recipe_result,
                    "analysis": dag_results.get("explanation"),
                    "sensory": dag_results.get("sensory"),
                    "verification": dag_results.get("verification")
                }

                logger.info(f"[ORCH] Generating final tailored response in mode {mode.value}...")
                await run_sync(self.engine.generate, session_id, user_message, mode, final_data, stream_callback=stream_callback)
                logger.info("[ORCH] Generation complete.")
                push_done("success")

            except Exception as e:
                logger.error(f"Orchestration failure: {e}", exc_info=True)
                push_event("error_event", {"message": str(e), "phase": "orchestration", "status": "failed"})
                push_done("error", str(e))
            finally:
                logger.info("[ORCH] Ending task and pushing sentinels.")
                push_done("success") # Failsafe
                loop.call_soon_threadsafe(event_queue.put_nowait, None) # Sentinel

        # Start the background task - KEEP REFERENCE
        task = asyncio.create_task(orchestration_task())

        # Drain the event queue
        while True:
            event = await event_queue.get()
            if event is None:
                logger.info("[ORCH] Generator received sentinel, exiting.")
                break
            logger.debug(f"[ORCH] Yielding event: {event.get('type')}")
            yield event
