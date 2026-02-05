import json
import logging
import asyncio
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Callable, Optional

from backend.food_synthesis import NutriPipeline, IntentOutput
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile
from backend.execution_profiles import ExecutionProfile, ExecutionRouter
from backend.utils.response_formatter import ResponseFormatter
from backend.execution_plan import ExecutionPlan
from backend.memory_guard import MemoryGuard
from backend.resource_budget import ResourceBudget
from backend.gpu_monitor import gpu_monitor
from backend.embedding_throttle import run_throttled_embedding


# New Architecture Modules
from backend.meta_learner import MetaLearner, ExecutionPolicy
from backend.execution_dag import DAGScheduler, AgentNode
from backend.utils.execution_trace import AgentExecutionTrace, AgentInvocation, create_trace

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
        # 🟢 Initialize with Registry Defaults
        self.pipeline = NutriPipeline(model_name=None)  # Uses registry
        self.memory = memory_store
        self.meta_learner = MetaLearner()
        
        # Unified Response Engine
        self.engine = NutriEngine(self.pipeline.engine.llm, memory_store)
        
        logger.info("✅ NutriOrchestrator initialized with Model Registry")
        
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
        # 🟢 Initialize Trace per Session (Mandatory)
        trace_id = f"tr_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        trace = create_trace(session_id, trace_id)
        
        # Add Audit Data to Trace
        trace.system_audit = {
            "rag": "enabled",
            "model": self.pipeline.engine.llm.model_name
        }
        loop = asyncio.get_running_loop()
        event_queue = asyncio.Queue()
        seq_counter = 0

        def push_event(event_type: str, content: Any):
            nonlocal seq_counter
            seq_counter += 1
            logger.debug(f"[ORCH] push_event: {event_type} (seq={seq_counter})")
            # Safe way to put into queue from ANY thread
            asyncio.run_coroutine_threadsafe(
                event_queue.put({
                    "type": event_type, 
                    "content": content,
                    "seq": seq_counter
                }), 
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
                    # Status contract: OK | FAILED | RESOURCE_EXCEEDED
                    push_event("done", {"status": status, "message": message})
                    done_emitted = True

            try:
                # 0. Resource Check
                ResourceBudget.check_budget("NutriOrchestration", requires_gpu=True)
                gpu_monitor.sample_before()

                # 0.1 Meta-Learner Policy Decision

                policy = self.meta_learner.decide_policy(user_message, execution_mode)
                
                def emit_status(phase: str, msg: str):
                    if phase and msg and msg.strip():
                        # Calculate latency since last status
                        nonlocal last_status_ts
                        now = time.perf_counter()
                        duration_ms = int((now - last_status_ts) * 1000)
                        last_status_ts = now
                        
                        logger.debug(f"[ORCH] Status update: {phase} ({duration_ms}ms)")
                        push_event("status", {
                            "phase": phase, 
                            "message": msg,
                            "duration_ms": duration_ms
                        })

                last_status_ts = time.perf_counter()
                logger.info(f"Orchestrating with Policy: {policy.profile.value}")
                emit_status("initializing", "Connecting to Nutri engine...")
                emit_status("starting", f"Thinking ({policy.profile.value})...")


                # 1. Context Preparation
                context = self.memory.get_context_string(session_id)
                augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message

                # 2. Intent Extraction
                emit_status("intent", "Understanding...")
                inv_intent = AgentInvocation(agent_name="intent_agent", model_used=self.pipeline.intent_agent.llm.model_name, status="success", reason="selected")
                intent_raw = await run_sync(self.pipeline.intent_agent.extract, augmented_query)
                inv_intent.complete(tokens=len(str(intent_raw))) # Estimated
                trace.add_invocation(inv_intent)
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
                
                # 🟢 PHASE 5 & 6 INTEGRATION
                # Memory Extraction and Phase Selection
                from backend.selective_memory import MemoryExtractor
                from backend.phase_schema import PhaseSelector
                
                # Get/create user_id for this session
                user_id = self.memory.get_user_id(session_id)
                if not user_id:
                    # Will be set by frontend on first request
                    user_id = None
                
                # Load existing memory
                user_prefs = self.memory.get_preferences(user_id) if user_id else None
                
                #  🟢 PHASE 6.1: Apply decay logic on session start
                if user_prefs:
                    user_prefs.apply_decay(decay_days=90, decay_amount=0.2)
                    # Update DB if decay was applied (confidence changed)
                    if user_prefs.last_confirmed_at:
                        self.memory.update_preferences(user_id, user_prefs.to_dict())
                
                session_ctx = self.memory.get_context(session_id)
                
                # Extract new preferences (two-stage: deterministic filter → LLM)
                inv_mem = AgentInvocation(agent_name="memory_agent", model_used=self.pipeline.engine.llm.model_name, status="success", reason="selected")
                memory_extractor = MemoryExtractor(self.pipeline.engine.llm)
                pref_updates = await run_sync(memory_extractor.extract_preferences, user_message, user_prefs)
                
                if pref_updates and user_id:
                    self.memory.update_preferences(user_id, pref_updates)
                    user_prefs = self.memory.get_preferences(user_id)  # Reload
                    inv_mem.complete(reason="updates_found")
                else:
                    inv_mem.complete(status="skipped", reason="no_triggers")
                trace.add_invocation(inv_mem)
                
                #  🟢 PHASE 6.1: Filter memory by confidence before using
                # Only inject if confidence >= 0.6
                prefs_to_inject = user_prefs if (user_prefs and user_prefs.should_inject(0.6)) else None
                
                # Select phases with confidence gate
                selected_phases = PhaseSelector.select_phases(user_message, mode, intent, prefs_to_inject)
                logger.info(f"🧠 [PHASE] Selected {len(selected_phases)} phases: {[p.value for p in selected_phases]}")

                # 4. Mode-Based Execution with Phase Integration
                
                # 🟢 ZERO-PHASE PATH: Simple conversation or high confidence < threshold
                if len(selected_phases) == 0:
                    if mode == ResponseMode.CONVERSATION:
                        emit_status("conversation", "Chatting...")
                    else:
                        emit_status("generating", "Thinking...")
                    
                    logger.info("[ORCH] Zero-phase path: Direct response generation")
                    
                    # Inject memory into generation (filtered by confidence)
                    final_data = {
                        "user_preferences": prefs_to_inject,  # 🟢 Only if confidence >= 0.6
                        "session_context": session_ctx
                    }
                    
                    await run_sync(self.engine.generate, session_id, user_message, mode, final_data, stream_callback=stream_callback)
                    logger.info("[ORCH] Generation finished.")
                    push_done("success")
                    return
                
                # 🟢 MULTI-PHASE PATH with HARD VALIDATION
                emit_status("retrieval", "Researching...")
                docs = await run_throttled_embedding(run_sync, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2)

                
                valid_phase_count = 0
                phase_results = {}
                
                for phase in selected_phases:
                    phase_start = time.perf_counter()
                    emit_status(f"phase_{phase.value}", f"{phase.value.title()}...")
                    
                    # Execute phase (simplified: use synthesis engine)
                    emit_status("synthesis", f"Analyzing ({phase.value})...")
                    phase_result_raw = await run_sync(self.pipeline.engine.synthesize, augmented_query, docs, intent, stream_callback=None)

                    
                    # Unpack (recipe, enforcement_meta)
                    if isinstance(phase_result_raw, tuple):
                        phase_result, enf_meta = phase_result_raw
                        # Update trace with enforcement data
                        trace.set_pubchem_enforcement(enf_meta)
                        
                        # 📋 PHASE 1-3 Claim Intelligence Integration
                        if "claims" in enf_meta:
                            # Re-wrap claims into object format for trace helper if needed, 
                            # but trace.set_claims handles dict/object mapping.
                            # We'll pass the list directly.
                            from types import SimpleNamespace
                            claim_objs = [SimpleNamespace(**c) for c in enf_meta["claims"]]
                            trace.set_claims(claim_objs, enf_meta.get("variance_drivers", {}))
                    else:
                        phase_result = phase_result_raw

                    # ENFORCEMENT: Skip phase if content doesn't match type
                    if not PhaseSelector.validate_phase_content(phase, str(phase_result)):
                        logger.warning(f"[PHASE] Skipping {phase.value}: content validation failed")
                        continue  # Skip this phase entirely
                    
                    valid_phase_count += 1
                    phase_results[phase.value] = phase_result
                    
                    # Duration for the thinking phase specifically
                    phase_duration = int((time.perf_counter() - phase_start) * 1000)
                    
                    push_event("thinking_phase", {
                        "type": phase.value,
                        "content": str(phase_result)[:500],  # Truncated for SSE
                        "duration_ms": phase_duration
                    })

                
                # FALLBACK: If all phases were skipped, emit zero-phase response
                if valid_phase_count == 0:
                    logger.info("[PHASE] All phases failed validation. Falling back to direct response.")
                    final_data = {
                        "user_preferences": user_prefs,
                        "session_context": session_ctx
                    }
                    await run_sync(self.engine.generate, session_id, user_message, mode, final_data, stream_callback=stream_callback)
                    push_done("success")
                    return
                
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

                # 6. Final Presentation & Trace Emission
                emit_status("finalizing", "Plating your response...")
                final_data = {
                    "phase_results": phase_results,
                    "analysis": dag_results.get("explanation"),
                    "sensory": dag_results.get("sensory"),
                    "verification": dag_results.get("verification"),
                    "user_preferences": prefs_to_inject,
                    "session_context": session_ctx
                }

                logger.info(f"[ORCH] Generating final tailored response in mode {mode.value}...")
                await run_sync(self.engine.generate, session_id, user_message, mode, final_data, stream_callback=stream_callback)
                
                # 🟢 Emit Execution Trace for Observability
                trace_start_ts = start_time # Align with orchestrator start
                trace_dict = trace.to_dict()
                push_event("execution_trace", trace_dict)
                
                # 🥗 Emit Nutrition Intelligence Report
                nutrition_report = {
                    "session_id": session_id,
                    "confidence_score": trace.confidence_score,
                    "final_confidence": getattr(trace, "final_confidence", trace.confidence_score),
                    "weakest_link_id": getattr(trace, "weakest_link_id", None),
                    "compounds_resolved": len(trace.pubchem_compounds),
                    "compounds_unverified": len(trace.enforcement_failures),
                    "unverified_list": trace.enforcement_failures,
                    "proof_hash": trace.pubchem_proof_hash,
                    "verified_claims": sum(1 for c in trace.claims if c.get("verified")),
                    "total_claims": len(trace.claims),
                    "claims": trace.claims, # Deep claim evidence
                    "variance_drivers": trace.variance_drivers,
                    "conflicts_detected": any(c.get("has_conflict") for c in trace.claims),
                    "summary": f"Nutrition verified via PubChem & USDA ({len(trace.pubchem_compounds)} compounds, {len(trace.claims)} verifiable claims)"
                }
                push_event("nutrition_report", nutrition_report)
                
                logger.info("[ORCH] Generation finished.")
                push_done("success", {"nutrition_report": nutrition_report})
                # Update session context after response
                new_context = await run_sync(memory_extractor.extract_context, user_message, "")
                if new_context:
                    self.memory.update_context(session_id, new_context)
                
                logger.info("[ORCH] Generation complete.")
                push_done("success")

            except RuntimeError as e:
                # Catch ResourceBudgetExceeded specifically if needed, otherwise general
                logger.error(f"[ORCH] Resource Rejection: {e}")
                push_event("error_event", {"message": str(e), "phase": "resource_guard", "status": "RESOURCE_EXCEEDED"})
                push_done("RESOURCE_EXCEEDED", str(e))
            except Exception as e:
                logger.error(f"Orchestration failure: {e}", exc_info=True)
                push_event("error_event", {"message": str(e), "phase": "orchestration", "status": "FAILED"})
                push_done("FAILED", str(e))
            finally:
                gpu_monitor.sample_after()
                logger.info("[ORCH] Ending task and pushing sentinels.")
                
                # FINAL ASSERTION: Exactly one terminal event
                if not done_emitted:
                    logger.warning("[ORCH] Development Warning: No [DONE] emitted! Failsafe triggered.")
                    push_done("OK")
                
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
