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
from backend.nutrition_enforcer import (
    calculate_confidence_score,
    generate_proof_hash,
    NutritionEnforcementMode
)
from backend.explanation_router import ExplanationRouter, ExplanationVerbosity

from backend.belief_state import initialize_belief_state, BeliefState
from backend.belief_revision_engine import BeliefRevisionEngine
from backend.decision_comparator import DecisionComparator
from backend.reversal_explainer import ReversalExplainer
from backend.confidence_tracker import ConfidenceTracker, EvidenceStrength
from backend.context_saturation import ContextSaturationGuard
from backend.session_reset_policy import SessionResetPolicy

# Unified Persona Modules
from backend.response_modes import ResponseMode
from backend.mode_classifier import classify_response_mode
from backend.nutri_engine import NutriEngine
from backend.utils.execution_trace import create_trace, AgentInvocation

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
        self.explanation_router = ExplanationRouter()
        
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
        # 🟢 Initialize Trace per Session (Mandatory, but Non-Fatal)
        trace_id = f"tr_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        try:
            # Attempt to import create_trace dynamically or verify scope
            from backend.utils.execution_trace import create_trace
            trace = create_trace(session_id, trace_id)
            trace.schema_version = 2
            # Add Audit Data to Trace
            trace.system_audit = {
                "rag": "enabled",
                "model": self.pipeline.engine.llm.model_name
            }
        except Exception as e:
            logger.warning(f"Trace initialization failed (non-fatal): {e}")
            # Safe Minimal Fallback to prevent orchestration crash
            class FallbackTrace:
                def __init__(self, t_id, err):
                    self.id = t_id
                    self.status = "trace_error"
                    self.error = str(err)
                    self.system_audit = {}
                    self.claims = []
                    self.variance_drivers = {}
                    self.compounds = []
                    self.enforcement_failures = []
                    self.pubchem_proof_hash = ""
                    self.confidence_score = 0.0
                    self.tier4_belief_revisions = []
                    self.tier4_decision_changes = {}
                    self.tier4_confidence_delta = {}
                    self.tier4_uncertainty_resolved_count = 0
                    self.tier4_saturation_triggered = False
                    self.tier4_clarification_attempts = 0
                    self.tier4_session_age = 0
                    self.schema_version = 2 # Align with UI contract

                def to_dict(self):
                    return {
                        "id": self.id,
                        "status": "trace_error",
                        "error": self.error,
                        "tiers": {},
                        "metrics": {"duration": 0},
                        "claims": [],
                        "schema_version": self.schema_version
                    }
                
                def add_invocation(self, *args, **kwargs): pass
                def set_claims(self, *args, **kwargs): pass
                def set_pubchem_enforcement(self, *args, **kwargs): pass

            trace = FallbackTrace(trace_id, e)
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
                    "seq": seq_counter,
                    "stream_id": trace_id
                }), 
                loop
            )


        def stream_callback(token: str):
            # This is called from the executor thread
            push_event("token", token)

        async def run_sync(func, *args, **kwargs):
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        async def orchestration_task():
            nonlocal seq_counter
            logger.info("[ORCH] Background task started.")
            start_time = time.perf_counter()  # Fix: Ensure start_time is always initialized
            orchestration_status = "success"
            orchestration_error = ""
            done_emitted = False

            async def push_done(status: str, message: str = ""):
                nonlocal done_emitted
                nonlocal seq_counter
                if not done_emitted:
                    seq_counter += 1
                    # Status contract: OK | FAILED | RESOURCE_EXCEEDED
                    await event_queue.put({
                        "type": "done",
                        "content": {
                            "status": status, 
                            "message": message
                        },
                        "stream_id": trace_id,
                        "seq": seq_counter
                    })
                    logger.debug(f"[ORCH] push_done: {status} (seq={seq_counter})")
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
                

                # 🕐 Tier 4: Belief State & Turn Management
                session_ctx_obj = self.memory.get_context(session_id)
                session_ctx = session_ctx_obj.to_dict() if hasattr(session_ctx_obj, "to_dict") else session_ctx_obj
                current_turn = session_ctx.get("current_turn", 0) + 1
                session_ctx["current_turn"] = current_turn
                
                belief_state_dict = session_ctx.get("belief_state")
                if belief_state_dict:
                    belief_state = BeliefState.from_dict(belief_state_dict)
                else:
                    belief_state = initialize_belief_state()
                
                # Check for session reset (staleness/topic shift)
                reset_policy = SessionResetPolicy()
                if reset_policy.should_downgrade_confidence(belief_state, current_turn, user_message):
                    reset_policy.apply_reset(belief_state, "staleness")
                
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


                    session_ctx["belief_state"] = belief_state.to_dict()
                    final_data = {
                        "user_preferences": prefs_to_inject,
                        "session_context": session_ctx,
                        "moa_analysis": [],
                        "context_prompt": None,
                        "tier4_metrics": trace.to_dict().get("tier4", {}),
                    }
                    
                    await self.engine.generate(session_id, user_message, mode, final_data, stream_callback=stream_callback)
                    logger.info("[ORCH] Generation finished.")
                    await push_done("success")
                    return
                
                # 🟢 MULTI-PHASE PATH with HARD VALIDATION
                emit_status("retrieval", "Researching...")
                docs = await run_throttled_embedding(run_sync, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2)

                
                valid_phase_count = 0
                phase_results = {}
                recipe_result = ""  # Fix: Initialize recipe_result for parallel DAG
                
                for phase in selected_phases:
                    phase_start = time.perf_counter()
                    emit_status(f"phase_{phase.value}", f"{phase.value.title()}...")
                    
                    # Execute phase (simplified: use synthesis engine)
                    emit_status("synthesis", f"Analyzing ({phase.value})...")
                    phase_result_raw = await self.pipeline.engine.synthesize(augmented_query, docs, intent, stream_callback=None)

                    
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
                    recipe_result = str(phase_result)  # Update for DAG consumption
                    
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
                    session_ctx["belief_state"] = belief_state.to_dict()
                    final_data = {
                        "user_preferences": user_prefs,
                        "session_context": session_ctx,
                        "moa_analysis": [],
                        "context_prompt": None,
                        "tier4_metrics": trace.to_dict().get("tier4", {}),
                    }
                    await self.engine.generate(session_id, user_message, mode, final_data, stream_callback=stream_callback)
                    await push_done("success")
                    return
                
                # 5. Parallel DAG
                dag_results = {}
                if policy.profile != ExecutionProfile.FAST:
                    emit_status("enhancement", "Analyzing & Refining...")
                    dag = DAGScheduler()
                    start_time = time.perf_counter() # Fix: Initialize start_time
                    
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
                
                # 🔒 MoA GATE (Phase 1): Enforce mechanism requirement for causal claims
                from backend.mode_classifier import is_causal_intent
                
                has_causal_intent = is_causal_intent(user_message)
                verification_results = dag_results.get("verification", [])
                
                # Check mechanism completeness
                claims_with_valid_moa = sum(
                    1 for c in verification_results 
                    if hasattr(c, "mechanism") and c.mechanism and c.mechanism.is_valid
                )
                claims_total = len(verification_results)
                
                if has_causal_intent and claims_total > 0 and claims_with_valid_moa == 0:
                    logger.warning(
                        f"[MOA_GATE] Causal intent detected but no valid mechanisms available. "
                        f"Suppressing causal language. Claims: {claims_total}, Valid MoA: {claims_with_valid_moa}"
                    )
                    # Add gate metadata to final_data
                    moa_gate_active = True
                    moa_gate_reason = "Causal claim blocked: No complete mechanism-of-action chains available"
                else:
                    moa_gate_active = False
                    moa_gate_reason = None
                
                # 🧬 Tier 3 CONTEXTUAL ENFORCEMENT: Applicability + Risk + Recommendation
                from backend.claim_classifier import ClaimClassifier
                from backend.applicability_profile import ApplicabilityProfile, compute_applicability_match
                from backend.risk_engine import RiskEngine
                from backend.recommendation_gate import RecommendationGate
                from backend.context_prompt_engine import ContextPromptEngine
                
                claim_classifier = ClaimClassifier()
                risk_engine = RiskEngine()
                recommendation_gate = RecommendationGate()
                context_prompt_engine = ContextPromptEngine()
                
                # Classify claim type
                claim_type = claim_classifier.classify(user_message)
                
                # Build Tier 3 assessments for each verified claim
                tier3_results = []
                for claim in verification_results:
                    if not hasattr(claim, "mechanism") or not claim.mechanism:
                        continue
                    
                    # Build applicability profile (placeholder - to be populated from RAG)
                    profile = ApplicabilityProfile(
                        population={"general_adults"},  # Default, should come from RAG
                        dietary_context=set(),
                        dose_constraints=None
                    )
                    
                    # Match against user context (empty for now - no personalization)
                    user_context = preferences.get("context", {})
                    applicability_match = compute_applicability_match(profile, user_context)
                    
                    # Extract compound names for risk assessment
                    compound_names = [
                        step.description for step in claim.mechanism.steps 
                        if step.type == "compound"
                    ]
                    
                    # Assess risks
                    rag_coverage = 0.7  # Placeholder - should come from actual RAG source quality
                    population = user_context.get("population", "general_adults")
                    risk_assessment = risk_engine.assess(compound_names, population, rag_coverage)
                    
                    # Get recommendation decision
                    recommendation_result = recommendation_gate.evaluate(
                        mechanism_valid=claim.mechanism.is_valid,
                        applicability_match=applicability_match,
                        risk_assessment=risk_assessment,
                        claim_type=claim_type
                    )
                    
                    tier3_results.append({
                        "claim_text": claim.text if hasattr(claim, "text") else "",
                        "applicability_match": applicability_match.to_dict(),
                        "risk_assessment": risk_assessment.to_dict(),
                        "recommendation": recommendation_result.to_dict()
                    })
                    
                    # Log important decisions
                    if recommendation_result.decision.value != "allow":
                        logger.warning(
                            f"[TIER3_RECOMMENDATION_BLOCK] {recommendation_result.decision.value}: "
                            f"{recommendation_result.explanation}"
                        )
                
                # Generate context prompt if needed
                context_prompt = None
                if tier3_results and any(r["recommendation"]["decision"] == "require_more_context" for r in tier3_results):
                    missing_fields = []
                    for r in tier3_results:
                        missing_fields.extend(r["applicability_match"].get("missing_fields", []))
                    
                    unique_missing = list(set(missing_fields))
                    trace.tier3_missing_context_fields = unique_missing
                    
                    if unique_missing:
                        context_prompt = context_prompt_engine.suggest_missing_context(
                            unique_missing,
                            user_message
                        )
                
                # Aggregate Tier 3 metrics into trace
                if tier3_results:
                    trace.tier3_applicability_match = sum(r["applicability_match"]["score"] for r in tier3_results) / len(tier3_results)
                    trace.tier3_risk_flags_count = sum(len(r["risk_assessment"]["risks"]) for r in tier3_results)
                    
                    dist = {}
                    for r in tier3_results:
                        dec = r["recommendation"]["decision"]
                        dist[dec] = dist.get(dec, 0) + 1
                    trace.tier3_recommendation_distribution = dist
                

                # 🧠 Tier 4: Temporal & Epistemic Consistency Logic
                revision_engine = BeliefRevisionEngine()
                decision_comparator = DecisionComparator()
                reversal_explainer = ReversalExplainer()
                confidence_tracker = ConfidenceTracker()
                saturation_guard = ContextSaturationGuard()
                
                # Turn user context into belief updates
                user_context = preferences.get("context", {})
                for field, value in user_context.items():
                    if hasattr(belief_state, field):
                        revision = revision_engine.detect_conflict(belief_state, field, value, current_turn)
                        if revision:
                            revision_engine.apply_revision(belief_state, revision)
                            trace.tier4_belief_revisions.append(f"Turn {current_turn}: {field} updated")

                # Map tier3 results for comparison
                current_decisions = {
                    r["claim_text"]: r["recommendation"] for r in tier3_results 
                    if isinstance(r["recommendation"], dict) or hasattr(r["recommendation"], "decision")
                }
                
                from backend.recommendation_gate import RecommendationResult, RecommendationDecision
                norm_results = {}
                for cid, res in current_decisions.items():
                    if isinstance(res, dict):
                        norm_results[cid] = RecommendationResult(
                            decision=RecommendationDecision(res["decision"]),
                            reason=res.get("reason", "mechanism_strong"),
                            explanation=res.get("explanation", "")
                        )
                    else:
                        norm_results[cid] = res

                # Decision Comparison
                deltas = decision_comparator.compare_decisions(belief_state, norm_results, current_turn)
                trace.tier4_decision_changes = {cid: d.change_type for cid, d in deltas.items()}

                # Reversal Explanations and Confidence Evolution
                moa_explanations = []
                for claim in verification_results:
                    claim_id = getattr(claim, "text", str(claim))
                    delta = deltas.get(claim_id)
                    
                    ev_strength = confidence_tracker.classify_evidence_strength(
                        has_mechanism=claim.mechanism.is_valid if hasattr(claim, "mechanism") and claim.mechanism else False,
                        has_applicability=True, 
                        has_rag_support=True, 
                        user_provided_context=bool(user_context)
                    )
                    
                    prior_conf = belief_state.prior_confidences.get(claim_id, 0.5)
                    current_conf = getattr(claim, "confidence", 0.5)
                    is_valid_jump, _ = confidence_tracker.validate_confidence_evolution(
                        prior_conf, current_conf, ev_strength
                    )
                    
                    if not is_valid_jump:
                        current_conf = confidence_tracker.suggest_capped_confidence(prior_conf, current_conf, ev_strength)
                        if hasattr(claim, "confidence"): claim.confidence = current_conf
                    
                    trace.tier4_confidence_delta[claim_id] = current_conf - prior_conf
                    
                    reversal_expl = None
                    if delta and delta.change_type != "STABLE":
                        reversal_expl = reversal_explainer.generate_explanation(delta, belief_state)
                        trace.tier4_uncertainty_resolved_count += 1
                    
                    verbosity_str = preferences.get("explanation_verbosity", "quick").upper()
                    from backend.explanation_router import ExplanationVerbosity
                    verbosity = getattr(ExplanationVerbosity, verbosity_str, ExplanationVerbosity.QUICK)
                    
                    rendered = self.explanation_router.render(
                        claim_id, 
                        claim.mechanism if hasattr(claim, "mechanism") else None, 
                        verbosity,
                        norm_results.get(claim_id).decision.value if claim_id in norm_results else "allow",
                        decision_delta=delta,
                        confidence_delta=current_conf - prior_conf,
                        belief_state=belief_state,
                        reversal_explanation=reversal_expl
                    )
                    
                    moa_explanations.append({
                        "claim": claim_id,
                        "explanation": rendered,
                        "status": getattr(claim, "status_label", "verified")
                    })
                    
                    belief_state.prior_recommendations[claim_id] = norm_results.get(claim_id).decision.value if claim_id in norm_results else "allow"
                    belief_state.prior_confidences[claim_id] = current_conf

                # Context Saturation Check
                if context_prompt:
                    if saturation_guard.should_stop_asking(belief_state):
                        logger.warning("[ORCH] Clarification limit reached. Suppressing prompt.")
                        context_prompt = None
                        belief_state.trigger_saturation(current_turn)
                        trace.tier4_saturation_triggered = True
                    elif saturation_guard.is_repeat_question(context_prompt, belief_state):
                        logger.warning("[ORCH] Repeat question detected. Suppressing prompt.")
                        context_prompt = None
                    else:
                        belief_state.add_clarification(context_prompt, current_turn)
                
                trace.tier4_clarification_attempts = belief_state.clarification_attempts
                trace.tier4_session_age = current_turn
                session_ctx["belief_state"] = belief_state.to_dict()

                final_data = {
                    "phase_results": phase_results,
                    "analysis": dag_results.get("explanation"),
                    "sensory": dag_results.get("sensory"),
                    "verification": dag_results.get("verification"),
                    "user_preferences": prefs_to_inject,
                    "session_context": session_ctx,
                    "moa_gate_active": moa_gate_active,
                    "moa_gate_reason": moa_gate_reason,
                    "tier3_results": tier3_results,
                    "context_prompt": context_prompt,
                    "claim_type": claim_type,
                    "moa_analysis": moa_explanations,
                    "tier4_metrics": {
                        "decision_changes": trace.tier4_decision_changes,
                        "confidence_delta": trace.tier4_confidence_delta,
                        "session_age": trace.tier4_session_age,
                        "saturation_triggered": trace.tier4_saturation_triggered
                    },
                }

                logger.info(f"[ORCH] Generating final tailored response in mode {mode.value}...")
                await self.engine.generate(session_id, user_message, mode, final_data, stream_callback=stream_callback)
                
                # 🥗 Emit Nutrition Intelligence Report (Legacy companion)
                nutrition_report = {
                    "session_id": session_id,
                    "confidence_score": trace.confidence_score,
                    "final_confidence": getattr(trace, "final_confidence", getattr(trace, "confidence_score", 0.0)),
                    "weakest_link_id": getattr(trace, "weakest_link_id", None),
                    "compounds_resolved": len(trace.compounds),
                    "compounds_unverified": len(trace.enforcement_failures),
                    "unverified_list": trace.enforcement_failures,
                    "proof_hash": trace.pubchem_proof_hash,
                    "verified_claims": sum(1 for c in trace.claims if isinstance(c, dict) and c.get("verified")),
                    "total_claims": len(trace.claims),
                    "claims": trace.claims, # Deep claim evidence
                    "variance_drivers": trace.variance_drivers,
                    "conflicts_detected": any(c.get("has_conflict") for c in trace.claims if isinstance(c, dict)),
                    "summary": f"Nutrition verified via PubChem & USDA ({len(trace.compounds)} compounds, {len(trace.claims)} verifiable claims)"
                }
                push_event("nutrition_report", nutrition_report)
                
                logger.info("[ORCH] Generation finished.")
                await push_done("success", {"nutrition_report": nutrition_report})
                # Update session context after response
                new_context = await run_sync(memory_extractor.extract_context, user_message, "")
                if new_context:
                    self.memory.update_context(session_id, new_context)
                
                logger.info("[ORCH] Generation complete.")
                # push_done removed here, moved to finally to ensure trace precedes it

            except RuntimeError as e:
                # Catch ResourceBudgetExceeded specifically if needed, otherwise general
                orchestration_status = "RESOURCE_EXCEEDED"
                orchestration_error = str(e)
                logger.error(f"[ORCH] Resource Rejection: {e}")
                push_event("error_event", {
                    "message": str(e), 
                    "phase": "resource_guard", 
                    "status": "RESOURCE_EXCEEDED",
                    "stream_id": trace_id
                })
            except Exception as e:
                orchestration_status = "FAILED"
                orchestration_error = str(e)
                logger.error(f"Orchestration failure: {e}", exc_info=True)
                push_event("error_event", {
                    "message": str(e), 
                    "phase": "orchestration", 
                    "status": "FAILED",
                    "stream_id": trace_id
                })
            finally:
                gpu_monitor.sample_after()
                logger.info(f"[ORCH] Finalizing stream (status={orchestration_status}). Guaranteeing trace -> done.")
                
                # 1. 🟢 ALWAYS emit execution_trace
                try:
                    trace_dict = trace.to_dict()
                    seq_counter += 1
                    await event_queue.put({
                        "type": "execution_trace",
                        "content": trace_dict,
                        "seq": seq_counter,
                        "stream_id": trace_id
                    })
                    logger.info(f"[ORCH] Trace emitted (claims={len(trace.claims)}, seq={seq_counter})")
                except Exception as te:
                    logger.error(f"[ORCH] Failed to emit trace: {te}")

                # 2. ✅ Final DONE (Only if not already emitted by something else)
                if not done_emitted:
                    await push_done(orchestration_status, orchestration_error)

                # 3. 🏁 SENTINEL
                await event_queue.put(None)



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
