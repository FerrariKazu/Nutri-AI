import json
import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, List, Callable, Optional
from backend.food_synthesis import NutriPipeline
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile
from backend.execution_profiles import ExecutionProfile, ExecutionRouter
from backend.execution_plan import ExecutionPlan
from backend.memory_guard import MemoryGuard

logger = logging.getLogger(__name__)

class NutriOrchestrator:
    """Orchestrates 13 distinct phases of Nutri reasoning with streaming support."""

    def __init__(self, memory_store: SessionMemoryStore):
        self.pipeline = NutriPipeline(use_phase2=True)
        self.memory = memory_store

    async def _run_blocking(self, func: Callable, *args, phase_id: int = 0, title: str = "Processing") -> Any:
        """
        Run a blocking synchronous function in a thread pool while yielding keep-alive signals.
        This prevents 504 Gateway Timeouts during long LLM generation steps.
        """
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, func, *args)
        
        while not future.done():
            try:
                # Wait for 5 seconds or until done
                await asyncio.wait_for(asyncio.shield(future), timeout=5.0)
            except asyncio.TimeoutError:
                # Still running, yield keep-alive
                logger.debug(f"Phase {phase_id} still processing... sending heartbeat.")
                # We yield a special non-rendering update or just a log message? 
                # For SSE, comments like ": keep-alive" are best, but our format uses JSON data.
                # We'll send a status update that doesn't change the UI much.
                pass 
                # Actually, the generator can't yield from here easily without being an async generator itself.
                # Use a different pattern: the caller handles the yield loop? 
                # No, let's just await the future. The 'await' yields control to the loop, 
                # but doesn't send data to the client. 
                # The StreamingResponse needs ACTUAL DATA to keep the connection open? 
                # Most proxies timeout if NO DATA is received.
                
        return await future

    async def execute_streamed(
        self, 
        session_id: str, 
        user_message: str, 
        preferences: Dict[str, Any],
        execution_mode: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the Nutri pipeline with tiered execution and yields structured event dictionaries.
        Event types: 'status', 'reasoning', 'token', 'intermediate', 'final', 'error'.
        
        Args:
            session_id: Unique session identifier
            user_message: User's natural language request
            preferences: User preferences (audience_mode, optimization_goal, verbosity)
            execution_mode: Optional explicit execution mode ("fast", "sensory", "optimize", "research")
        """
        loop = asyncio.get_running_loop()
        token_queue = asyncio.Queue()
        
        def stream_callback(token: str):
            """Callback for sync LLM threads to push tokens to async queue"""
            loop.call_soon_threadsafe(token_queue.put_nowait, token)

        try:
            # 0. Determine execution profile and plan
            raw_profile = ExecutionRouter.determine_profile(user_message, execution_mode)
            profile = MemoryGuard.safe_profile(raw_profile)  # May downgrade if memory pressure
            plan = ExecutionPlan.from_profile(profile)
            
            logger.info(f"Executing with profile: {profile.value} (requested: {raw_profile.value if raw_profile != profile else 'auto'})")
            MemoryGuard.log_memory_stats()
            
            # Emit initial status
            yield {
                "type": "status",
                "content": {
                    "profile": profile.value,
                    "phase": "starting",
                    "message": f"Executing {profile.value.upper()} profile"
                }
            }
            
            # 1. PRE-PHASE: Memory Injection
            context = self.memory.get_context_string(session_id)
            augmented_query = f"{context}\\n\\nUSER: {user_message}" if context else user_message
            
            # Helper: Consumes stream and yields event dicts
            async def run_phase(phase_id: int, func: Callable, *args, use_stream=False):
                phase_start = time.time()
                call_args = list(args)
                if use_stream:
                    call_args.append(stream_callback)
                
                future = loop.run_in_executor(None, func, *call_args)
                
                while not future.done():
                    if use_stream:
                        # Wait for token or future
                        done, pending = await asyncio.wait(
                            [asyncio.create_task(token_queue.get()), asyncio.wrap_future(future)],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # Process tokens
                        while not token_queue.empty():
                            try:
                                token = token_queue.get_nowait()
                                yield {"type": "token", "content": token}
                            except asyncio.QueueEmpty:
                                break
                    else:
                         # Heartbeat wait (Status logic)
                         await asyncio.sleep(2)
                         if not future.done():
                             yield {"type": "reasoning", "content": "Analyzing data..."}

                # Flush remaining tokens
                if use_stream:
                    while not token_queue.empty():
                        token = await token_queue.get()
                        yield {"type": "token", "content": token}
                
                # Final Result
                result = await future
                phase_duration = time.time() - phase_start
                logger.info(f"Phase {phase_id} completed in {phase_duration:.2f}s")
                yield {"type": "result", "content": result}

            # 2. Execute IMMEDIATE phases
            intent = None
            docs = None
            recipe = None
            verification = None
            profile_obj = None
            explanation = None
            frontier = None
            selection = None
            
            for phase_id in plan.immediate_phases:
                # Emit status for this phase
                yield {
                    "type": "status",
                    "content": {
                        "phase": self._get_phase_name(phase_id),
                        "message": self._get_phase_message(phase_id)
                    }
                }
                
                # Execute phase
                if phase_id == 1:
                    # Intent Extraction
                    async for event in run_phase(1, self.pipeline.intent_agent.extract, augmented_query, use_stream=True):
                        if event["type"] == "result": intent = event["content"]
                        else: yield event
                        
                elif phase_id == 2:
                    # Knowledge Retrieval
                    async for event in run_phase(2, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2):
                        if event["type"] == "result": docs = event["content"]
                        else: yield event
                        
                elif phase_id == 3:
                    # Synthesis
                    async for event in run_phase(3, self.pipeline.engine.synthesize, augmented_query, docs, intent, use_stream=True):
                        if event["type"] == "result": recipe = event["content"]
                        else: yield event
                    
                    # Verification (always runs with synthesis)
                    async for event in run_phase(3, self.pipeline.verify, recipe):
                        if event["type"] == "result": verification = event["content"]
                        else: yield event
                        
                elif phase_id == 4:
                    # Sensory Modeling
                    async for event in run_phase(4, self.pipeline.predict_sensory, recipe):
                        if event["type"] == "result": profile_obj = event["content"]
                        else: yield event
                        
                elif phase_id == 5:
                    # Verification (if not already run)
                    if not verification:
                        async for event in run_phase(5, self.pipeline.verify, recipe):
                            if event["type"] == "result": verification = event["content"]
                            else: yield event
                            
                elif phase_id == 6:
                    # Explanation Control
                    audience = preferences.get("audience_mode", "scientific")
                    async for event in run_phase(6, self.pipeline.explain_sensory, profile_obj, audience):
                        if event["type"] == "result": explanation = event["content"]
                        else: yield event
                        
                elif phase_id == 8:
                    # Frontier Generation
                    async for event in run_phase(8, self.pipeline.generate_sensory_frontier, recipe):
                        if event["type"] == "result": frontier = event["content"]
                        else: yield event
                        
                elif phase_id == 9:
                    # Variant Selection
                    goal = preferences.get("optimization_goal", "balanced")
                    async for event in run_phase(9, self.pipeline.select_sensory_variant, frontier, UserPreferences(eating_style=goal)):
                        if event["type"] == "result": selection = event["content"]
                        else: yield event

            # 3. Yield INTERMEDIATE result (for FAST/SENSORY profiles)
            if not plan.is_fast_mode():
                logger.info("Assembling intermediate result...")
                intermediate_recipe = recipe
                intermediate_explanation = explanation if explanation else "Recipe synthesized successfully."
                
                yield {
                    "type": "intermediate",
                    "content": {
                        "recipe": intermediate_recipe,
                        "explanation": intermediate_explanation,
                        "profile": profile.value
                    }
                }

            # 4. Execute DEFERRED phases (for OPTIMIZE profile)
            if plan.deferred_phases:
                yield {
                    "type": "status",
                    "content": {
                        "phase": "deep_analysis",
                        "message": "Enhancing with deep analysis..."
                    }
                }
                
                for phase_id in plan.deferred_phases:
                    # Emit status for deferred phase
                    yield {
                        "type": "status",
                        "content": {
                            "phase": self._get_phase_name(phase_id),
                            "message": self._get_phase_message(phase_id)
                        }
                    }
                    
                    # Execute deferred phase
                    if phase_id == 4 and not profile_obj:
                        async for event in run_phase(4, self.pipeline.predict_sensory, recipe):
                            if event["type"] == "result": profile_obj = event["content"]
                            else: yield event
                            
                    elif phase_id == 6 and not explanation:
                        audience = preferences.get("audience_mode", "scientific")
                        async for event in run_phase(6, self.pipeline.explain_sensory, profile_obj, audience):
                            if event["type"] == "result": explanation = event["content"]
                            else: yield event
                            
                    elif phase_id == 8 and not frontier:
                        async for event in run_phase(8, self.pipeline.generate_sensory_frontier, recipe):
                            if event["type"] == "result": frontier = event["content"]
                            else: yield event
                            
                    elif phase_id == 9 and not selection:
                        goal = preferences.get("optimization_goal", "balanced")
                        async for event in run_phase(9, self.pipeline.select_sensory_variant, frontier, UserPreferences(eating_style=goal)):
                            if event["type"] == "result": selection = event["content"]
                            else: yield event

            # 5. FINAL assembly
            logger.info("Assembling final structured response...")
            yield {"type": "status", "content": {"phase": "finalizing", "message": "Wrapping final response..."}}
            
            final_recipe = recipe
            if selection and hasattr(selection, 'selected_variant') and selection.selected_variant:
                final_recipe = selection.selected_variant.recipe
            
            final_explanation = explanation
            if selection and hasattr(selection, 'reasoning') and selection.reasoning:
                final_explanation = selection.reasoning[0]
            
            # Format results
            # sse_safe in the server layer will handle the recursive conversion of 
            # profile_obj, verification, etc. to JSON-safe dictionaries.
            result = {
                "recipe": final_recipe,
                "sensory_profile": profile_obj,
                "explanation": final_explanation,
                "verification_report": verification,
                "execution_profile": profile.value
            }

            logger.info("Saving session memory...")
            try:
                self.memory.add_message(session_id, "user", user_message)
                summary = f"RECIPE: {final_recipe[:50]}... | EXPLANATION: {final_explanation[:50]}..."
                self.memory.add_message(session_id, "assistant", summary)
            except Exception as e:
                logger.error(f"Memory persistence failed: {e}")

            logger.info("Orchestration complete. Yielding final event.")
            yield {"type": "final", "content": result}

        except Exception as e:
            logger.error(f"Orchestration failure: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
    
    def _get_phase_name(self, phase_id: int) -> str:
        """Get human-readable phase name"""
        names = {
            1: "intent_extraction",
            2: "knowledge_retrieval",
            3: "synthesis",
            4: "sensory_modeling",
            5: "verification",
            6: "explanation",
            7: "optimization",
            8: "frontier_generation",
            9: "variant_selection"
        }
        return names.get(phase_id, f"phase_{phase_id}")
    
    def _get_phase_message(self, phase_id: int) -> str:
        """Get user-friendly phase status message"""
        messages = {
            1: "Extracting culinary intent...",
            2: "Retrieving scientific context...",
            3: "Synthesizing core concepts...",
            4: "Modeling sensory profile...",
            5: "Verifying scientific accuracy...",
            6: "Generating explanation...",
            7: "Optimizing recipe...",
            8: "Generating variants...",
            9: "Selecting best variant..."
        }
        return messages.get(phase_id, "Processing...")
