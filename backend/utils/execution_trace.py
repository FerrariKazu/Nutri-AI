"""
Nutri Agent Execution Trace

Provides structured observability for multi-agent workflows.
Tracks every invocation, model used, and reasoning step.
"""

import time
import json
import uuid
import logging
import hashlib
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum
from jsonschema import validate, ValidationError
from backend.utils.trace_substance_classifier import classify_trace_substance

# ── v1.2.7 API GOVERNANCE CONSTANTS ──
TRACE_SCHEMA_VERSION = "1.2.8"
TRACE_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), f"trace_schema_v{TRACE_SCHEMA_VERSION.replace('.', '_')}.json")

class EpistemicStatus(Enum):
    """
    Formal scientific classification of a claim's validity based on trace properties.
    """
    EMPIRICAL_VERIFIED = "empirical_verified"
    MECHANISTICALLY_SUPPORTED = "mechanistically_supported"
    CONVERGENT_SUPPORT = "convergent_support"
    THEORETICAL = "theoretical"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_REGISTRY_SNAPSHOT = "no_registry_snapshot"
    POLICY_ONLY = "policy_only"
    FALLBACK_EXECUTION = "fallback_execution"
    NOT_APPLICABLE = "not_applicable"

class ExecutionMode(Enum):
    FULL_TRACE = "full_trace"
    SCIENTIFIC_EXPLANATION = "scientific_explanation"  # v2.0: Mechanistic pipeline
    FALLBACK = "fallback"
    POLICY_ONLY = "policy_only"
    NON_SCIENTIFIC_DISCOURSE = "non_scientific_discourse"

class TraceDomainType(str, Enum):
    """Domain classification for trace enforcement routing."""
    SCIENTIFIC = "scientific"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"

class TraceVisibility(str, Enum):
    """Backend-dictated UI panel visibility."""
    HIDDEN = "hidden"
    COLLAPSIBLE = "collapsible"
    EXPANDED = "expanded"

class DowngradeReason(str, Enum):
    """Standardized reasons for scientific -> contextual downgrades."""
    NO_ENRICHED_CLAIMS = "NO_ENRICHED_CLAIMS"
    LOW_INTEGRITY_SCORE = "LOW_INTEGRITY_SCORE"
    REGISTRY_MISMATCH = "REGISTRY_MISMATCH"
    SURFACE_VALIDATION_FAILURE = "SURFACE_VALIDATION_FAILURE"
    POLICY_CONSTRAINT = "POLICY_CONSTRAINT"
    NOT_APPLICABLE = "NOT_APPLICABLE"

from backend.ranking_engine import RankingEngine

logger = logging.getLogger(__name__)

class TraceStatus(str, Enum):
    INIT = "INIT"
    STREAMING = "STREAMING"
    ENRICHING = "ENRICHING"
    VERIFIED = "VERIFIED"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

@dataclass
class CompoundTrace:
    """
    Trace record for a single PubChem-resolved compound.
    
    Provides proof that a specific compound was verified via PubChem API.
    """
    name: str
    cid: int
    endpoint: str  # PubChem API endpoint used
    source: Literal["pubchem"] = "pubchem"
    cached: bool = False
    resolution_time_ms: int = 0
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None

@dataclass
class AgentInvocation:
    agent_name: str
    model_used: str
    status: str  # "success" | "skipped" | "failed"
    reason: str  # "selected" | "no_intent" | "memory_hit" | error message
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    duration_ms: Optional[float] = None
    input_hash: Optional[str] = None
    output_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, status: str = "success", reason: str = "selected", tokens: Optional[int] = None):
        self.end_ts = time.time()
        self.duration_ms = (self.end_ts - self.start_ts) * 1000
        self.status = status
        self.reason = reason
        self.output_tokens = tokens

@dataclass
class AgentExecutionTrace:
    session_id: str
    trace_id: str
    run_id: str = ""
    pipeline: str = "flavor_explainer"
    start_ts: float = field(default_factory=time.time)
    schema_version: float = 1.3  # STC Contract v1.3 Freeze
    status: TraceStatus = TraceStatus.INIT
    trace_required: bool = False  # Mandated by Classifier
    validation_status: str = "valid"  # "valid" | "invalid" | "partial"
    coverage_metrics: Dict[str, Any] = field(default_factory=dict) # e.g. {"mechanisms": ["fermentation"]}
    invocations: List[AgentInvocation] = field(default_factory=list)
    system_audit: Dict[str, Any] = field(default_factory=dict)
    
    # 📋 Intelligence Trace Fields (Epistemic Honesty)
    reasoning_mode: str = "direct_synthesis" # "direct_synthesis" | "retrieval_augmented"
    integrity: Dict[str, str] = field(default_factory=dict) # tier_id -> "verified" | "partial" | "insufficient_evidence"
    confidence_provenance: Dict[str, Any] = field(default_factory=dict) # { value, basis, estimator }
    conflicts_detected: bool = False
    tool_ledger: List[Dict[str, Any]] = field(default_factory=list) # List of tool calls/results
    retrievals: List[Dict[str, Any]] = field(default_factory=list) # Document hits
    
    # 📝 Claims & Variance (CRITICAL: Must be fields for assertions)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    variance_drivers: Dict[str, float] = field(default_factory=dict)
    
    # 🔬 PubChem Enforcement Fields (P0 Requirements)
    pubchem_used: bool = False
    compounds: List[CompoundTrace] = field(default_factory=list)
    confidence_score: float = 0.0 # Base confidence
    final_confidence: float = 0.0 # Uncertainty-adjusted confidence
    pubchem_proof_hash: str = ""
    enforcement_failures: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.start_ts = time.time()
        if not self.run_id:
            self.run_id = str(uuid.uuid4())
    
    # 🧬 MoA Metrics (Phase 3)
    moa_coverage: float = 0.0  # % of claims with valid mechanisms
    broken_step_histogram: Dict[str, int] = field(default_factory=dict)  # Broken by step type
    source_contribution: Dict[str, int] = field(default_factory=dict)  # Steps by source
    
    # 🧪 Evidence Metrics (Phase 9)
    evidence_coverage: float = 0.0  # % of claims with verified evidence
    contradiction_ratio: float = 0.0  # % of evidence set that is contradictory
    
    # 📜 Policy Accountability (Phase 10)
    evidence_policy_id: str = ""
    policy_version: str = ""
    policy_hash: str = ""
    policy_selection_reason: str = ""  # (Phase 11 / Gap 3)
    
    # 🔒 Trace Initialization Barrier (Phase 11 / Gap 2)
    version_lock: bool = False
    registry_version: str = ""
    registry_hash: str = ""
    ontology_version: str = ""
    registry_scope: str = "global"
    
    # 🏷️ Trace Variant tagging
    trace_variant: Literal["standard", "fallback", "mechanistic"] = "standard"
    
    # 🧠 Epistemic Authority (Upgrade 27/Refinement)
    epistemic_status: EpistemicStatus = EpistemicStatus.THEORETICAL
    epistemic_basis: Dict[str, bool] = field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.FULL_TRACE
    confidence_breakdown: Dict[str, Any] = field(default_factory=dict)
    
    # 🧬 Mechanistic v2.0 Fields
    causality_chain: List[Dict[str, Any]] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict) # { "nodes": [], "edges": [] }
    tier_1_surface: Optional[str] = None
    tier_2_process: Optional[str] = None
    tier_3_molecular: Optional[str] = None
    
    # ⚖️ Root-Level Conclusion
    decision: str = "PENDING"  # ACCEPT | REJECT | PARTIAL | PENDING
    policy_layer: Dict[str, Any] = field(default_factory=dict)
    confidence: Dict[str, Any] = field(default_factory=dict)
    execution_profile: Dict[str, Any] = field(default_factory=dict)
    causality: Dict[str, Any] = field(default_factory=dict)
    governance: Dict[str, Any] = field(default_factory=lambda: {
        "policy_id": "NONE",
        "ontology_version": "1.0",
        "enrichment_version": "1.0",
        "registry_lookup_status": "not_applicable",
        "ontology_consistency": True,
        "unique_ontologies": ["1.0"],
        "policy_signature_present": False
    })
    baseline_evidence_summary: Dict[str, Any] = field(default_factory=dict)
    
    # 🧪 Scientific Instrument Metadata (SSOT)
    # ⚠ CONTRACT LOCK:
    # Any changes to serialization shape must:
    # 1. Update TRACE_SCHEMA_VERSION
    # 2. Update frontend types
    # 3. Update snapshot test
    # Do not modify field names casually.
    trace_schema_version: str = TRACE_SCHEMA_VERSION

    # 🔬 Deterministic Trace Enforcement (Option 1 / Phase 1 & 2.4)
    domain_type: str = "scientific"          # TraceDomainType.value (legacy/general)
    domain_original: str = ""                # Phase 2.4: Raw classifier output before override
    domain_effective: str = ""               # Phase 2.4: Final domain used for enforcement
    visibility_level: str = "expanded"       # TraceVisibility.value
    domain_confidence: float = 0.0           # Classification signal strength (0.60-0.95)
    contextual_layer: Dict[str, Any] = field(default_factory=dict)
    surface_validation: Dict[str, Any] = field(default_factory=dict)
    contract_validation: Dict[str, Any] = field(default_factory=dict)
    epistemic_integrity_score: Optional[float] = None  # None for contextual, 0.0-1.0 for scientific/hybrid
    downgrade_reason: DowngradeReason = DowngradeReason.NOT_APPLICABLE
    
    # 🧠 Intent Classification (v1.3.2 Routing)
    intent_type: str = "recipe_synthesis"  # recipe_synthesis | mechanistic_explanation | diagnostic | conversation
    routing_reason: str = "default"        # Telemetry for why a pipeline was chosen
    scientific_trigger: bool = False        # v2.0: True if domain classifier detected scientific signal

    def lock_versions(self, reg_v: str, reg_h: str, ont_v: str):
        """
        Seals the version snapshot into the trace.
        Must be called BEFORE any resolution logic.
        """
        self.registry_version = reg_v
        self.registry_hash = reg_h
        self.ontology_version = ont_v
        self.version_lock = True
        logger.info(f"[TRACE_BARRIER] Locked versions: reg={reg_v} ont={ont_v}")

    # 🎯 Tier 3 Metrics (Contextual Causality)
    tier3_applicability_match: float = 0.0  # Average applicability match score
    tier3_risk_flags_count: int = 0  # Total risk flags detected
    tier3_recommendation_distribution: Dict[str, int] = field(default_factory=dict)  # ALLOW/WITHHOLD/REQUIRE_MORE_CONTEXT counts
    tier3_missing_context_fields: List[str] = field(default_factory=list)  # Aggregated missing fields

    # 🕐 Tier 4 Metrics (Temporal Consistency)
    tier4_decision_changes: Dict[str, str] = field(default_factory=dict)  # claim_id → change_type
    tier4_uncertainty_resolved_count: int = 0
    tier4_clarification_attempts: int = 0
    tier4_confidence_delta: Dict[str, float] = field(default_factory=dict)  # claim_id → delta
    tier4_saturation_triggered: bool = False
    tier4_belief_revisions: List[str] = field(default_factory=list)  # Audit trail
    tier4_session_age: int = 0  # Turns since start
    tier4_decision_state: str = "initial"
    tier4_resolved_deltas: int = 0

    def add_invocation(self, invocation: AgentInvocation):
        self.invocations.append(invocation)
        dur = invocation.duration_ms if invocation.duration_ms is not None else 0.0
        logger.info(f"[AGENT_TRACE] {invocation.agent_name} | {invocation.status} | {dur:.2f}ms")
    
    def add_claims(self, new_claims: List[Any], variance_drivers: Dict[str, float] = None):
        """
        Safely MERGE new claims into the trace.
        IMMUTABILITY GUARD: Never overwrites, only appends unique claims.
        """
        import inspect
        try:
            caller = inspect.stack()[1]
            location = f"{caller.filename.split('/')[-1]}:{caller.lineno}"
        except:
            location = "unknown"

        logger.info(f"[TRACE_AUDIT] OP=ADD_CLAIMS before={len(self.claims)} incoming={len(new_claims)} location={location}")

        processed_claims = []
        existing_ids = {c["id"] for c in self.claims}

        for c in new_claims:
            # 1. Normalize to dict
            if isinstance(c, dict):
                c_dict = c.copy()
                if "importance_score" not in c_dict:
                    c_dict["importance_score"] = 0.2
            else:
                # Handle SimpleNamespace or other objects
                c_dict = {
                    "id": getattr(c, "id", getattr(c, "claim_id", str(uuid.uuid4()))),
                    "text": getattr(c, "text", getattr(c, "statement", None)),
                    "statement": getattr(c, "statement", getattr(c, "text", None)), # Sync both
                    "domain": getattr(c, "domain", "biological"),
                    "importance_score": getattr(c, "importance_score", 0.2),
                    "verified": getattr(c, "verified", getattr(c, "isVerified", False)),
                    "verification_level": getattr(c, "verification_level", "heuristic"),
                    "confidence": getattr(c, "confidence", None),
                    "mechanism": getattr(c, "mechanism", None),
                    "receptors": getattr(c, "receptors", []),
                    "compounds": getattr(c, "compounds", []),
                    "perception_outputs": getattr(c, "perception_outputs", []),
                    "nodes": getattr(c, "nodes", []),
                }
            
            c_id = c_dict.get("id") or c_dict.get("claim_id") or str(uuid.uuid4())
            c_dict["id"] = c_id
            c_dict["claim_id"] = c_id # Support both
            
            c_dict["run_id"] = self.run_id
            c_dict["pipeline"] = self.pipeline
            
            # Log incoming claim state
            has_mech = c_dict.get("mechanism") is not None
            logger.info(f"[TRACE_ADD] id={c_id} keys={list(c_dict.keys())} mechanism_present={has_mech}")
            
            if c_id in existing_ids:
                continue

            # Ensure decision mapping exists for backwards compatibility
            if "decision" not in c_dict:
                status = c_dict.get("status", "verified") if "status" in c_dict else ("verified" if c_dict.get("verified") else "pending")
                c_dict["decision"] = self._map_status_to_decision(status)

            processed_claims.append(c_dict)
            existing_ids.add(c_id)

        # MERGE
        self.claims.extend(processed_claims)
        
        # Update Variance Drivers (Merge)
        if variance_drivers:
            self.variance_drivers.update(variance_drivers)
        
        # 🏆 Re-Sort by Importance (Safe get for robustness)
        self.claims = sorted(self.claims, key=lambda x: x.get("importance_score", 0.0), reverse=True)

        self._recalculate_metrics()
        
        logger.info(f"[TRACE_AUDIT] OP=COMPLETE total={len(self.claims)} added={len(processed_claims)}")

    def set_claims(self, claims: List[Any], variance_drivers: Dict[str, float] = None):
        """DEPRECATED: Alias for add_claims to enforce immutability."""
        self.add_claims(claims, variance_drivers)

    def _recalculate_metrics(self):
        """Recalculate MoA and coverage metrics on the full claim set."""
        mechanisms = set()
        for c in self.claims:
            # c is now a dict
            noch_mech = c.get("mechanism_type")
            if noch_mech and noch_mech != "heuristic":
                mechanisms.add(noch_mech)

        self.coverage_metrics["mechanisms"] = list(mechanisms)
        
        # Simple heuristic for valid MoA in flat dicts (if verified/allow)
        claims_with_valid_moa = sum(
            1 for c in self.claims 
            if c.get("decision") == "ALLOW" and c.get("mechanism_type") != "heuristic"
        )
        self.moa_coverage = (claims_with_valid_moa / len(self.claims) * 100) if self.claims else 0.0
        
        # Calculate Evidence Metrics (Phase 9)
        total_claims = len(self.claims)
        if total_claims > 0:
            claims_with_ev = sum(1 for c in self.claims if c.get("evidence"))
            self.evidence_coverage = round(claims_with_ev / total_claims, 2)
            
            all_evidence = []
            for c in self.claims:
                ev_list = c.get("evidence")
                if isinstance(ev_list, list):
                    all_evidence.extend(ev_list)
            
            if all_evidence:
                contradictions = sum(1 for e in all_evidence if e.get("effect_direction") == "contradictory")
                self.contradiction_ratio = round(contradictions / len(all_evidence), 2)

        logger.info(f"[MOA_METRICS] Coverage: {self.moa_coverage:.1f}% | Evidence Cov: {self.evidence_coverage:.2f} | Ctrl Ratio: {self.contradiction_ratio:.2f}")

    def _map_status_to_decision(self, status: str) -> str:
        """verified -> ALLOW, rejected -> WITHHOLD, pending -> REQUIRE_MORE_CONTEXT"""
        mapping = {
            "verified": "ALLOW",
            "rejected": "WITHHOLD",
            "pending": "REQUIRE_MORE_CONTEXT"
        }
        return mapping.get(status, "ALLOW")
    
    def set_pubchem_enforcement(self, enforcement_meta: Dict[str, Any]):
        """
        Attach PubChem enforcement metadata to the trace.
        """
        self.pubchem_used = enforcement_meta.get("pubchem_used", True) # Default to true if called
        self.confidence_score = enforcement_meta.get("confidence_score", 0.0)
        self.final_confidence = enforcement_meta.get("final_confidence", self.confidence_score)
        self.pubchem_proof_hash = enforcement_meta.get("pubchem_proof_hash", "")
        self.enforcement_failures = enforcement_meta.get("enforcement_failures", [])
        
        # Build compound trace list
        resolved_data = enforcement_meta.get("resolved_compounds", [])
        for rd in resolved_data:
            self.compounds.append(CompoundTrace(
                name=rd.get("name", ""),
                cid=rd.get("cid", 0),
                endpoint=rd.get("endpoint", "/rest/pug/compound/cid/{cid}/property"),
                source="pubchem",
                cached=rd.get("cached", False),
                resolution_time_ms=rd.get("resolution_time_ms", 0),
                molecular_formula=rd.get("molecular_formula"),
                molecular_weight=rd.get("molecular_weight")
            ))
            
        logger.info(
            f"[PUBCHEM_TRACE] used={self.pubchem_used}, "
            f"confidence={self.confidence_score:.2f}, "
            f"compounds={len(self.compounds)}"
        )

    def _compute_baseline_evidence_summary(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Derived strictly from scientific_layer. Non-persistent.
        """
        total_claims = len(claims)
        total_ev = 0
        study_types = set()
        empirical_types = {"RCT", "meta-analysis", "human_trial"}
        empirical_present = False

        for c in claims:
            ev_list = c.get("evidence", [])
            if isinstance(ev_list, list):
                total_ev += len(ev_list)
                for ev in ev_list:
                    s_type = ev.get("study_type", "unknown")
                    study_types.add(s_type)
                    if s_type in empirical_types:
                        empirical_present = True

        highest_study = "none"
        if "meta-analysis" in study_types: highest_study = "meta-analysis"
        elif "RCT" in study_types: highest_study = "RCT"
        elif "human_trial" in study_types: highest_study = "human_trial"
        elif study_types:
            highest_study = sorted(list(study_types))[0]

        return {
            "total_claims": total_claims,
            "total_evidence_entries": total_ev,
            "highest_study_type": highest_study,
            "empirical_support_present": empirical_present
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trace to dictionary, ensuring EXACT frontend contract compliance (v1.2.7).
        """
        # Identity root fields - MANDATORY CONTRACT
        if not self.trace_id or not self.session_id or not self.run_id:
            err = f"[TRACE_INTEGRITY] Identity Failure: Missing mandatory ID fields (trace_id={self.trace_id}, session_id={self.session_id}, run_id={self.run_id})"
            logger.error(err)
            raise ValueError(err)

        # ── PHASE 1: PRE-PROCESSING & NORMALIZATION ──
        final_epistemic_status = str(self.epistemic_status.value if hasattr(self.epistemic_status, 'value') else self.epistemic_status).lower()
        
        # v1.2.6: CENTRALIZED MODE MAPPING (Single source of truth)
        raw_pipeline = self.pipeline if self.pipeline else "standard"
        if raw_pipeline in ["mechanistic_explainer", "scientific_pipeline"]:
            external_mode = "scientific_explanation"
        elif raw_pipeline in ["standard", "conversation"]:
            external_mode = "conversation"
        elif raw_pipeline == "moderation":
            external_mode = "moderation"
        else:
            external_mode = "standard"

        # Claims must be nested strictly in scientific_layer (v1.2.7 Requirement)
        claims_list = [c for c in self.claims if isinstance(c, dict)]
        
        def _serialize_confidence(conf: Any) -> dict:
            if isinstance(conf, (int, float)):
                conf = {"current": float(conf), "tier": "theoretical", "breakdown": {}}
            elif not isinstance(conf, dict):
                conf = {}
                
            current_score = conf.get("current", conf.get("score", 0.0))
            raw_tier = conf.get("tier", "theoretical")
            bd_raw = conf.get("breakdown", {})
            if not isinstance(bd_raw, dict): bd_raw = {}
            
            final_sc = bd_raw.get("final_score", bd_raw.get("final", current_score))
            
            serialized_conf = {
                "current": current_score,
                "tier": raw_tier.lower() if isinstance(raw_tier, str) else "theoretical",
                "breakdown": {
                    "final_score": final_sc,
                    "baseline_used": bd_raw.get("baseline_used", bd_raw.get("baseline", final_sc)),
                    "rule_firings": bd_raw.get("rule_firings", [])
                }
            }
            
            assert set(serialized_conf.keys()) == {"current", "tier", "breakdown"}, f"Confidence keys violation: {serialized_conf.keys()}"
            assert set(serialized_conf["breakdown"].keys()) == {"final_score", "baseline_used", "rule_firings"}, f"Breakdown keys violation: {serialized_conf['breakdown'].keys()}"
            
            return serialized_conf

        # Ensure claim-level confidence parity and strict schema compliance
        for i, claim in enumerate(claims_list):
            if "confidence" in claim:
                claim["confidence"] = _serialize_confidence(claim["confidence"])
            
            # Additional rigorous cleaning per-claim
            clean_claim = {
                "id": claim.get("id", f"claim_{i}"),
                "confidence": claim.get("confidence")
            }
            
            # Pass through any other valid fields that aren't restricted
            for k, v in claim.items():
                if k not in ["id", "confidence"]:
                    clean_claim[k] = v
                    
            claims_list[i] = clean_claim

        # ── PHASE 2: SUBSTANCE VERIFICATION ──
        temp_data = {"scientific_layer": {"claims": claims_list}, "execution_mode": external_mode}
        substance_result = classify_trace_substance(temp_data)
        
        # Root breakdown fallback and strict struct
        clean_root_confidence = _serialize_confidence(self.confidence)

        # ── PHASE 3: NESTED STRUCTURE ASSEMBLY ──
        result = {
            "id": self.trace_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "pipeline": self.pipeline,
            "decision": self.decision,
            "confidence": clean_root_confidence,
            "execution_profile": {
                "id": self.trace_id,
                "mode": external_mode,
                "epistemic_status": final_epistemic_status,
                "confidence": self.confidence.get("current", self.confidence.get("score", 0.0)),
                "status": "COMPLETE"
            },
            "scientific_layer": {
                "claims": claims_list,
                "compounds": [asdict(c) if hasattr(c, "to_dict") == False and hasattr(c, "__dataclass_fields__") else (c.to_dict() if hasattr(c, "to_dict") else c) for c in self.compounds],
                "moa_coverage": getattr(self, "moa_coverage", 0.0),
                "evidence_coverage": getattr(self, "evidence_coverage", 0.0),
                "contradiction_ratio": getattr(self, "contradiction_ratio", 0.0),
                "registry_snapshot": {
                    "version": self.registry_version,
                    "registry_hash": self.registry_hash,
                    "ontology_version": self.ontology_version,
                    "locked": self.version_lock,
                    "scope": json.dumps(self.registry_scope) if isinstance(self.registry_scope, dict) else str(self.registry_scope)
                }
            },
            "causality": {
                "chain": self.causality_chain or [],
                "applicability": self.tier3_applicability_match,
                "riskCount": self.tier3_risk_flags_count,
            },
            "domain_type": self.domain_type,
            "domain_original": self.domain_original,
            "domain_effective": self.domain_effective,
            "trace_metrics": {
                "substance_state": substance_result.get("reason", "VERIFIED" if substance_result.get("has_substance") else "NO_SUBSTANCE"),
                "biological_claim_count": substance_result.get("biological_claim_count", 0),
                "anchor_count": substance_result.get("anchor_count", 0)
            },
            "epistemic_status": str(self.epistemic_status.value if hasattr(self.epistemic_status, 'value') else self.epistemic_status).lower(),
            "execution_mode": self.execution_mode.value if hasattr(self.execution_mode, 'value') else str(self.execution_mode),
            "temporal_layer": {
                "session_age": self.tier4_session_age,
                "belief_revisions": len(self.tier4_belief_revisions),
                "decision_state": self.tier4_decision_state,
                "resolved_deltas": self.tier4_resolved_deltas
            },
            "governance": self.governance,
            "baseline_evidence_summary": self._compute_baseline_evidence_summary(claims_list),
            "system_audit": self.system_audit,
            "graph": self.graph or {}
        }

        # ── PHASE 4: BACKEND SELF-VALIDATION (FIREWALL) ──
        self._validate_contract(result)

        # ── PHASE 5: DETERMINISTIC CONTRACT HASHING ──
        # sort_keys + separators ensures hash is invariant to dict order or whitespace
        canonical_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
        contract_hash = hashlib.sha256(canonical_json.encode()).hexdigest()[:8]
        logger.info(f"[TRACE_CONTRACT_HASH] version={TRACE_SCHEMA_VERSION} hash={contract_hash} run_id={self.run_id}")
        
        return result

    def _validate_contract(self, data: Dict[str, Any]):
        """Formal jsonschema gate for v1.2.7 governance."""
        
        # ── INVARIANT ASSERTION INTERCEPT ──
        assert isinstance(data.get("confidence", {}).get("breakdown", {}).get("rule_firings", []), list), "Root rule_firings must uniformly be a list"

        for i, claim in enumerate(data.get("scientific_layer", {}).get("claims", [])):
            assert isinstance(claim.get("confidence", {}).get("breakdown", {}).get("rule_firings", []), list), f"Claim {i} rule_firings must uniformly be a list"

        try:
            # Import here to allow graceful failure if not installed in some envs
            from jsonschema import validate, ValidationError
            
            if not os.path.exists(TRACE_SCHEMA_PATH):
                logger.warning(f"[TRACE_VALIDATION_WARNING] Schema file missing at {TRACE_SCHEMA_PATH}. Skipping validation.")
                return

            logger.info(f"[TRACE_SCHEMA] Using schema version {TRACE_SCHEMA_VERSION}")
            with open(TRACE_SCHEMA_PATH, "r") as f:
                schema = json.load(f)
            
            validate(instance=data, schema=schema)
        except ImportError:
            logger.error("[TRACE_VALIDATION_CRITICAL] jsonschema library missing. Cannot enforce contract.")
            # We don't raise here to allow the system to keep running, but log the failure
        except ValidationError as e:
            err_msg = f"[TRACE_CONTRACT_VIOLATION] version={TRACE_SCHEMA_VERSION} path={list(e.path)} message={e.message}"
            logger.error(err_msg)
            # We raise here because a contract violation is a programmatic error that MUST be fixed
            raise ValueError(err_msg) from e
        except Exception as e:
            logger.error(f"[TRACE_VALIDATION_ERROR] Unexpected failure during schema validation: {str(e)}")

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

def create_trace(session_id: str, trace_id: str) -> AgentExecutionTrace:
    return AgentExecutionTrace(session_id=session_id, trace_id=trace_id)
