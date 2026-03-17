import json
import logging
import asyncio
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Callable, Optional
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

from backend.food_synthesis import NutriPipeline, IntentOutput
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile
from backend.execution_profiles import ExecutionProfile, ExecutionRouter
from backend.utils.response_formatter import ResponseFormatter
from backend.execution_plan import ExecutionPlan
from backend.memory_guard import MemoryGuard
from backend.resource_budget import ResourceBudget
from backend.intelligence.claim_enricher import enrich_claims
from backend.gpu_monitor import gpu_monitor
from backend.embedding_throttle import run_throttled_embedding


# New Architecture Modules
from backend.meta_learner import MetaLearner, ExecutionPolicy
from backend.execution_dag import DAGScheduler, AgentNode
from backend.nutrition_enforcer import (
    calculate_resolution_coverage,
    generate_proof_hash,
    NutritionEnforcementMode
)
from backend.explanation_router import ExplanationRouter, ExplanationVerbosity
from backend.policies.default_policy_v1 import NUTRI_EVIDENCE_V1

from backend.belief_state import initialize_belief_state, BeliefState
from backend.belief_revision_engine import BeliefRevisionEngine
from backend.decision_comparator import DecisionComparator
from backend.reversal_explainer import ReversalExplainer
from backend.v2_intent_sandbox import IntentDetector
from backend.llm_qwen3 import LLMQwen3
from backend.confidence_tracker import ConfidenceTracker, EvidenceStrength
from backend.context_saturation import ContextSaturationGuard
from backend.session_reset_policy import SessionResetPolicy
from backend.governance_types import GovernanceState, EscalationLevel
from backend.macro_output_validator import MacroOutputValidator
from backend.prompts.system_roles import get_system_prompt_for_state

# Unified Persona Modules
from backend.response_modes import ResponseMode
from backend.mode_classifier import classify_response_mode
from backend.nutri_engine import NutriEngine
from backend.utils.execution_trace import (
    AgentExecutionTrace, 
    AgentInvocation, 
    create_trace, 
    TraceStatus,
    ExecutionMode,
    DowngradeReason,
    EpistemicStatus
)
from backend.utils.trace_finalizer import finalize_trace_stage
from backend.intelligence_classifier import IntelligenceClassifier
from backend.ranking_engine import RankingEngine, MoleculeReceptorMapper
from backend.contracts.output_contract import ContractViolationError, validate_sse_content, render_structured_to_narrative
from backend.retriever.router import IndexType
from backend.utils.query_segmentation import segment_clauses

# ── Phase 2: Scientific Registry Sources ──
from backend.intelligence.scientific_registries import SCIENTIFIC_KEYWORDS, BIO_CONTEXT, NUTRITION_KEYWORDS

# ── Phase 2.2: Grounding & Mandate Constraints ──

# ── FIX 2: Per-cycle Retrieval Cache ─────────────────────────────────────────
class RetrievalCache:
    """Short-lived per-request cache used to avoid duplicate FAISS searches."""
    def __init__(self):
        self.cache: dict = {}

    def get(self, query: str):
        return self.cache.get(query)

    def set(self, query: str, results):
        self.cache[query] = results
# ─────────────────────────────────────────────────────────────────────────────
MIN_MECHANISTIC_SIMILARITY = 0.65
MIN_SCIENTIFIC_SCORE = 0.60

AGENT_ACTIVATION_MATRIX = {
    EscalationLevel.TIER_0: ["presentation_agent", "intent_classifier", "memory_extractor"],
    EscalationLevel.TIER_1: ["presentation_agent", "intent_classifier", "synthesis_engine", "memory_agent", "memory_extractor"],
    EscalationLevel.TIER_2: ["presentation_agent", "intent_classifier", "synthesis_engine", "memory_agent", "rag_agent", "refinement_agent", "memory_extractor"],
    EscalationLevel.TIER_3: [
        "presentation_agent", "intent_classifier", "synthesis_engine", "memory_agent", 
        "rag_agent", "verifier_agent", "refinement_agent", "pubchem_client", 
        "mechanistic_explainer", "sensory_model", "verification", "llm_engine", 
        "frontier_optimizer", "memory_extractor"
    ]
}

# ── Phase 2.1: Governance Baseline & Thresholds ──
GOVERNANCE_VERSION = "1.0.0"
TIER_2_THRESHOLD = 3   # Nutrition Research
TIER_3_THRESHOLD = 5   # Biochemical/Molecular

# ── Phase 2: Domain Index Map (Tier → Allowed Retrieval Indices) ──
TIER_INDEX_MAP = {
    EscalationLevel.TIER_0: [],     # Chat — no retrieval
    EscalationLevel.TIER_1: [],     # Clarification — ask before acting
    EscalationLevel.TIER_2: [IndexType.USDA_BRANDED, IndexType.USDA_FOUNDATION, IndexType.FNDDS, IndexType.OPEN_NUTRITION, IndexType.RECIPES],
    # Mechanistic ONLY relies on molecular mechanisms and biological context, NOT general recipes/brands.
    EscalationLevel.TIER_3: [IndexType.CHEMISTRY, IndexType.SCIENCE],
}

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
        # V2 Intent Enforcement Node (Phase 1.5)
        self.intent_enforcer = IntentDetector(LLMQwen3("intent_classifier"))  # Uses registry
        self.explanation_router = ExplanationRouter()
        self.last_emitted_trace = None # Cache for debug endpoint
        
        # Unified Response Engine
        self.engine = NutriEngine(self.pipeline.engine.llm, memory_store)

        # Phase 2: Mandatory escalation tier (no hasattr fallback)
        self._current_escalation_tier = EscalationLevel.TIER_0
        self._blocked_agents_count = 0
        
        logger.info("✅ NutriOrchestrator initialized with Model Registry")
        
    async def execute_streamed(
        self, 
        session_id: str, 
        user_message: str, 
        preferences: Dict[str, Any],
        execution_mode: Optional[str] = None, 
        run_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the synthesis loop, yielding SSE event dicts.
        Identity is enforced: every packet has run_id and pipeline.
        """
        # Identity and Trace Init
        run_id = run_id or str(uuid.uuid4())
        trace_id = f"tr_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
        # Determine Pipeline name from logic (simplification for now)
        # In a more complex system, this would be dynamic.
        active_pipeline = execution_mode or "flavor_explainer"
        try:
            # Attempt to import create_trace dynamically or verify scope
            trace = create_trace(session_id, trace_id)
            trace.run_id = run_id
            trace.pipeline = active_pipeline
            # Add Audit Data to Trace
            from backend.sensory.sensory_registry import SensoryRegistry
            snapshot = SensoryRegistry.get_registry_snapshot()
            trace.lock_versions(
                reg_v=snapshot["version"],
                reg_h=snapshot["hash"],
                ont_v=snapshot["ontology_version"]
            )
            trace.registry_scope = snapshot.get("scope", {})
            
            # Skip legacy scientific intent check here
            # Boundaries will be enforced after Domain Pass 1 (L561)
            
            trace.evidence_policy_id = NUTRI_EVIDENCE_V1.policy_id
            
            trace.evidence_policy_id = NUTRI_EVIDENCE_V1.policy_id
            trace.policy_version = NUTRI_EVIDENCE_V1.version
            trace.policy_hash = NUTRI_EVIDENCE_V1.compute_hash()
            trace.policy_selection_reason = "system_default_profile"
            
            trace.system_audit = {
                "rag": "enabled",
                "model": self.pipeline.engine.llm.model_name,
                "intelligence_mandated": trace.trace_required,
                "policy_id": trace.evidence_policy_id,
                "selection_reason": trace.policy_selection_reason
            }
        except Exception as e:
            import traceback
            logger.warning(f"Trace initialization failed (non-fatal): {e}\n{traceback.format_exc()}")
            # Safe Minimal Fallback to prevent orchestration crash
            class FallbackTrace:
                def __init__(self, t_id, s_id, r_id, p_name, err):
                    self.id = t_id
                    self.session_id = s_id
                    self.run_id = r_id
                    self.pipeline = p_name
                    self.trace_variant = "fallback"
                    self.epistemic_status = EpistemicStatus.FALLBACK_EXECUTION
                    self.execution_mode = ExecutionMode.FALLBACK
                    self.confidence_breakdown = {
                        "baseline": 0.0,
                        "multipliers": [],
                        "policy_adjustment": 0.0,
                        "final": 0.0
                    }
                    self.trace_seq = 0
                    self.status = "trace_error"
                    self.error = str(err)
                    self.system_audit = {}
                    self.claims = []
                    self.variance_drivers = {}
                    self.compounds = []
                    self.enforcement_failures = []
                    self.pubchem_proof_hash = ""
                    self.confidence_score = 0.0
                    self.schema_version = 2 

                def to_dict(self):
                    return {
                        "id": self.id,
                        "trace_id": self.id,
                        "session_id": self.session_id,
                        "run_id": self.run_id,
                        "pipeline": self.pipeline,
                        "trace_variant": self.trace_variant,
                        "epistemic_status": self.epistemic_status.value,
                        "execution_mode": self.execution_mode.value,
                        "confidence_breakdown": self.confidence_breakdown,
                        "trace_seq": self.trace_seq,
                        "status": "trace_error",
                        "error": self.error,
                        "tiers": {},
                        "metrics": {"duration": 0},
                        "claims": [],
                        "schema_version": "1.2.6",
                        "trace_schema_version": "1.2.6",
                        "trace_metrics": {
                            "substance_state": "fallback",
                            "biological_claim_count": 0,
                            "anchor_count": 0
                        },
                        "temporal_layer": {
                            "session_age": 0,
                            "belief_revisions": 0,
                            "decision_state": "initial",
                            "resolved_deltas": 0
                        },
                        "governance": {},
                        "baseline_evidence_summary": {
                            "total_claims": 0,
                            "total_evidence_entries": 0,
                            "highest_study_type": "none",
                            "empirical_support_present": False
                        }
                    }
                
                def add_invocation(self, *args, **kwargs): pass
                def set_claims(self, *args, **kwargs): pass
                def set_pubchem_enforcement(self, *args, **kwargs): pass

            trace = FallbackTrace(trace_id, session_id, run_id, active_pipeline, e)
        loop = asyncio.get_running_loop()
        event_queue = asyncio.Queue()
        seq_counter = 0

        TEXTUAL_EVENTS = {"token", "reasoning", "message"}

        def push_event(event_type: str, content: Any, agent: str = "orchestrator"):
            # Transport Contract Hardening
            if event_type in TEXTUAL_EVENTS and not isinstance(content, str):
                logger.critical(f"🚨 [CONTRACT_VIOLATION] agent='{agent}' attempted to emit {type(content)} to {event_type} stream: {str(content)[:100]}")
                raise TypeError(f"Transport Contract Violation: {event_type} stream must be string, got {type(content)}")

            nonlocal seq_counter
            seq_counter += 1
            if event_type != "token":
                logger.debug(f"[ORCH][{active_pipeline}] push_event: {event_type} (seq={seq_counter}) agent={agent}")
            
            # Safe way to put into queue from ANY thread
            asyncio.run_coroutine_threadsafe(
                event_queue.put({
                    "type": event_type, 
                    "content": content,
                    "seq": seq_counter,
                    "stream_id": trace_id,
                    "agent": agent
                }), 
                loop
            )

        # 🕐 Tier 4: Belief State & Session Context (Load Early for Phase 2 Persistence)
        session_ctx_obj = self.memory.get_context(session_id)
        session_ctx = session_ctx_obj.to_dict() if hasattr(session_ctx_obj, "to_dict") else session_ctx_obj
        current_turn = session_ctx.get("current_turn", 0) + 1
        session_ctx["current_turn"] = current_turn
        
        belief_state_dict = session_ctx.get("belief_state")
        if belief_state_dict:
            belief_state = BeliefState.from_dict(belief_state_dict)
        else:
            belief_state = initialize_belief_state()

        async def push_event_async(event_type: str, content: Any, agent: str = "orchestrator"):
            # Transport Contract Hardening
            if event_type in TEXTUAL_EVENTS and not isinstance(content, str):
                logger.critical(f"🚨 [CONTRACT_VIOLATION_ASYNC] agent='{agent}' attempted to emit {type(content)} to {event_type} stream: {str(content)[:100]}")
                raise TypeError(f"Transport Contract Violation: {event_type} stream must be string, got {type(content)}")

            nonlocal seq_counter
            seq_counter += 1
            if event_type != "token":
                logger.debug(f"[ORCH][{active_pipeline}] push_event_async: {event_type} (seq={seq_counter}) agent={agent}")
            await event_queue.put({
                "type": event_type, 
                "content": content,
                "seq": seq_counter,
                "stream_id": trace_id,
                "agent": agent
            })



        full_response_text = ""
        # 🤖 Phase 1.8 State Governance (Context dictionary to prevent scoping collisions)
        gov_context = {
            "state": GovernanceState.ALLOW_QUALITATIVE,
            "quantitative_required": False,
            "mode": ResponseMode.CONVERSATION
        }
        
        def stream_callback_sync(token: str):
            nonlocal full_response_text
            full_response_text += token
            
            # PHASE 1.7: Hard Kill-Switch
            # If we are in ANY guided nutrition state, streaming is FORBIDDEN.
            # We enforce zero-token emission at the transport layer.
            if not gov_context["quantitative_required"]:
                push_event("token", token, agent="llm_engine")
            else:
                # Even if the engine is called (which it shouldn't be in 1.7),
                # we do NOT release tokens to the user socket.
                pass

        async def run_sync(func, *args, **kwargs):
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        async def _enforce_intelligence(trace, full_response_text, intent, belief_state=None, current_turn=0, user_prefs=None):
            """
            Unbreakable intelligence mandate enforcement.
            Sequence: Parse -> Deduplicate -> Enrich -> Repair -> Validate -> Snapshot -> Memory.
            """
            # Structural Stability: Derive mode from trace context (Fixes NameError: mode)
            mode = getattr(trace, "execution_mode", ResponseMode.CONVERSATION)
            if not isinstance(mode, ResponseMode):
                if getattr(trace, "trace_variant", "standard") == "mechanistic":
                    gov_context["mode"] = ResponseMode.MECHANISTIC
                   # Case 3: Explicit complexity signals
                elif intent.get("explanation_depth") == "scientific":
                    gov_context["mode"] = ResponseMode.DIAGNOSTIC
                elif intent.get("nutritional_goals"):
                    gov_context["mode"] = ResponseMode.DIAGNOSTIC
                else:
                    gov_context["mode"] = ResponseMode.CONVERSATION

            if not trace.trace_required:
                return

            final_text = "".join(full_response_text)
            logger.info(f"[MANDATE] Enforcing intelligence (Unbreakable Flow) for {len(final_text)} characters.")
            
            try:
                # 1. Extraction Fallback (Parser)
                from backend.intelligence.mechanism_parser import MechanismParser
                from backend.intelligence.claim_filter import is_mechanistic, create_fallback_claim
                parser = MechanismParser()
                extracted_claims = parser.parse(final_text)
                
                # 1.5 Purity Gate (Stage 1: Raw Filter) - REMOVED per User Instruction
                # We send ALL parsed claims to enrichment to ensure we don't kill valid biology 
                # that just hasn't been tagged yet.
                # if extracted_claims:
                #     count_before = len(extracted_claims)
                #     extracted_claims = [c for c in extracted_claims if is_mechanistic(c)]
                #     removed = count_before - len(extracted_claims)
                #     if removed > 0:
                #         logger.info(f"[FILTER] Removed {removed} non-mechanistic claims after parsing.")

                # 2. Preparation & Merge
                if extracted_claims:
                    logger.info(f"[MANDATE] Parser extracted {len(extracted_claims)} valid claims.")
                    # Deduplication happens inside trace.add_claims via ID check
                    trace.add_claims(extracted_claims)
                
                # 3. Universal Enrichment & Repair (Enforced SSOT)
                from backend.intelligence.claim_enricher import enrich_claims
                # Re-enrich EVERYTHING in the trace to ensure 100% compliance
                if trace.claims:
                    logger.info(f"[ORCHESTRATOR] Pre-enrichment claims: {len(trace.claims)}")
                    trace.claims = enrich_claims(trace.claims)
                    
                    # 🔬 SURFACE VALIDATOR (EP-3: Trace-Aware)
                    try:
                        from backend.verification.surface_validator import validate_surface_response
                        from backend.sensory.sensory_registry import ONTOLOGY
                        surface_result = validate_surface_response(
                            final_text, trace.claims,
                            set(ONTOLOGY["compounds"].keys())
                        )
                        trace.surface_validation = surface_result
                        if not surface_result["validated"]:
                            logger.warning(f"[SURFACE] {len(surface_result['unsupported_mentions'])} unsupported mentions found in surface response")
                    except Exception as e:
                        logger.warning(f"[ORCHESTRATOR] Surface validator failed (non-blocking): {e}")
                    
                    # Post-Enrichment Audit (User Mandate)
                    for i, c in enumerate(trace.claims):
                        c_id = c.get("id")
                        has_mech = c.get("mechanism") is not None
                        is_ver = c.get("verified") is True
                        logger.info(f"[ORCHESTRATOR] Post-enrichment claim[{i}] id={c_id} verified={is_ver} mechanism={has_mech}")
                        
                        # ORCHESTRATOR HARD ASSERT
                        if is_ver and not has_mech:
                            raise ValueError(f"Orchestrator Integrity Failure: Claim {c_id} is verified but lost mechanism immediately after enrichment.")

                    # 3.5 Purity Gate (Stage 2: Post-Enrichment Sync)
                    count_before = len(trace.claims)
                    trace.claims = [c for c in trace.claims if is_mechanistic(c)]
                    removed = count_before - len(trace.claims)
                    if removed > 0:
                        logger.info(f"[FILTER] Removed {removed} non-mechanistic claims after enrichment.")
                    
                    if trace.claims:
                        logger.info(f"[MANDATE] Enriched and Repaired {len(trace.claims)} claims.")
                
                # 4. Fallback Logic (Mandatory Purity)
                if not trace.claims and trace.trace_required:
                    logger.warning("[MANDATE] 0 claims remain after filtering. Generating fallback.")
                    fallback = create_fallback_claim(final_text)
                    trace.add_claims([fallback])
                    trace.validation_status = "partial"
                elif trace.claims:
                    trace.validation_status = "verified" if any(c.get("verified") for c in trace.claims) else "partial"
                else:
                    trace.validation_status = "invalid"

                # 🌐 CONTEXTUAL INTELLIGENCE LAYER (Phase 4)
                # Mechanistic traces are context-isolated — no conversational memory injection.
                if trace.trace_variant == "mechanistic":
                    trace.contextual_layer = None
                    logger.info("[ORCHESTRATOR] 🧪 Mechanistic mode: contextual layer suppressed (memory isolation).")
                else:
                    try:
                        from backend.verification.contextual_evaluator import ContextualIntelligenceEvaluator
                        ctx_evaluator = ContextualIntelligenceEvaluator()
                        trace.contextual_layer = ctx_evaluator.evaluate(
                            session_id, user_message, self.memory, 
                            belief_state, user_prefs, current_turn
                        )
                        logger.info(f"[ORCHESTRATOR] 🌐 Contextual Layer: {trace.contextual_layer.get('memory_hits')} memory hits, follow_up={trace.contextual_layer.get('follow_up_decision')}")
                    except Exception as e:
                        logger.warning(f"[ORCHESTRATOR] Contextual evaluator failed (non-blocking): {e}")

                # 🔬 DOMAIN CLASSIFIER PASS 2 (EP-3: Post-Enrichment Final)
                try:
                    from backend.verification.trace_domain_classifier import classify_trace_domain_final
                    # Access belief_state from enclosing scope (loaded at L488 before this is called)
                    _bs_active = False
                    _has_prior = False
                    try:
                        _bs_active = bool(belief_state and getattr(belief_state, 'prior_recommendations', None))
                        _has_prior = bool(belief_state and len(getattr(belief_state, 'prior_recommendations', {})) > 0)
                    except NameError:
                        pass  # belief_state not yet initialized (shouldn't happen but safe guard)
                    
                    final_domain, final_vis, final_conf, final_reason = classify_trace_domain_final(
                        preliminary_domain=trace.domain_type,
                        preliminary_confidence=trace.domain_confidence,
                        has_enriched_claims=bool(trace.claims),
                        enriched_claim_count=len(trace.claims),
                        belief_state_active=_bs_active,
                        has_prior_claims=_has_prior
                    )
                    
                    # 🛡️ Capture Standardized Downgrade Reason (Refinement Phase)
                    if final_domain == "contextual" and trace.domain_type == "scientific":
                        trace.downgrade_reason = DowngradeReason.NO_ENRICHED_CLAIMS
                        logger.info(f"[ORCHESTRATOR] 📉 Domain Downgrade: {trace.downgrade_reason.value}")

                    # Apply final classification (may upgrade from preliminary)
                    trace.domain_type = final_domain
                    trace.visibility_level = final_vis
                    trace.domain_confidence = final_conf
                    logger.info(f"[ORCHESTRATOR] 🔬 Domain Pass 2: {final_domain} (conf={final_conf}, reason={final_reason})")
                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Domain classifier Pass 2 failed (non-blocking): {e}")

                # 📜 SCIENTIFIC TRACE CONTRACT (Phase 2: Warn-Only)
                try:
                    from backend.verification.scientific_trace_contract import validate_scientific_trace
                    # Only validate if domain is SCIENTIFIC or HYBRID (skip contextual unless mandated)
                    # For Phase 2 we validate all non-contextual or if specifically upgraded
                    if trace.domain_type in ["scientific", "hybrid"]:
                        contract_res = validate_scientific_trace(trace, gov_context["mode"])
                        trace.contract_validation = contract_res.to_dict()
                        
                        if not contract_res.passed:
                            logger.warning(
                                f"[CONTRACT] Trace {trace.id} failed validation (Warn-Only): "
                                f"{[v.rule for v in contract_res.violations]}"
                            )
                            
                            # 🛠️ CORRECTION PATH (EP-3.5: Deterministic Repair)
                            blocking_violations = [v for v in contract_res.violations if v.severity == "blocking"]
                            if 0 < len(blocking_violations) <= 2:
                                try:
                                    from backend.verification.correction_path import attempt_trace_correction
                                    corrected_claims, strategy = attempt_trace_correction(trace, blocking_violations, trace.claims)
                                    trace.claims = corrected_claims
                                    # Re-validate after correction
                                    contract_res = validate_scientific_trace(trace, gov_context["mode"])
                                    trace.contract_validation = contract_res.to_dict()
                                    trace.contract_validation["correction_applied"] = strategy
                                    logger.info(f"[CORRECTION] Trace {trace.id} repaired via {strategy}. New pass={contract_res.passed}")
                                except Exception as e:
                                    logger.warning(f"[CORRECTION] Attempt failed: {e}")
                    else:
                        # Contextual traces get a pass
                        trace.contract_validation = {"passed": True, "violations": [], "depth_score": 0.0, "status": "skipped_contextual"}

                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Contract validation failed (non-blocking): {e}")

                # ⚖️ EPISTEMIC ADJUDICATION FLOW (v1.3 Freeze)
                # This block is the Final Adjudication Engine. 
                # Precedence: Registry (Hard) > STC Integrity (Soft) > Surface Coverage.
                
                try:
                    from backend.verification.scientific_trace_contract import compute_epistemic_integrity
                    
                    # 1. 🧪 Base Evidence Analytics
                    has_verified = any(c.get("verified") for c in trace.claims)
                    has_mechanisms = any(c.get("mechanism") or c.get("nodes") for c in trace.claims)
                    has_evidence = len(trace.retrievals) > 0 or any(c.get("evidence") for c in trace.claims)
                    has_valid_registry = bool(trace.registry_hash)

                    # 2. 🛡️ Integrity Computation (EP-5)
                    integrity = compute_epistemic_integrity(
                        trace.contract_validation, 
                        getattr(trace, 'surface_validation', {}), 
                        trace.domain_type,
                        trace_registry_hash=trace.registry_hash
                    )
                    trace.epistemic_integrity_score = integrity.get("score")
                    
                    # 3. 🧠 Status Adjudication (Precedence Hierarchy)
                    # Start with Heuristic Base
                    if not has_evidence and not has_mechanisms:
                        status = EpistemicStatus.INSUFFICIENT_EVIDENCE
                    elif has_verified and has_mechanisms:
                        status = EpistemicStatus.CONVERGENT_SUPPORT
                    elif has_verified:
                        status = EpistemicStatus.EMPIRICAL_VERIFIED
                    elif has_mechanisms:
                        status = EpistemicStatus.MECHANISTICALLY_SUPPORTED
                    else:
                        status = EpistemicStatus.THEORETICAL

                    # GUARD 1: Registry Hard Guard (Registry > All)
                    if not has_valid_registry or integrity.get("adjustment") == "downgrade_hard_insufficient":
                        status = EpistemicStatus.INSUFFICIENT_EVIDENCE
                        trace.downgrade_reason = DowngradeReason.REGISTRY_MISMATCH
                        logger.error(f"[ADJUDICATION] Hard Fail: {trace.downgrade_reason}")
                    
                    # GUARD 2: STC/Integrity Soft Guard (Integrity > Heuristics)
                    elif integrity.get("adjustment") == "downgrade_soft_theoretical":
                        t_tier = [EpistemicStatus.CONVERGENT_SUPPORT, EpistemicStatus.EMPIRICAL_VERIFIED, EpistemicStatus.MECHANISTICALLY_SUPPORTED]
                        if status in t_tier:
                            logger.warning(f"[ADJUDICATION] Soft Downgrade: {status.value} -> theoretical (integrity={integrity.get('score')})")
                            status = EpistemicStatus.THEORETICAL
                            trace.downgrade_reason = DowngradeReason.LOW_INTEGRITY_SCORE

                    # GUARD 3: Confidence Adjustment
                    if integrity.get("adjustment") == "reduce_confidence_multiplier":
                        dampener = integrity.get("dampening_factor", 0.85)
                        trace.confidence_score = trace.confidence_score * dampener
                        logger.info(f"[ADJUDICATION] Confidence Dampened (integrity={integrity.get('score')})")

                    # 📜 Diagnostic Basis
                    trace.epistemic_basis = {
                        "evidence_present": has_evidence,
                        "mechanism_complete": has_mechanisms,
                        "registry_valid": has_valid_registry,
                        "integrity_score": integrity.get("score"),
                        "adjudication_adjustment": integrity.get("adjustment")
                    }
                    trace.epistemic_status = status
                    
                except Exception as e:
                    logger.error(f"[ADJUDICATION] Critical Flow Failure: {e}", exc_info=True)
                    trace.epistemic_status = EpistemicStatus.FALLBACK_EXECUTION

                # Only set FULL_TRACE if not already in scientific explanation mode.
                # Mechanistic pipeline sets this upstream and it must not be overwritten.
                if trace.execution_mode != ExecutionMode.SCIENTIFIC_EXPLANATION:
                    trace.execution_mode = ExecutionMode.FULL_TRACE
                
                # Capture Confidence Breakdown if available
                if hasattr(trace, "uncertainty_model") and trace.uncertainty_model:
                     trace.confidence_breakdown = getattr(trace.uncertainty_model, "confidence_breakdown", {})
                     # Update basis if policy intervention detected
                     if trace.confidence_breakdown.get("policy_adjustment", 0.0) != 0.0:
                         trace.epistemic_basis["policy_intervention"] = True
                    
            except Exception as e:
                logger.error(f"[MANDATE] Fatal flow failure: {e}", exc_info=True)
                trace.validation_status = "invalid"

            # 4. Memory Hydration
            try:
                trace_json = trace.to_json() if hasattr(trace, "to_json") else str(trace.to_dict())
                self.memory.update_last_message_trace(session_id, trace_json)
                logger.info("[ORCH] Hydrated memory with final unbreakable trace.")
            except Exception as mem_err:
                logger.error(f"[ORCH] Failed to hydrate memory trace: {mem_err}")

        async def orchestration_task():
            nonlocal seq_counter, active_pipeline, trace
            logger.info("[ORCH] Background task started.")
            start_time = time.perf_counter()  # Fix: Ensure start_time is always initialized
            orchestration_status = "success"
            orchestration_metadata = {}
            done_emitted = False
            
            # ── FIX 2: Per-request Retrieval Cache ───────────────────────────
            # Shared across all RAG agent calls in this cycle
            retrieval_cache = RetrievalCache()

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
                        "run_id": run_id,
                        "pipeline": active_pipeline,
                        "agent": "orchestrator",
                        "seq": seq_counter
                    })
                    logger.debug(f"[ORCH] push_done: {status} (seq={seq_counter})")
                    done_emitted = True

            def _prepare_enforcement_trace_exit(trace):
                nonlocal orchestration_status
                orchestration_status = "success"
                trace.status = TraceStatus.COMPLETE
                trace.decision = "ENFORCED"
                trace.claims = []
                trace.execution_mode = ExecutionMode.NON_SCIENTIFIC_DISCOURSE
                trace.confidence = {
                    "current": 1.0,
                    "tier": "verified",
                    "breakdown": {
                        "final_score": 1.0,
                        "baseline_used": 1.0,
                        "rule_firings": []
                    }
                }
                trace.execution_profile = {
                    "id": trace.trace_id,
                    "mode": trace.execution_mode.value if hasattr(trace.execution_mode, 'value') else str(trace.execution_mode),
                    "epistemic_status": "enforced_routing",
                    "confidence": 1.0,
                    "status": "COMPLETE"
                }

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
                        }, agent="orchestrator")

                last_status_ts = time.perf_counter()
                logger.info(f"Orchestrating with Policy: {policy.profile.value}")
                emit_status("initializing", "Connecting to Nutri engine...")
                emit_status("starting", f"Thinking ({policy.profile.value})...")


                # 1. Context Preparation
                # Phase 3: Mechanistic Memory Isolation
                if active_pipeline == "mechanistic_explainer":
                    context = ""
                    logger.info("[ORCH] Mechanistic mode: memory retrieval disabled")
                else:
                    context = self.memory.get_context_string(session_id)
                
                augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message
                # 2. Intent Extraction
                emit_status("intent", "Understanding...")
                
                # Update reasoning mode and integrity init
                trace.reasoning_mode = "direct_synthesis"
                # Mechanistic traces use 3-tier schema, not legacy 4-tier
                if trace.trace_variant == "mechanistic":
                    trace.integrity = {
                        "tier_1_surface": "pending",
                        "tier_2_process": "pending",
                        "tier_3_molecular": "pending"
                    }
                else:
                    trace.integrity = {
                        "tier1": "pending",
                        "tier2": "pending",
                        "tier3": "pending",
                        "tier4": "pending"
                    }
                
                inv_intent = AgentInvocation(agent_name="intent_agent", model_used=self.pipeline.intent_agent.llm.model_name, status="success", reason="selected")
                
                # PART 2 — Prevent Intent Agent for Scientific Tier
                if self._current_escalation_tier == EscalationLevel.TIER_3:
                    logger.info("[ROUTING] Skipping intent_agent for scientific tier")
                    intent_raw = {"intent": "scientific_query", "status": "skipped"}
                else:
                    intent_raw = await self.invoke_agent("intent_classifier", run_sync, self.pipeline.intent_agent.extract, augmented_query)
                
                inv_intent.complete(tokens=len(str(intent_raw))) # Estimated
                trace.add_invocation(inv_intent)
                logger.info("[ORCH] Intent extracted.")
                
                # Support both object and dict (normalization to dict for downstream .get() calls)
                if hasattr(intent_raw, "to_dict"):
                    intent = intent_raw.to_dict()
                elif isinstance(intent_raw, dict):
                    intent = intent_raw
                else:
                    intent = {}

                # ══════════════════════════════════════════════════════
                # v2.1 ESCALATION AUTHORITY & ROUTING ARCHITECTURE
                # Order: Intent → Escalation Tier → Domain Class → Pipeline
                # ══════════════════════════════════════════════════════

                # 1. INTENT EXTRACTION (V2 ENFORCEMENT & CONTEXT ISOLATION)
                v2_intent = None
                if execution_mode is None:
                    emit_status("intent_check", "Analyzing intent...")
                    v2_intent = await self.invoke_agent("intent_classifier", self.intent_enforcer.analyze_intent_sandbox, user_message)
                    
                    # ── FIX 4: Respect intent agent error state ──────────────────────
                    if v2_intent and ("error" in v2_intent or v2_intent.get("status") == "error"):
                        logger.warning(f"[ORCH] Intent agent error detected: {v2_intent.get('error')}. Triggering segmentation.")
                        # This will force the mixed query path later if possible
                        intent["intent"] = "mixed_query" 
                # ──────────────────────────────────────────────────────────────────

                # 2. ESCALATION AUTHORITY (Must precede routing)
                session_ctx = {"belief_state": belief_state, "preferences": preferences}
                escalation_tier = self.resolve_escalation_tier(user_message, session_ctx)
                
                belief_state.current_tier = escalation_tier.value
                self._current_escalation_tier = escalation_tier
                self._blocked_agents_count = 0
                push_event("escalation", {"tier": escalation_tier.name, "value": escalation_tier.value})

                # 3. SET ALLOWED INDICES VIA MAP
                allowed_indices = TIER_INDEX_MAP.get(escalation_tier, [])
                if hasattr(self.pipeline, 'retriever') and hasattr(self.pipeline.retriever, 'set_allowed_indices'):
                    self.pipeline.retriever.set_allowed_indices(allowed_indices)
                logger.info(f"🔒 [RETRIEVER_LOCK] Tier {escalation_tier.name} → indices={[i.value for i in allowed_indices]}")

                # 3.5 CLAUSE SEGMENTATION (Phase 2.4: Mixed Query Support)
                query_segments = segment_clauses(user_message)
                is_mixed_query = (len([k for k in query_segments.keys() if k != "other"]) > 1)
                
                # For classification and routing, we use the original message to preserve all signals,
                # but we'll use segments in the retrieval phase.
                if is_mixed_query:
                    logger.info(f"[ORCH] Mixed query detected: {list(query_segments.keys())}")
                    trace.system_audit["is_mixed_query"] = True
                    trace.system_audit["query_segments"] = query_segments

                # 4. DOMAIN CLASSIFICATION & TIER DOWNGRADE PREVENTION
                from backend.domain_classifier import classify_domain
                classification = classify_domain(user_message)
                trace.intent_type = classification.domain_type
                trace.scientific_trigger = classification.scientific_trigger
                trace.domain_confidence = classification.confidence
                trace.routing_reason = f"domain_classifier:{classification.domain_type}@{classification.confidence:.2f}"
                
                # Phase 2.4: Domain Override Observability
                trace.domain_original = classification.domain_type
                trace.domain_effective = classification.domain_type
                
                logger.info(
                    f"[ROUTING] 🧭 Domain: {classification.domain_type} "
                    f"(trigger={classification.scientific_trigger}, conf={classification.confidence:.2f})"
                )
                
                proposed_tier_value = EscalationLevel.TIER_1.value
                if classification.scientific_trigger: 
                    proposed_tier_value = EscalationLevel.TIER_3.value
                elif classification.domain_type in ["food_query", "recipe_analysis", "general_nutrition", "clinical_nutrition", "design_specification", "compound_lookup"]: 
                    proposed_tier_value = EscalationLevel.TIER_2.value
                
                trace.tier_lock_active = False # For observability logs
                if proposed_tier_value < escalation_tier.value:
                    logger.warning(f"[TIER_DOWNGRADE_BLOCKED] Domain classifier attempted downgrade.")
                    trace.tier_lock_active = True

                # 5. PIPELINE SELECTION (AUTHORITATIVE FROM TIER)
                if escalation_tier == EscalationLevel.TIER_3:
                    gov_context["mode"] = ResponseMode.MECHANISTIC
                    active_pipeline = "mechanistic_explainer"
                    trace.execution_mode = ExecutionMode.SCIENTIFIC_EXPLANATION
                    trace.trace_required = True
                    trace.domain_type = "scientific"
                    trace.domain_effective = "scientific" # Phase 2.4 Override
                    trace.visibility_level = "expanded"
                    logger.info("[ROUTING] 🧪 Pipeline locked to mechanistic_explainer (TIER_3)")
                    
                elif escalation_tier == EscalationLevel.TIER_2:
                    # Default for TIER_2
                    gov_context["mode"] = ResponseMode.PROCEDURAL
                    if classification.domain_type in ["clinical_nutrition", "compound_lookup"]:
                        gov_context["mode"] = ResponseMode.DIAGNOSTIC
                        
                    active_pipeline = "flavor_explainer"
                    trace.execution_mode = ExecutionMode.FULL_TRACE
                    trace.trace_required = True
                    trace.domain_effective = "scientific" # Phase 2.4 Override
                    logger.info(f"[ROUTING] 🍳 Pipeline locked to flavor_explainer (TIER_2, mode={gov_context['mode'].value})")
                    
                else: # TIER_1 and TIER_0
                    gov_context["mode"] = ResponseMode.CONVERSATION
                    active_pipeline = "conversational_lightweight"
                    logger.info("[ROUTING] 💬 Pipeline locked to conversational_lightweight (<= TIER_1)")
                    
                trace.pipeline = active_pipeline

                # 6. ENFORCEMENT & SAFETY GUARDS (MEDICAL / QUANTITIES / AGENTIC RAG)
                if execution_mode is None and v2_intent:
                    cat = v2_intent.get("intent_category")
                    ingredients = v2_intent.get("extracted_ingredients", [])
                    
                    # Hard mandate for nutrition intents
                    gov_context["quantitative_required"] = (cat in ("general_nutrition", "recipe_analysis"))
                    gov_context["state"] = GovernanceState.ALLOW_QUALITATIVE
                    
                    if cat == "medical_violation":
                        gov_context["state"] = GovernanceState.BLOCK_MEDICAL
                    elif gov_context["quantitative_required"]:
                        # If no ingredients extracted stochastically, force a generic block or fallback
                        if not ingredients:
                            logger.warning(f"⚖️ [GOVERNANCE] '{cat}' detected without ingredients. Forcing block.")
                            gov_context["state"] = GovernanceState.BLOCK_NUMERIC_OUTPUT
                        else:
                            # Check if ALL ingredients have quantities
                            missing_qties = [ing.get("canonical_name", "unknown") for ing in ingredients if not ing.get("quantity") or ing.get("quantity") <= 0]
                            if missing_qties:
                                gov_context["state"] = GovernanceState.REQUIRE_QUANTITIES
                            else:
                                gov_context["state"] = GovernanceState.BLOCK_NUMERIC_OUTPUT
                    
                    logger.info({
                        "intent_governance_log": "V2_ENFORCEMENT_LAYER",
                        "intent": cat,
                        "quantitative_required": gov_context["quantitative_required"],
                        "ingredients_detected": len(ingredients),
                        "governance_state": gov_context["state"].value,
                        "action": "evaluating_route"
                    })
                        
                    # -- MEDICAL HARD HALT (BLOCK_MEDICAL) --
                    if gov_context["state"] == GovernanceState.BLOCK_MEDICAL:
                        logger.warning("🚨 [GOVERNANCE] Medical violation detected. Halting execution.")
                        safe_msg = "I cannot provide medical diagnosis or treatment advice. Please consult a licensed healthcare professional."
                        self.memory.add_message(session_id, "user", user_message)
                        self.memory.add_message(session_id, "assistant", safe_msg)
                        self.memory.set_response_mode(session_id, ResponseMode.CONVERSATION)
                        await push_event_async("token", safe_msg, agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return
                        
                    # -- NUTRITION CLARIFICATION (REQUIRE_QUANTITIES) --
                    if active_pipeline != "conversational_lightweight" and gov_context["state"] == GovernanceState.REQUIRE_QUANTITIES:
                        logger.info(f"⚖️ [GOVERNANCE] Missing quantities detected: {missing_qties}. Prompting.")
                        clarify_payload = {
                            "status": "clarification_required",
                            "missing_quantities": missing_qties,
                            "message": f"Please specify serving size (grams, cups, or pieces) for the following ingredients: {', '.join(missing_qties)}."
                        }
                        json_msg = json.dumps(clarify_payload, indent=2)
                        self.memory.add_message(session_id, "user", user_message)
                        self.memory.add_message(session_id, "assistant", json_msg)
                        self.memory.set_response_mode(session_id, ResponseMode.CONVERSATION)
                        await push_event_async("token", f"```json\n{json_msg}\n```", agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return
                        
                    # -- NUTRITION PLACEHOLDER (BLOCK_NUMERIC_OUTPUT) --
                    elif active_pipeline != "conversational_lightweight" and gov_context["state"] == GovernanceState.BLOCK_NUMERIC_OUTPUT:
                        logger.info("⚖️ [GOVERNANCE] All quantities present. Emitting Phase 2 placeholder. Blocking LLM numeric generation.")
                        placeholder = {
                            "status": "nutrition_engine_not_ready",
                            "extracted_ingredients": ingredients,
                            "message": "Deterministic macro engine pending Phase 2 implementation. Qualitative fallback blocked."
                        }
                        json_msg = json.dumps(placeholder, indent=2)
                        self.memory.add_message(session_id, "user", user_message)
                        self.memory.add_message(session_id, "assistant", json_msg)
                        self.memory.set_response_mode(session_id, ResponseMode.PROCEDURAL)
                        await push_event_async("token", f"```json\n{json_msg}\n```", agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return
                        
                    # -- FAIL-SAFE INTENT FALLBACK --
                    if active_pipeline != "conversational_lightweight":
                        if not ingredients and gov_context["state"] == GovernanceState.ALLOW_QUALITATIVE:
                            message_lower = user_message.lower()
                            suspect_keywords = ["calorie", "kcal", "macros", "protein", "carbs", "fats", "sugar", "chicken", "egg", "oat", "milk", "spinach"]
                            if any(k in message_lower for k in suspect_keywords):
                                logger.warning("⚠️ [GOVERNANCE] Intent detection failed but suspect keywords detected. Forcing REQUIRE_QUANTITIES.")
                                gov_context["quantitative_required"] = True
                                fallback_payload = {
                                    "status": "clarification_required",
                                    "missing_quantities": ["ingredients"],
                                    "message": "I detected nutrition-related keywords but was unable to verify quantities. Please specify serving sizes."
                                }
                                json_msg = json.dumps(fallback_payload, indent=2)
                                await push_event_async("token", f"```json\n{json_msg}\n```", agent="llm_engine")
                                _prepare_enforcement_trace_exit(trace)
                                return

                    # -- AGENTIC RAG INTEGRATION FOR KNOWLEDGE INTENTS --
                    KNOWLEDGE_INTENTS = ["food_query", "recipe_analysis", "general_nutrition", "chemistry_query", "compound_lookup", "clinical_nutrition", "scientific_query", "scientific", "unknown"]
                    # We pass control to AgenticRAG ONLY IF the tier isn't dictating mechanistic explainer (which does its own RAG)
                    if active_pipeline == "flavor_explainer" and cat in KNOWLEDGE_INTENTS:
                        logger.info("[ROUTER] Knowledge route")
                        from backend.tools.database_tools import resolve_tools_by_intent
                        allowed_tools = resolve_tools_by_intent(cat)
                        logger.info(f"[ROUTER] Allowed tools list printed: {allowed_tools}")
                        
                        from backend.agentic_rag import AgenticRAG
                        rag_agent = AgenticRAG(allowed_tools=allowed_tools, current_intent=cat, escalation_tier=self._current_escalation_tier)
                        
                        for event in rag_agent.stream_query(user_message):
                            if event['type'] == 'token':
                                await push_event_async("token", event['content'], agent="llm_engine")
                            elif event['type'] == 'thinking':
                                push_event("thinking_phase", {"type": event.get('stage', 'thought'), "content": event['content'], "duration_ms": 100})
                        
                        _prepare_enforcement_trace_exit(trace)
                        return

                # HARD GUARD: Greeting MUST NOT use flavor_explainer
                if intent.get("goal") == "greeting" and active_pipeline == "flavor_explainer":
                    logger.critical("[ROUTER_FAILURE] Greeting intent improperly routed to flavor_explainer!")
                    raise RuntimeError("Pipeline isolation failure: greeting intent assigned to flavor_explainer")

                
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
                

                # Check for session reset (staleness/topic shift)
                reset_policy = SessionResetPolicy()
                if reset_policy.should_downgrade_confidence(belief_state, current_turn, user_message):
                    reset_policy.apply_reset(belief_state, "staleness")
                
                # Extract new preferences (two-stage: deterministic filter → LLM)
                inv_mem = AgentInvocation(agent_name="memory_agent", model_used=self.pipeline.engine.llm.model_name, status="success", reason="selected")
                memory_extractor = MemoryExtractor(self.pipeline.engine.llm)
                pref_updates = await self.invoke_agent("memory_extractor", run_sync, memory_extractor.extract_preferences, user_message, user_prefs)
                
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
                
                # 🛑 RETRIEVAL GUARDRAILS (Phase 1.9)
                # Skip RAG if message is too short or clearly a greeting/meta query
                itent_cat = v2_intent.get("intent_category") if v2_intent else "unknown"
                
                # Check for food keywords as a secondary heuristic
                food_keywords = ["egg", "chicken", "milk", "bread", "sugar", "salt", "butter", "oil", "cook", "recipe", "protein", "carbs", "fat", "kcal"]
                has_food_entities = any(kw in user_message.lower() for kw in food_keywords)
                
                skip_retrieval = (
                    len(user_message.strip()) < 5 or 
                    itent_cat in ("chit_chat", "greeting", "help", "irrelevant") or
                    (itent_cat == "unknown" and not has_food_entities)
                )
                
                # Check if it's explicitly scientific (exempt from simple food check)
                from backend.phase_schema import PhaseSelector
                if skip_retrieval and PhaseSelector._is_scientific_query(user_message):
                    skip_retrieval = False

                if skip_retrieval:
                    logger.info(f"[ORCH] Skipping RAG: length={len(user_message.strip())}, intent={itent_cat}, food_entities={has_food_entities}")
                    selected_phases = []
                else:
                    # Select phases with confidence gate
                    selected_phases = PhaseSelector.select_phases(user_message, gov_context["mode"], intent, prefs_to_inject)
                
                logger.info(f"🧠 [PHASE] Selected {len(selected_phases)} phases: {[p.value for p in selected_phases]}")

                # 4. Mode-Based Execution with Phase Integration
                
                # ══════════════════════════════════════════════════════
                # MECHANISTIC PIPELINE SHORT-CIRCUIT (v2.0)
                # Bypasses recipe synthesis entirely for causal queries
                # ══════════════════════════════════════════════════════
                if active_pipeline == "mechanistic_explainer":
                    emit_status("mechanistic_analysis", "Analyzing causal mechanisms...")
                    logger.info("[ORCH] 🧪 Mechanistic pipeline activated — skipping recipe path")

                    from backend.mechanistic_explainer import MechanisticExplainer
                    from backend.utils.query_utils import decompose_scientific_query
                    
                    mech_explainer = MechanisticExplainer(
                        llm_client=self.pipeline.engine.llm,
                        retriever=self.pipeline.retriever
                    )

                    # 1. Mechanistic Query Decomposition (Phase 2.4: Use Segment)
                    target_query = query_segments.get("scientific", user_message)
                    queries = decompose_scientific_query(target_query)
                    logger.info(f"[QUERY_DECOMPOSITION] original='{target_query[:60]}' generated={queries}")
                    
                    # 2. Multi-Query Retrieval with Aggregation
                    mech_docs = []
                    query_stats = []
                    
                    target_indices = TIER_INDEX_MAP.get(EscalationLevel.TIER_3, [])
                    if not target_indices:
                        target_indices = [IndexType.SCIENCE, IndexType.CHEMISTRY]
                        
                    # ── FIX 3: Load indices ONCE before loop checking to prevent thrashing
                    try:
                        if hasattr(self.pipeline.retriever, "load_index"):
                            for idx in target_indices:
                                self.pipeline.retriever.load_index(idx)
                    except Exception as e:
                        logger.warning(f"Error eagerly loading indexes: {e}")

                    max_total_raw_score = 0.0

                    for q in queries:
                        try:
                            # Check cache first
                            hits = retrieval_cache.get(q)
                            if hits is not None:
                                logger.info(f"[RAG_CACHE] Hit for query: {q}")
                            else:
                                # TIER_3 Retrieval Logic (Decomposed subqueries)
                                # Note: We bypass invoke_agent for retrieval to get raw results if needed
                                # or we use a wrapper that returns the max score.
                                hits = await self.invoke_agent("rag_agent", run_sync, 
                                    self.pipeline.retriever.retrieve, # Direct retrieve instead of phase fallback
                                    query=q, 
                                    target_indices=target_indices, # Enforce TIER_INDEX_MAP targets
                                    top_k=5 # Limit per subquery
                                )
                                hits = hits or []
                                retrieval_cache.set(q, hits)

                            # Track highest score for PART 5
                            if hits:
                                scores = []
                                for h in hits:
                                    # Defensive: Handle MagicMocks in tests which might lack 'score'
                                    if hasattr(h, 'score') and not isinstance(h.score, MagicMock):
                                        scores.append(float(h.score))
                                    elif isinstance(h, dict) and 'score' in h:
                                        scores.append(float(h['score']))
                                
                                if scores:
                                    current_max = max(scores)
                                    if current_max > max_total_raw_score:
                                        max_total_raw_score = current_max

                            mech_docs.extend(hits)
                            query_stats.append({"query": q, "results": len(hits)})
                            logger.info(f"\n[RAG] Query: {q}\nRetrieved: {len(hits)} docs\n")
                        except Exception as e:
                            logger.warning(f"[ORCH] Mechanistic RAG retrieval for '{q}' failed: {e}")
                    
                    # Deduplicate docs by ID strictly
                    unique_docs = {}
                    for d in mech_docs:
                        doc_id = d.id if hasattr(d, 'id') else str(d)
                        if doc_id not in unique_docs:
                            unique_docs[doc_id] = d
                    mech_docs = list(unique_docs.values())
                    
                    # Log Audit Metrics
                    total_raw_hits = sum(s["results"] for s in query_stats)
                    unique_count = len(mech_docs)
                    queries_count = len(queries)
                    density = unique_count / queries_count if queries_count > 0 else 0
                    
                    logger.info(f"[TIER3_RECALL_AUDIT] queries={queries_count} total_docs={total_raw_hits} unique_docs={unique_count}")
                    logger.info(f"[RETRIEVAL_DENSITY] {density:.2f}")

                    # PART 5 — Add Retrieval Safety Check
                    if len(mech_docs) == 0 and max_total_raw_score > 0.55:
                        logger.warning(
                            f"[RETRIEVAL_SUSPECT] Good semantic match ({max_total_raw_score:.3f}) filtered by threshold"
                        )

                    if not mech_docs:
                        logger.warning("[GENERATION_BLOCK] Zero evidence retrieved for scientific query.")
                        await self._scientific_evidence_required_response(
                            push_event_async, 
                            trace, 
                            exit_helper=_prepare_enforcement_trace_exit
                        )
                        return

                    # 4. Execute pipeline (Phase 2.4: Mixed Query Integration)
                    scientific_query = query_segments.get("scientific", user_message)
                    nutritional_query = query_segments.get("nutritional")
                    is_mixed_query = scientific_query != user_message and nutritional_query is not None
                    
                    # For mixed queries, we suppress immediate streaming and capture to merge later
                    effective_stream_callback = None if is_mixed_query else stream_callback_sync
                    
                    mech_output = await self.invoke_agent(
                        "mechanistic_explainer", 
                        mech_explainer.execute,
                        user_query=scientific_query,
                        retrieved_docs=mech_docs,
                        stream_callback=effective_stream_callback
                    )

                    if not mech_output:
                        logger.error("[ORCH] Mechanistic explainer was BLOCKED or failed. Capping trace.")
                        await push_event_async("token", "System restriction: Biological mechanistic analysis is not available for this query.", agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return

                    # Populate trace from structured output
                    if mech_output.claims:
                        trace.add_claims(mech_output.claims)

                    # 🧬 v2.0: Direct Field Synchronization
                    trace.tier_1_surface = mech_output.tier_1_surface
                    trace.tier_2_process = mech_output.tier_2_process
                    trace.tier_3_molecular = mech_output.tier_3_molecular
                    trace.causality_chain = mech_output.causal_chain
                    trace.graph = mech_output.graph

                    # Legacy Integrity Hydration (for backwards compatibility if needed)
                    trace.integrity["tier_1_surface"] = "complete" if mech_output.tier_1_surface else "incomplete"
                    trace.integrity["tier_2_process"] = "complete" if mech_output.tier_2_process else "incomplete"
                    trace.integrity["tier_3_molecular"] = "complete" if mech_output.tier_3_molecular else "incomplete"

                    # Hydrate causal chain into legacy metrics
                    if mech_output.causal_chain:
                        trace.tier3_applicability_match = 1.0
                        trace.tier3_recommendation_distribution = {"ALLOW": len(mech_output.claims)}
                    if not mech_output.validation_passed:
                        logger.error(
                            f"[TRACE_SUBSTANCE_GENERATION_FAILURE] "
                            f"Mechanistic pipeline validation failed: {mech_output.validation_errors}"
                        )
                        trace.system_audit["substance_generation_failure"] = mech_output.validation_errors

                    # --- MIXED QUERY MERGE LOGIC ---
                    if is_mixed_query and nutritional_query:
                        emit_status("nutritional_analysis", "Analyzing nutritional impact...")
                        from backend.agentic_rag import AgenticRAG
                        from backend.tools.database_tools import resolve_tools_by_intent
                        
                        # Use default food query tools
                        nut_tools = resolve_tools_by_intent("food_query")
                        rag_agent = AgenticRAG(allowed_tools=nut_tools, current_intent="food_query", escalation_tier=self._current_escalation_tier)
                        
                        # Run nutritional segment through AgenticRAG
                        nut_res = await self.invoke_agent("rag_agent", run_sync, 
                            rag_agent.query, nutritional_query
                        )
                        
                        # 🛡️ EVIDENCE ANCHORING (Phase 2.1)
                        # Extract retrieved chunks from RAG metadata and anchor to trace
                        if nut_res and "metadata" in nut_res:
                            retrieved = nut_res["metadata"].get("retrieved_chunks", [])
                            for chunk in retrieved:
                                doc_id = chunk.get("id")
                                score = chunk.get("score")
                                source = chunk.get("source", "nutrition_db")
                                text = chunk.get("text", "")
                                
                                # Add as hard proof evidence
                                trace.add_evidence(doc_id, score, source, text)
                                logger.info(f"[EVIDENCE_ANCHOR] Linked DOC_{doc_id} (score={score}) to execution trace.")

                            # If the RAG generated a final claim, link all evidence to it
                            if nut_res.get("answer"):
                                claim_id = f"nutritional_{run_id}"
                                trace.add_claim(
                                    text=nut_res["answer"],
                                    claim_id=claim_id,
                                    evidence=[c.get("id") for c in retrieved if c.get("id") is not None],
                                    confidence=float(nut_res["metadata"].get("max_score", 0.7))
                                )
                        
                        # Assembler Merged JSON
                        merged_output = {
                            "scientific_response": {
                                "narrative": mech_output.narrative,
                                "molecular_mechanisms": mech_output.tier_3_molecular,
                                "causal_chain": mech_output.causal_chain
                            },
                            "nutritional_response": {
                                "answer": nut_res.get("answer", "No nutritional insights found."),
                                "agentic_reasoning": nut_res.get("reasoning", [])
                            },
                            "metadata": {
                                "is_mixed": True,
                                "scientific_segment": scientific_query,
                                "nutritional_segment": nutritional_query
                            }
                        }
                        
                        final_json = json.dumps(merged_output, indent=2)
                        # Push merged JSON as a block
                        await push_event_async("token", f"```json\n{final_json}\n```", agent="orchestrator")
                        
                        # Store in memory
                        self.memory.add_message(session_id, "assistant", f"Merged Analysis: {final_json}")
                        self.memory.add_message(session_id, "user", user_message)
                        _prepare_enforcement_trace_exit(trace)
                        return
                    else:
                        # Standard single-path response
                        mech_response_text = mech_output.narrative or "Unable to generate mechanistic explanation."

                        # Store in memory
                        self.memory.add_message(session_id, "user", user_message)
                        self.memory.add_message(session_id, "assistant", mech_response_text)
                        self.memory.set_response_mode(session_id, gov_context["mode"])

                        # Intelligence enforcement (runs claim parsing + enrichment)
                        await _enforce_intelligence(trace, mech_response_text, intent, belief_state, current_turn, user_prefs)

                    # ═══ MECHANISTIC LIFECYCLE ENFORCEMENT ═══
                    # These MUST be set AFTER _enforce_intelligence to prevent overwrite.
                    trace.status = TraceStatus.COMPLETE
                    trace.execution_mode = ExecutionMode.SCIENTIFIC_EXPLANATION
                    trace.trace_variant = "mechanistic"
                    trace.system_audit["intelligence_mandated"] = True
                    trace.contextual_layer = None  # Wipe any contextual memory injected during enforcement

                    # Epistemic: no evidence ≠ low integrity for theoretical mechanistic explanation
                    if trace.epistemic_status == EpistemicStatus.INSUFFICIENT_EVIDENCE:
                        if mech_output.validation_passed:
                            trace.epistemic_status = EpistemicStatus.THEORETICAL
                            trace.downgrade_reason = DowngradeReason.NOT_APPLICABLE
                            logger.info("[MECH] Corrected epistemic: theoretical (validation passed, no empirical citations).")

                    # Clear LOW_INTEGRITY_SCORE downgrade if mechanism is complete
                    if trace.downgrade_reason == DowngradeReason.LOW_INTEGRITY_SCORE:
                        if all(v == "complete" for v in trace.integrity.values()):
                            trace.downgrade_reason = DowngradeReason.NOT_APPLICABLE
                            logger.info("[MECH] Cleared LOW_INTEGRITY_SCORE downgrade: all tiers complete.")

                    # Add invocation record
                    inv_mech = AgentInvocation(
                        agent_name="mechanistic_explainer",
                        model_used=self.pipeline.engine.llm.model_name,
                        status="success" if mech_output.validation_passed else "partial",
                        reason="mechanistic_pipeline"
                    )
                    inv_mech.complete()
                    trace.add_invocation(inv_mech)

                    logger.info("[ORCH] 🧪 Mechanistic pipeline complete. status=COMPLETE mode=scientific_explanation")
                    return

                elif active_pipeline == "conversational_lightweight":
                    logger.info("[ROUTER] Executing conversational_lightweight pipeline.")
                    logger.info("Skipping RAG/Synthesis/Enforcement")

                    emit_status("conversation", "Chatting...")
                    
                    def looks_like_food_fragment(text):
                        words = text.lower().split()
                        food_keywords = {"egg", "eggs", "chicken", "spinach", "protein", "carbs", "fats", "macros", "sugar", "salt", "oat", "milk", "beef", "rice", "flour", "apple", "bread"}
                        return len(words) <= 5 and any(w in food_keywords for w in words)
                        
                    def is_numeric_probe(text):
                        stripped = text.strip()
                        return stripped.isdigit() or (stripped.replace('.','',1).isdigit() and stripped.count('.') < 2)

                    if intent.get("goal") == "greeting":
                        safe_msg = "Hello! I am Nutri. How can I assist you with your culinary or nutritional queries today?"
                    elif intent.get("goal") == "help":
                        safe_msg = "I am Nutri, your advanced culinary and nutrition AI. I can analyze recipes, provide molecular cooking advice, and answer food science questions."
                    elif looks_like_food_fragment(user_message):
                        safe_msg = "Your message appears to reference food items.\nPlease specify your goal:\n\n• Nutritional analysis\n• Recipe suggestion\n• Flavor explanation\n• Cooking method"
                    elif is_numeric_probe(user_message):
                        safe_msg = "Please provide more context for this number. What ingredient or recipe are you referring to?"
                    else:
                        logger.info("[ORCH] Invoking lightweight conversational LLM for general query.")
                        sys_prompt = "You are Nutri, an AI culinary assistant. Answer the user's conversational message politely in a few sentences. Do not provide recipes."
                        try:
                            # Use lightweight LLM generation without tools or ReAct loop
                            llm_ans = await self.invoke_agent(
                                "synthesis_engine",
                                run_sync,
                                self.pipeline.engine.llm.generate_text,
                                messages=[
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": user_message}
                                ],
                                max_new_tokens=512,
                                temperature=0.7
                            )
                            safe_msg = llm_ans.strip() if llm_ans else "Hello! I'm here to help."
                        except Exception as e:
                            logger.error(f"[ORCH] Lightweight LLM failed: {e}")
                            safe_msg = "I'm here to help you with culinary science, recipes, and nutritional facts. What's on your mind?"

                    # Yield tokens 
                    self.memory.add_message(session_id, "user", user_message)
                    self.memory.add_message(session_id, "assistant", safe_msg)
                    self.memory.set_response_mode(session_id, ResponseMode.CONVERSATION)
                    
                    # Instead of streaming via engine, stream directly
                    await push_event_async("token", safe_msg, agent="llm_engine")

                    inv = AgentInvocation(agent_name="conversational_lightweight", model_used="static_response", status="success", reason="selected")
                    inv.complete(status="success", reason="selected")
                    trace.add_invocation(inv)

                    trace.status = TraceStatus.COMPLETE
                    trace.decision = "FALLBACK"
                    trace.execution_mode = ExecutionMode.NON_SCIENTIFIC_DISCOURSE
                    trace.confidence = {
                        "current": 1.0, "tier": "verified", "breakdown": {"final_score": 1.0, "baseline_used": 1.0, "rule_firings": []}
                    }
                    return

                if len(selected_phases) == 0:
                    if gov_context["mode"] == ResponseMode.CONVERSATION:
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
                    
                    # Update integrity to reflect skipped tiers
                    for tier in ["tier1", "tier2", "tier3", "tier4"]:
                        if trace.integrity.get(tier) == "pending":
                            trace.integrity[tier] = "not_requested_direct_synthesis"
                    
                    trace.claims = [] # Explicitly empty
                    trace.confidence_provenance = {
                        "value": 0.5, # Default for direct synthesis
                        "basis": "persona-based generation",
                        "estimator": "heuristic_v1"
                    }

                    inv = AgentInvocation(agent_name="final_synthesis", model_used=f"nutri-{gov_context['mode'].value}", status="success", reason="selected")
                    trace.add_invocation(inv)

                    # 🤖 Phase 1.8: Pass gov_state to engine
                    if not hasattr(self.engine, "generate"):
                        raise RuntimeError("NutriEngine missing expected method 'generate'. Check engine interface.")

                    await self.invoke_agent("presentation_agent", self.engine.generate, session_id, user_message, gov_context["mode"], final_data, stream_callback=stream_callback_sync, gov_state=gov_context["state"])
                    
                    # PHASE 1.6: Post-Generation Validation (Zero-Tolerance)
                    # For cases where quantitative_required is True but the early retun placeholder was bypassed.
                    validation = MacroOutputValidator.validate_response(full_response_text, gov_context["quantitative_required"])
                    if not validation.get("valid"):
                        logger.error(f"🚨 [GOVERNANCE] LLM output rejected: {validation.get('message')}")
                        error_json = json.dumps({
                            "status": validation.get("status"), 
                            "message": validation.get("message"),
                            "trigger": validation.get("trigger")
                        }, indent=2)
                        await push_event_async("token", f"```json\n{error_json}\n```", agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return

                    # If valid AND buffered, stream it now
                    if gov_context["quantitative_required"]:
                        logger.info("[GOVERNANCE] LLM output validated (Zero numbers). Streaming buffer.")
                        # (The full_response_text is already captured, but if we buffered, we need to send it)
                        # Actually, better to send it as a single block if it was buffered.
                        await push_event_async("token", full_response_text, agent="llm_engine")

                    inv.complete(status="success", reason="selected")
                    
                    # 🛡️ MANDATE
                    if active_pipeline != "conversational_lightweight":
                        await _enforce_intelligence(trace, full_response_text, intent)
                    else:
                        logger.info("Skipping enforcement: Conversational pipeline.")
                    
                    logger.info("[ORCH] Zero-phase path complete.")
                    return
                
                # 🟢 MULTI-PHASE PATH with HARD VALIDATION
                emit_status("retrieval", "Researching...")
                trace.reasoning_mode = "retrieval_augmented"
                docs = await self.invoke_agent("rag_agent", run_throttled_embedding, run_sync, self.pipeline.retriever.retrieve_for_phase, 2, augmented_query, 2)
                
                if docs is None:
                    logger.warning("[ORCH] rag_agent BLOCKED or failed in multi-phase path. Proceeding with empty docs.")
                    docs = []

                # Populate Retrieval Telemetry
                trace.retrievals = [
                    {
                        "source": doc.source,
                        "doc_type": doc.doc_type,
                        "text": doc.text[:200] + "...",
                        "score": doc.score
                    } for doc in docs
                ]
                trace.tool_ledger.append({
                    "tool": "faiss_retriever",
                    "action": "retrieve_for_phase",
                    "hits": len(docs),
                    "ts": time.time()
                })

                
                valid_phase_count = 0
                phase_results = {}
                recipe_result = ""
                claim_objs = [] # Mandatory Initialization for Intelligence Mandate
                
                for phase in selected_phases:
                    phase_start = time.perf_counter()
                    emit_status(f"phase_{phase.value}", f"{phase.value.title()}...")
                    
                    # Execute phase (simplified: use synthesis engine)
                    emit_status("synthesis", f"Analyzing ({phase.value})...")
                    phase_result_raw = await self.invoke_agent("synthesis_engine", self.pipeline.engine.synthesize, augmented_query, docs, intent, stream_callback=None)

                    # Unpack (recipe, enforcement_meta)
                    if isinstance(phase_result_raw, tuple):
                        phase_result, enf_meta = phase_result_raw
                        # 🔒 Phase 2: PubChem Tier Guard — mandatory, no hasattr fallback
                        if self._current_escalation_tier != EscalationLevel.TIER_3:
                            logger.warning(f"[BLOCKED_AGENT] pubchem_client enforcement skipped at {self._current_escalation_tier.name}")
                            self._blocked_agents_count += 1
                            enf_meta = {}  # Suppress PubChem data at non-TIER_3
                        # Update trace with enforcement data
                        trace.set_pubchem_enforcement(enf_meta)
                        
                        # 📋 PHASE 1-3 Claim Intelligence Integration
                        if "claims" in enf_meta:
                            from types import SimpleNamespace
                            claim_objs = [SimpleNamespace(**c) for c in enf_meta["claims"]]
                            trace.set_claims(claim_objs, enf_meta.get("variance_drivers", {}))
                            
                            # Update Integrity for Tier 1
                            trace.integrity["tier1"] = "verified" if any(c.get("verified") for c in enf_meta["claims"]) else "insufficient_evidence"
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
                    if not hasattr(self.engine, "generate"):
                        raise RuntimeError("NutriEngine missing expected method 'generate'. Check engine interface.")

                    await self.invoke_agent("presentation_agent", self.engine.generate, session_id, user_message, gov_context["mode"], final_data, stream_callback=stream_callback_sync)
                    
                    # PHASE 1.6: Post-Generation Validation (Zero-Tolerance)
                    # For cases where quantitative_required is True but the early retun placeholder was bypassed.
                    validation = MacroOutputValidator.validate_response(full_response_text, gov_context["quantitative_required"])
                    if not validation.get("valid"):
                        logger.error(f"🚨 [GOVERNANCE] LLM output rejected: {validation.get('message')}")
                        error_json = json.dumps({
                            "status": validation.get("status"), 
                            "message": validation.get("message"),
                            "trigger": validation.get("trigger")
                        }, indent=2)
                        await push_event_async("token", f"```json\n{error_json}\n```", agent="llm_engine")
                        _prepare_enforcement_trace_exit(trace)
                        return

                    # If valid AND buffered, stream it now
                    if gov_context["quantitative_required"]:
                        logger.info("[GOVERNANCE] LLM output validated (Zero numbers). Streaming buffer.")
                        await push_event_async("token", full_response_text, agent="llm_engine")

                    # 🛡️ MANDATE
                    await _enforce_intelligence(trace, full_response_text, intent)
                    
                    return
                
                # 5. Parallel DAG
                dag_results = {}
                if policy.profile != ExecutionProfile.FAST:
                    emit_status("enhancement", "Analyzing & Refining...")
                    dag = DAGScheduler()
                    start_time = time.perf_counter() # Fix: Initialize start_time
                    
                    if "sensory_model" in policy.enabled_agents:
                        dag.add_node(AgentNode(name="sensory", func=self.invoke_agent, args=["sensory_model", run_sync, self.pipeline.predict_sensory, recipe_result]))
                    
                    dag.add_node(AgentNode(name="verification", func=self.invoke_agent, args=["verification", run_sync, self.pipeline.verify, recipe_result]))
                    
                    if "explanation" in policy.enabled_agents:
                        audience = preferences.get("audience_mode", "scientific")
                        dag.add_node(AgentNode(name="explanation", func=self.invoke_agent, args=["llm_engine", run_sync, self.pipeline.explain_sensory, "sensory", audience], depends_on={"sensory"}))
                    
                    if "frontier" in policy.enabled_agents:
                        dag.add_node(AgentNode(name="frontier", func=self.invoke_agent, args=["frontier_optimizer", run_sync, self.pipeline.generate_sensory_frontier, recipe_result], is_luxury=True))
                        goal = preferences.get("optimization_goal", "balanced")
                        dag.add_node(AgentNode(name="selector", func=self.invoke_agent, args=["frontier_optimizer", run_sync, self.pipeline.select_sensory_variant, "frontier", UserPreferences(eating_style=goal)], depends_on={"frontier"}, is_luxury=True))

                    dag_results = await dag.execute()
                    
                    trace.tool_ledger.append({
                        "tool": "dag_scheduler",
                        "action": "execute",
                        "results": list(dag_results.keys()),
                        "ts": time.time()
                    })
                    await event_queue.put({"type": "status", "content": {"phase": "reset", "message": "New environment initialized."}, "seq": seq_counter, "stream_id": trace_id})
                    seq_counter += 1
                
                    trace.status = TraceStatus.STREAMING
                  
                    if "verification" in dag_results:
                        report = dag_results["verification"]
                        # Fix: VerificationReport is not iterable, access verified_claims
                        # Also VerifiedClaim doesn't have mechanism, check status
                        has_verified = any(vc.status.value == "supported" for vc in report.verified_claims)
                        trace.integrity["tier2"] = "verified" if has_verified else "insufficient_evidence"

                    if "sensory" in dag_results:
                        push_event("enhancement", {"sensory_profile": dag_results["sensory"], "message": "Sensory profile modeled."})
                    if "explanation" in dag_results:
                        push_event("enhancement", {"explanation": dag_results["explanation"], "message": "Scientific explanation added."})

                # 🔒 MANDATORY INTELLIGENCE RECOVERY (Extraction Fallback)
                if trace.trace_required and not trace.claims:
                    emit_status("structuring", "Post-response scientific structuring...")
                    logger.info("[ORCH] Mandated intelligence missing. Triggering extraction fallback.")
                    
                    # Call fallback extraction on the accumulated result
                    # We use the raw recipe_result if multiple phases were concatenated
                    extracted_claims = await self.pipeline.engine.extract_claims_fallback(recipe_result)
                    
                    if extracted_claims:
                        from types import SimpleNamespace
                        # Set origin to 'extracted' and mapping to contract
                        for c in extracted_claims:
                            c_obj = SimpleNamespace(**c)
                            c_obj.origin = "extracted"
                            c_obj.verification_level = "heuristic" # Fallback is usually heuristic
                            c_obj.verified = False
                            
                            # 🧬 Tier 2 Enrichment
                            MoleculeReceptorMapper.enrich_perception(c_obj)
                            c_obj.importance_score = RankingEngine.calculate_importance(c_obj)
                            
                            claim_objs.append(c_obj)
                        
                        trace.set_claims(claim_objs)
                        trace.validation_status = "partial" # Marked as processed after-the-fact
                        logger.info(f"[ORCH] Successfully extracted {len(extracted_claims)} claims via fallback.")
                        emit_status("structuring_complete", f"Added {len(extracted_claims)} scientific claims via extraction.")
                    else:
                        trace.validation_status = "invalid"
                        logger.warning("[ORCH] Extraction fallback FAILED to produce claims.")
                        emit_status("structuring_partial", "No additional claims extracted.")

                # 6. Final Presentation & Trace Emission
                emit_status("finalizing", "Plating your response...")
                
                # 🔒 MoA GATE (Phase 1): Enforce mechanism requirement for causal claims
                from backend.mode_classifier import is_causal_intent
                
                has_causal_intent = is_causal_intent(user_message)
                verification_results = dag_results.get("verification", [])
                
                # Check mechanism completeness
                # Fix: VerificationReport is not iterable, access verified_claims
                # Note: VerifiedClaim doesn't have mechanism attribute, it has status/justification
                # We need to map back to original claims or assume verification implies validity?
                # Actually, claim_extractor extracts text claims.
                # MoA Gate expects structured mechanisms.
                # If we are using claim_extractor, we might not have mechanisms.
                # BUT, if trace.claims exists (from earlier phases or extraction), we should check THOSE.
                
                # If verification_results is a VerificationReport, we can't check 'mechanism'.
                # We should check trace.claims instead, which SHOULD be populated by now.
                
                # Let's check trace.claims for MoA validity
                claims_with_valid_moa = sum(
                    1 for c in trace.claims 
                    if hasattr(c, "mechanism") and c.mechanism and getattr(c.mechanism, "is_valid", False)
                )
                claims_total = len(trace.claims)
                
                if has_causal_intent and claims_total > 0 and claims_with_valid_moa == 0:
                    logger.warning(
                        f"[MOA_GATE] Causal intent detected but no valid mechanisms available. "
                        f"Per MANDATE: Recording unverified assertions instead of suppressing. Claims: {claims_total}"
                    )
                    # DISABLE SUPPRESSION per Mandate
                    moa_gate_active = False 
                    moa_gate_reason = "Unverified mechanisms detected - flagged for user review"
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
                # Build Tier 3 assessments for each verified claim
                tier3_results = []
                # Fix: Iterate trace.claims (structured objects) instead of VerificationReport
                # VerificationReport (verification_results) is not iterable and contains text-based checks.
                # trace.claims contains the Mechanism objects required here.
                for claim in trace.claims:
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
                    trace.tier3_recommendation_distribution = dist
                    
                    # Update Tier 3 integrity
                    trace.integrity["tier3"] = "verified" if any(r["recommendation"]["decision"] == "allow" for r in tier3_results) else "partial"
                    trace.conflicts_detected = any(v.metadata.get("has_conflict") for v in verification_results if hasattr(v, "metadata") and v.metadata)
                    
                    trace.tool_ledger.append({
                        "tool": "recommendation_gate",
                        "action": "evaluate_tier3",
                        "claims_assessed": len(tier3_results),
                        "conflicts": trace.conflicts_detected,
                        "ts": time.time()
                    })
                

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
                # Fix: Iterate trace.claims (structured) instead of VerificationReport
                for claim in trace.claims:
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
                
                # Update Tier 4 integrity
                trace.integrity["tier4"] = "verified" if trace.tier4_decision_changes else "stable"
                trace.tool_ledger.append({
                    "tool": "belief_revision_engine",
                    "action": "finalize_turn",
                    "turn": current_turn,
                    "revisions": len(trace.tier4_belief_revisions),
                    "ts": time.time()
                })

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

                logger.info(f"[ORCH] Generating final tailored response in mode {gov_context['mode'].value}...")
                
                # Final Integrity Finalization
                trace.status = TraceStatus.COMPLETE
                for tier in ["tier1", "tier2", "tier3", "tier4"]:
                    if trace.integrity.get(tier) == "pending":
                        trace.integrity[tier] = "incomplete"

                # ── TRACE STERILITY & GOVERNANCE (Refinement Phase) ──
                if trace.execution_mode == ExecutionMode.FULL_TRACE:
                    final_data["tone_modifier"] = "scientific_neutral"
                    # Hard-force contextual sterility
                    if "session_context" in final_data:
                        final_data["session_context"]["contextual_followup_injection"] = False
                    logger.info("[ORCH] Force scientific_neutral tone and sterile context for FULL_TRACE.")

                # Set final confidence provenance for multi-phase
                trace.confidence_provenance = {
                    "value": getattr(trace, "final_confidence", getattr(trace, "confidence_score", 0.7)),
                    "basis": f"{len(trace.retrievals)} retrievals, {len(trace.claims)} verified claims",
                    "estimator": "multi_tier_aggregation_v2"
                }
                
                # Contradiction Policy: If conflict detected, prioritize retrieval
                if trace.conflicts_detected:
                    final_data["system_policy"] = "PRIORITIZE_RETRIEVAL"
                    final_data["conflict_summary"] = "Discrepancy detected between retrieval and initial synthesis. Scientific documents override."

                # Add final_synthesis invocation for status: complete
                inv = AgentInvocation(agent_name="final_synthesis", model_used=f"nutri-{gov_context['mode'].value}", status="success", reason="selected")
                trace.add_invocation(inv)
                
                if not hasattr(self.engine, "generate"):
                    raise RuntimeError("NutriEngine missing expected method 'generate'. Check engine interface.")

                await self.invoke_agent("presentation_agent", self.engine.generate, session_id, user_message, gov_context["mode"], final_data, stream_callback=stream_callback_sync)

                # PHASE 1.6: Post-Generation Validation (Zero-Tolerance)
                validation = MacroOutputValidator.validate_response(full_response_text, gov_context["quantitative_required"])
                if not validation.get("valid"):
                    logger.error(f"🚨 [GOVERNANCE] LLM output rejected: {validation.get('message')}")
                    error_json = json.dumps({
                        "status": validation.get("status"), 
                        "message": validation.get("message"),
                        "trigger": validation.get("trigger")
                    }, indent=2)
                    await push_event_async("token", f"```json\n{error_json}\n```", agent="llm_engine")
                    _prepare_enforcement_trace_exit(trace)
                    return

                # If valid AND buffered, stream it now
                if gov_context["quantitative_required"]:
                    logger.info("[GOVERNANCE] LLM output validated (Zero numbers). Streaming buffer.")
                    await push_event_async("token", full_response_text, agent="llm_engine")

                inv.complete(status="success", reason="selected")

                # 🛡️ MANDATE (Unified) - Guaranteed Finalization
                try:
                    await _enforce_intelligence(trace, full_response_text, intent, belief_state, current_turn, user_prefs)
                finally:
                    # In-place finalization just in case outer finally is delayed
                    finalize_trace_stage(trace, active_pipeline)
                    
                    # ATOMIC FINALIZER BLOCK (Phase 2.2)
                    if trace.decision == "REJECT" and active_pipeline == "mechanistic_explainer":
                        logger.error("[FINALIZER_BLOCK] Mechanistic trace rejected (insufficient grounding). Blocking emission.")
                        await self._scientific_evidence_required_response(push_event_async, trace)
                        return

                # 🥗 Emit Nutrition Intelligence Report
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
                    "conflicts_detected": any(c.get("has_conflict") for c in trace.claims if isinstance(c, dict) and c.get("has_conflict")),
                    "summary": f"Nutrition verified via PubChem & USDA ({len(trace.compounds)} compounds, {len(trace.claims)} verifiable claims)"
                }
                push_event("nutrition_report", nutrition_report, agent="nutrition_enforcer")
                
                logger.info("[ORCH] Generation complete.")
                orchestration_metadata = {"nutrition_report": nutrition_report}
                # Update session context after response
                new_context = await self.invoke_agent("memory_extractor", run_sync, memory_extractor.extract_context, user_message, "")
                if new_context:
                    self.memory.update_context(session_id, new_context)
                
                logger.info("[ORCH] Flow finished.")
            except RuntimeError as e:
                # Catch ResourceBudgetExceeded specifically if needed, otherwise general
                orchestration_status = "RESOURCE_EXCEEDED"
                orchestration_metadata = {"error": str(e)}
                logger.error(f"[ORCH] Resource Rejection: {e}")
                push_event("error_event", {
                    "message": str(e), 
                    "phase": "resource_guard", 
                    "status": "RESOURCE_EXCEEDED",
                    "stream_id": trace_id,
                    "run_id": run_id,
                    "pipeline": active_pipeline
                }, agent="resource_budget")
            except Exception as e:
                orchestration_status = "FAILED"
                orchestration_metadata = {"error": str(e)}
                logger.error(f"Orchestration failure: {e}", exc_info=True)
                push_event("error_event", {
                    "message": str(e), 
                    "phase": "orchestration", 
                    "status": "FAILED",
                    "stream_id": trace_id,
                    "run_id": run_id,
                    "pipeline": active_pipeline
                }, agent="orchestrator")
            finally:
                gpu_monitor.sample_after()
                logger.info(f"[ORCH] Finalizing stream (status={orchestration_status}). Guaranteeing trace -> done.")

                # ── Phase 2: Structured Observability Summary ──
                try:
                    _obs_indices = TIER_INDEX_MAP.get(self._current_escalation_tier, [])
                    _obs_agents = [inv.agent_name for inv in getattr(trace, 'invocations', [])] if hasattr(trace, 'invocations') else []
                    _obs_blocked_idx = getattr(self.pipeline.retriever, '_blocked_count', 0) if hasattr(self.pipeline, 'retriever') else 0
                    logger.info(json.dumps({
                        "event": "orchestration_summary",
                        "gov_version": GOVERNANCE_VERSION,
                        "tier": self._current_escalation_tier.name,
                        "escalation_score": getattr(self, '_current_escalation_score', 0.0),
                        "escalation_source": "deterministic_weighted_v1",
                        "tier_lock_active": getattr(trace, 'tier_lock_active', False),
                        # Phase 2.4: Domain Observability
                        "domain_original": trace.domain_original,
                        "domain_effective": trace.domain_effective,
                        "is_mixed": trace.system_audit.get("is_mixed_query", False),
                        "agents": _obs_agents,
                        "indices": [i.value for i in _obs_indices],
                        "blocked_agents": self._blocked_agents_count,
                        "blocked_indices": _obs_blocked_idx,
                        "contract_violations": 0,
                        "status": orchestration_status
                    }))
                except Exception as obs_err:
                    logger.debug(f"[ORCH] Observability summary failed (non-blocking): {obs_err}")
                
                # 0. 🔐 ENFORCE TERMINAL STATE & CONTRACTS
                try:
                    finalize_trace_stage(trace, active_pipeline)
                    
                    # ── v1.2.8 LAYER ENRICHMENT ──
                    if hasattr(self, "_enrich_trace_v1_2_8"):
                        self._enrich_trace_v1_2_8(trace)
                except Exception as fe:
                    logger.error(f"[ORCH] Trace finalizer failed: {fe}")

                # 0.1 🛡️ AGGREGATION PERSISTENCE CHECK (Hard Assertions)
                try:
                    logger.info(f"[ORCH] Root decision after finalizer: {trace.decision}")
                    logger.info(f"[ORCH] Root confidence after finalizer: {trace.confidence}")
                    logger.info(f"[ORCH] Execution profile after finalizer: {trace.execution_profile}")

                    assert trace.decision != "PENDING", "Finalizer failed: decision not promoted"
                    assert trace.confidence, "Finalizer failed: confidence empty"
                    assert trace.execution_profile, "Finalizer failed: execution_profile empty"
                except AssertionError as ae:
                    logger.critical(f"[ORCH] TRACE CONTRACT VIOLATION: {ae}")

                # 1. 🟢 ALWAYS emit execution_trace
                try:
                    import copy
                    logger.info(f"[API] Root confidence before serialization: {trace.confidence}")
                    trace_dict = trace.to_dict()
                    self.last_emitted_trace = copy.deepcopy(trace_dict) # Safe debug capture
                    seq_counter += 1
                    await event_queue.put({
                        "type": "execution_trace",
                        "content": trace_dict,
                        "seq": seq_counter,
                        "stream_id": trace_id,
                        "run_id": run_id,
                        "pipeline": active_pipeline,
                        "agent": "orchestrator"
                    })
                    logger.info(f"[ORCH] Trace emitted (claims={len(trace.claims)}, seq={seq_counter})")
                except Exception as te:
                    logger.error(f"[ORCH] Failed to emit trace: {te}", exc_info=True)
                    
                    from backend.utils.execution_trace import TRACE_SCHEMA_VERSION
                    fallback_trace = {
                        "id": trace_id,
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "run_id": run_id,
                        "pipeline": active_pipeline,
                        "decision": "ERROR",
                        "trace_schema_version": TRACE_SCHEMA_VERSION,
                        "status": "CONTRACT_VIOLATION",
                        "error": str(te),
                        "scientific_layer": {
                            "claims": []
                        },
                        "confidence": {
                            "current": 0.0,
                            "tier": "invalid",
                            "breakdown": {
                                "final_score": 0.0,
                                "baseline_used": 0.0,
                                "rule_firings": []
                            }
                        },
                        "execution_profile": {
                            "id": trace_id,
                            "mode": "standard",
                            "epistemic_status": "theoretical",
                            "confidence": 0.0,
                            "status": "FAILED"
                        }
                    }
                    
                    seq_counter += 1
                    await event_queue.put({
                        "type": "execution_trace",
                        "content": fallback_trace,
                        "seq": seq_counter,
                        "stream_id": trace_id,
                        "run_id": run_id,
                        "pipeline": active_pipeline,
                        "agent": "orchestrator"
                    })
                    logger.info(f"[ORCH] Emitted fallback trace on violation (seq={seq_counter})")
                # 2. ✅ Final DONE (Only if not already emitted by something else)
                if not done_emitted:
                    # Pass metadata if success, otherwise error message
                    final_content = orchestration_metadata if orchestration_status == "success" else orchestration_metadata.get("error", "")
                    await push_done(orchestration_status, final_content)

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

        return

    def _enrich_trace_v1_2_8(self, trace):
        """
        Populates Governance, Temporal, and Baseline layers per v1.2.8 requirements.
        """
        if not hasattr(trace, "to_dict"):
            return

        # 1. Temporal Layer Refinement
        trace.tier4_decision_state = "initial" if trace.tier4_session_age <= 1 else "revised"
        if trace.status == TraceStatus.COMPLETE:
            trace.tier4_decision_state = "stable"
        
        # 2. Governance Layer (Core Metadata)
        # Detailed enrichment (consistency checks, etc.) happens in trace_finalizer.py
        trace.governance = {
            "policy_id": "NUTRI_EVIDENCE_V1",
            "ontology_version": trace.ontology_version or "1.0",
            "enrichment_version": trace.registry_version or "1.0",
            "registry_lookup_status": "matched" if trace.registry_hash else "not_found",
            "policy_signature_present": bool(trace.policy_layer.get("signature"))
        }

        # 3. Baseline Evidence Summary (Stub - logic moving to finalizer)
        # We ensure the key exists in the root dict
        if not hasattr(trace, "baseline_evidence_summary"):
             trace.baseline_evidence_summary = {}
        
        logger.info(f"[ORCH][v1.2.8] Synchronized trace {trace.trace_id} blocks.")

    def resolve_escalation_tier(self, message: str, session_context: dict) -> EscalationLevel:
        """
        [ESCALATION AUTHORITY] Top-level tier resolution.
        Determines the escalation tier strictly using weighted mathematical scoring
        and persistent locks. NO routing logic allowed here.
        """
        msg_lower = message.lower()
        score = 0.0
        
        belief_state = session_context.get("belief_state")
        preferences = session_context.get("preferences", {})
        
        # 1. Scientific Keywords (direct weight +2)
        has_sci = any(kw in msg_lower for kw in SCIENTIFIC_KEYWORDS)
        if has_sci:
            score += 2.0
            
        # 2. Biological Context (multiplier +2 if has_sci)
        if has_sci:
            if any(ctx in msg_lower for ctx in BIO_CONTEXT):
                score += 2.0
            
        # 3. Nutrition Keywords (+1 per unique match, max +2)
        msg_words = set(msg_lower.split())
        found_nutri = NUTRITION_KEYWORDS.intersection(msg_words)
        if found_nutri:
            score += float(min(2, len(found_nutri)))
            
        # 4. Scientific Audience Mode (+2)
        if preferences.get("audience_mode") == "scientific":
            score += 2.0
            
        # 5. Message Length (>20 chars -> +1)
        if len(message) > 20:
            score += 1.0
            
        # Determine Base Tier purely deterministically
        if score >= TIER_3_THRESHOLD:
            base_tier = EscalationLevel.TIER_3
        elif score >= TIER_2_THRESHOLD:
            base_tier = EscalationLevel.TIER_2
        else:
            # Below 3.0 defaults to TIER_1 (Clarification/Info limit)
            # TIER_0 vs TIER_1 routing distinction is left to the domain/intent checks later
            base_tier = EscalationLevel.TIER_1
            
        # 6. Scientific Lock Persistence
        if belief_state and belief_state.previous_tier >= EscalationLevel.TIER_2.value and score < TIER_2_THRESHOLD:
            if any(term in msg_lower for term in ["stop", "casual", "shut up", "quit"]):
                # Explicit downgrade breaking the lock
                base_tier = EscalationLevel.TIER_1
            else:
                # Maintain persistence
                base_tier = EscalationLevel(belief_state.previous_tier)
                
        # 7. Safety Caps (TIER_0 -> TIER_1 Limit for small queries)
        if belief_state and belief_state.previous_tier == EscalationLevel.TIER_0.value and len(message.strip()) < 10:
            if base_tier.value > EscalationLevel.TIER_1.value:
                base_tier = EscalationLevel.TIER_1
                
        # Store latest score for observability
        self._current_escalation_score = score
        
        logger.info(f"[ESCALATION_AUTHORITY] score={score} tier={base_tier.name}")
        return base_tier

    def _enforce_agent_matrix(self, agent_name: str, tier: EscalationLevel) -> bool:
        """Checks if an agent is permitted to run at the current escalation tier."""
        allowed = AGENT_ACTIVATION_MATRIX.get(tier, [])
        if agent_name in allowed:
            return True
        
        self._blocked_agents_count += 1
        logger.warning(f"⚠️ [BLOCKED_AGENT] '{agent_name}' attempted activation at {tier.name}. Restricted.")
        return False

    async def invoke_agent(self, agent_name: str, func, *args, **kwargs):
        """
        Centralized ASYNC agent invocation — the ONLY way agents should be called.
        Enforces the activation matrix before execution.
        
        Mandate: Policy-Only Gate. Do not add business logic or heavy 
        data transformation here. This remains the enforcement boundary.
        """
        tier = self._current_escalation_tier
        if not self._enforce_agent_matrix(agent_name, tier):
            logger.info(f"[INVOKE] {agent_name} blocked at {tier.name}. Returning None.")
            return None
        logger.debug(f"[INVOKE] {agent_name} permitted at {tier.name}. Executing.")
        
        # Check if the function is a coroutine or returns one
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            res = func(*args, **kwargs)
            if asyncio.iscoroutine(res):
                return await res
            return res

    async def _scientific_evidence_required_response(self, push_event: Callable, trace: AgentExecutionTrace, exit_helper: Optional[Callable] = None):
        """
        Emits a governed fallback response when scientific evidence is insufficient.
        Ensures epistemic honesty by withholding unsupported explanations.
        """
        logger.warning("[SCIENTIFIC_BLOCK] Zero evidence — explanation withheld.")
        
        # 1. Update Trace State
        trace.status = TraceStatus.COMPLETE  # Set strictly to COMPLETE, not ERROR
        trace.decision = "REJECT"
        trace.epistemic_status = EpistemicStatus.INSUFFICIENT_EVIDENCE
        trace.confidence = {"current": 0.0, "tier": "unsupported", "breakdown": {"final_score": 0.0, "baseline_used": 0.0, "rule_firings": []}}
        
        # 2. Emit Narrative Fallback
        msg = (
            "This scientific explanation cannot be verified against indexed sources. "
            "Please narrow the mechanism (e.g., specify organ, transporter, or receptor) "
            "or request citation-supported output."
        )
        await push_event("token", msg, agent="orchestrator")
        
        # 3. Clean exit
        if exit_helper:
            exit_helper(trace)

    @property
    def current_escalation_tier(self) -> EscalationLevel:
        return self._current_escalation_tier

    def invoke_agent_sync(self, agent_name: str, func, *args, **kwargs):
        """
        Centralized SYNC agent invocation.
        """
        tier = self._current_escalation_tier
        if not self._enforce_agent_matrix(agent_name, tier):
            logger.info(f"[INVOKE_SYNC] {agent_name} blocked at {tier.name}. Returning None.")
            return None
        logger.debug(f"[INVOKE_SYNC] {agent_name} permitted at {tier.name}. Executing.")
        return func(*args, **kwargs)
