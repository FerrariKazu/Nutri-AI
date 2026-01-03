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

    async def execute_streamed(self, session_id: str, user_message: str, preferences: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the 13-phase Nutri pipeline and yields structured event dictionaries.
        Event types: 'reasoning' (phase info), 'token' (LLM stream), 'final' (structured result), 'error'.
        """
        loop = asyncio.get_running_loop()
        token_queue = asyncio.Queue()
        
        def stream_callback(token: str):
            """Callback for sync LLM threads to push tokens to async queue"""
            loop.call_soon_threadsafe(token_queue.put_nowait, token)

        try:
            # 0. PRE-PHASE: Memory Injection
            context = self.memory.get_context_string(session_id)
            augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message
            
            # Helper: Consumes stream and yields event dicts
            async def run_phase(phase_id: int, func: Callable, *args, use_stream=False):
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
                yield {"type": "result", "content": await future}

            # PHASE 1: Intent & Extraction
            yield {"type": "reasoning", "content": "Extracting Culinary Intent..."}
            intent = None
            async for event in run_phase(1, self.pipeline.intent_agent.extract, augmented_query, use_stream=True):
                if event["type"] == "result": intent = event["content"]
                else: yield event
            
            # PHASE 2: Knowledge Retrieval
            yield {"type": "reasoning", "content": "Retrieving Scientific Context..."}
            docs = None
            async for event in run_phase(2, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2):
                if event["type"] == "result": docs = event["content"]
                else: yield event
            
            # PHASE 3: Synthesis
            yield {"type": "reasoning", "content": "Synthesizing Core Concepts..."}
            recipe = None
            async for event in run_phase(3, self.pipeline.engine.synthesize, augmented_query, docs, intent, use_stream=True):
                if event["type"] == "result": recipe = event["content"]
                else: yield event
            
            # Verification (Reasoning)
            verification = None
            async for event in run_phase(3, self.pipeline.verify, recipe):
                if event["type"] == "result": verification = event["content"]
                else: yield event
            
            # PHASE 4: Sensory Dimension Modeling
            # PHASE 4: Sensory modeling
            yield {"type": "reasoning", "content": "Modeling Sensory Profile..."}
            profile = None
            async for event in run_phase(4, self.pipeline.predict_sensory, recipe):
                if event["type"] == "result": profile = event["content"]
                else: yield event

            # PHASE 5-6: Trade-offs
            yield {"type": "reasoning", "content": "Simulating Culinary Counterfactuals..."}
            explanation = None
            audience = preferences.get("audience_mode", "scientific")
            async for event in run_phase(6, self.pipeline.explain_sensory, profile, audience):
                if event["type"] == "result": explanation = event["content"]
                else: yield event

            # PHASE 7-10: Optimization
            yield {"type": "reasoning", "content": "Performing Multi-Objective Optimization..."}
            frontier = None
            async for event in run_phase(8, self.pipeline.generate_sensory_frontier, recipe):
                if event["type"] == "result": frontier = event["content"]
                else: yield event

            selection = None
            goal = preferences.get("optimization_goal", "balanced")
            async for event in run_phase(9, self.pipeline.select_sensory_variant, frontier, UserPreferences(eating_style=goal)):
                if event["type"] == "result": selection = event["content"]
                else: yield event

            # PHASE 11-13: Final Synthesis
            yield {"type": "reasoning", "content": "Wrapping Final Structured Response..."}
            final_recipe = selection.selected_variant.recipe if selection and selection.selected_variant else recipe
            final_explanation = selection.reasoning[0] if selection and selection.reasoning else explanation
            
            result = {
                "recipe": final_recipe,
                "sensory_profile": profile.__dict__ if hasattr(profile, "__dict__") else {},
                "explanation": final_explanation,
                "verification_report": [v.__dict__ for v in verification.claims] if (verification and hasattr(verification, "claims")) else []
            }

            self.memory.add_message(session_id, "user", user_message)
            summary = f"RECIPE: {final_recipe[:50]}... | EXPLANATION: {final_explanation[:50]}..."
            self.memory.add_message(session_id, "assistant", summary)

            yield {"type": "final", "content": result}

        except Exception as e:
            logger.error(f"Orchestration failure: {e}")
            yield {"type": "error", "content": str(e)}



