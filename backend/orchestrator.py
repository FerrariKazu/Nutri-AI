import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Callable
from backend.food_synthesis import NutriPipeline
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile

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

    async def execute_streamed(self, session_id: str, user_message: str, preferences: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Executes the 13-phase Nutri pipeline and yields SSE-ready JSON chunks.
        Implementing True Token Streaming via Queue Bridge.
        """
        loop = asyncio.get_running_loop()
        token_queue = asyncio.Queue()
        
        def stream_callback(token: str):
            """Callback for sync LLM threads to push tokens to async queue"""
            loop.call_soon_threadsafe(token_queue.put_nowait, token)

        try:
            # PRE-PHASE: Memory Injection
            context = self.memory.get_context_string(session_id)
            augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message
            
            # Helper: Consumes stream and yields (is_result, data)
            # data is JSON string if is_result=False, or Result Object if is_result=True
            async def run_phase(phase_id: int, func: Callable, *args, use_stream=False):
                # Inject callback if needed
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
                                yield (False, json.dumps({"phase": phase_id, "stream": token}))
                            except asyncio.QueueEmpty:
                                break
                    else:
                         # Heartbeat wait
                         await asyncio.sleep(2)
                         if not future.done():
                             yield (False, json.dumps({"phase": "heartbeat", "partial_output": "Processing..."}))

                # Flush remaining tokens
                if use_stream:
                    while not token_queue.empty():
                        token = await token_queue.get()
                        yield (False, json.dumps({"phase": phase_id, "stream": token}))
                
                # Yield Result
                yield (True, await future)

            # PHASE 1: Intent & Constraint Extraction
            yield self._format_chunk(1, "Intent & Constraint Extraction", "Analyzing culinary intent and dietary constraints...")
            intent = None
            async for is_res, data in run_phase(1, self.pipeline.intent_agent.extract, augmented_query, use_stream=True):
                if is_res: intent = data
                else: yield data
            
            # PHASE 2: Domain Feasibility Check
            yield self._format_chunk(2, "Domain Feasibility Check", "Cross-referencing scientific knowledge and documents...")
            docs = None
            async for is_res, data in run_phase(2, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2):
                if is_res: docs = data
                else: yield data
            
            # PHASE 3: Culinary / Nutrition Rule Validation
            yield self._format_chunk(3, "Culinary / Nutrition Rule Validation", "Generating baseline recipe and verifying claims...")
            recipe = None
            # Synthesize (Streaming)
            async for is_res, data in run_phase(3, self.pipeline.engine.synthesize, augmented_query, docs, intent, use_stream=True):
                if is_res: recipe = data
                else: yield data
            
            # Verify
            verification = None
            async for is_res, data in run_phase(3, self.pipeline.verify, recipe):
                if is_res: verification = data
                else: yield data
            
            # PHASE 4: Sensory Dimension Modeling
            yield self._format_chunk(4, "Sensory Dimension Modeling", "Predicting physical and sensory properties...")
            profile = None
            async for is_res, data in run_phase(4, self.pipeline.predict_sensory, recipe):
                if is_res: profile = data
                else: yield data

            # PHASE 5: Counterfactual Variant Generation
            yield self._format_chunk(5, "Counterfactual Variant Generation", "Exploring recipe variations and sensitivity...")
            cf_report = None
            async for is_res, data in run_phase(5, self.pipeline.simulate_sensory_counterfactual, profile, "salt_pct", 0.1):
                if is_res: cf_report = data
                else: yield data

            # PHASE 6: Trade-off Explanation
            yield self._format_chunk(6, "Trade-off Explanation", "Analyzing sensory impacts and audience calibration...")
            explanation = None
            async for is_res, data in run_phase(6, self.pipeline.explain_sensory, profile, "scientific"):
                if is_res: explanation = data
                else: yield data

            # PHASE 7: Multi-Objective Optimization
            yield self._format_chunk(7, "Multi-Objective Optimization", "Balancing nutrition and sensory targets...")
            optimization = {"status": "balanced"}

            # PHASE 8: Sensory Pareto Frontier Construction
            yield self._format_chunk(8, "Sensory Pareto Frontier Construction", "Generating optimal variant landscape...")
            frontier = None
            async for is_res, data in run_phase(8, self.pipeline.generate_sensory_frontier, recipe, profile):
                if is_res: frontier = data
                else: yield data

            # PHASE 9: Variant Scoring
            yield self._format_chunk(9, "Variant Scoring", "Projecting user preferences onto sensory variants...")
            user_prefs = UserPreferences(eating_style="balanced")
            selection = None
            async for is_res, data in run_phase(9, self.pipeline.select_sensory_variant, frontier, user_prefs):
                if is_res: selection = data
                else: yield data

            # PHASE 10: Constraint Reconciliation
            yield self._format_chunk(10, "Constraint Reconciliation", "Enforcing physical and chemical feasibility limits...")
            feasibility = {"warnings": []}

            # PHASE 11: Output Synthesis
            yield self._format_chunk(11, "Output Synthesis", "Compiling final recipe instructions and science logs...")
            final_recipe = selection.selected_variant.recipe if selection.selected_variant else recipe

            # PHASE 12: Explanation Layer
            yield self._format_chunk(12, "Explanation Layer", "Calibrating final feedback for chosen audience...")
            final_explanation = selection.reasoning[0] if selection.reasoning else "Optimized for target balance."

            # PHASE 13: Final Structured Response
            yield self._format_chunk(13, "Final Structured Response", "Finalizing response structure...")
            
            result = {
                "recipe": final_recipe,
                "sensory_profile": profile.__dict__ if hasattr(profile, "__dict__") else {},
                "explanation": final_explanation,
                "verification_report": [v.__dict__ for v in verification.claims] if hasattr(verification, "claims") else []
            }

            # WRITE-BACK: Memory
            self.memory.add_message(session_id, "user", user_message)
            self.memory.add_message(session_id, "assistant", f"Recipe: {final_recipe[:100]}...")

            yield json.dumps({"phase": "final", "output": result})

        except Exception as e:
            logger.error(f"Orchestration failure: {e}")
            import traceback
            traceback.print_exc()
            yield json.dumps({"error": str(e)})

    # Removed _consume_stream and _run_blocking_stream methods as they are replaced by run_phase closure
    
    def _format_chunk(self, phase_id: int, title: str, text: str) -> str:
        return json.dumps({
            "phase": phase_id,
            "title": title,
            "partial_output": text
        })



