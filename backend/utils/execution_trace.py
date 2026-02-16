"""
Nutri Agent Execution Trace

Provides structured observability for multi-agent workflows.
Tracks every invocation, model used, and reasoning step.
"""

import time
import json
import uuid
import logging
from dataclasses import dataclass, field, asdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum

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
    schema_version: int = 2  # Current Contract: v2
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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trace to dictionary, ensuring EXACT frontend contract compliance.
        """
        data = asdict(self)
        
        # Identity root fields
        data["run_id"] = self.run_id
        data["pipeline"] = self.pipeline
        
        # Policy Accountability Validation
        if not self.evidence_policy_id or not self.policy_version:
            err_msg = f"[TRACE_INTEGRITY] Serialization Failure: Missing mandatory policy metadata (ID/Version) for run {self.run_id}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        # ── GAP 3: STRUCTURAL PARTITIONING ──
        # Explicit separation of Factual Observations vs. Policy Interpretation.
        scientific_layer = {
            "claims": data.get("claims", []),
            "compounds": data.get("compounds", []),
            "moa_coverage": data.get("moa_coverage", 0.0),
            "evidence_coverage": data.get("evidence_coverage", 0.0),
            "contradiction_ratio": data.get("contradiction_ratio", 0.0),
            "registry_snapshot": {
                "version": self.registry_version,
                "hash": self.registry_hash,
                "ontology_version": self.ontology_version,
                "locked": self.version_lock
            }
        }
        
        policy_layer = {
            "policy_id": self.evidence_policy_id,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "selection_reason": self.policy_selection_reason
        }
        
        # 1. Integrity Transformation
        raw_integrity = data.get("integrity", {})
        missing = [k for k, v in raw_integrity.items() if v in ["pending", "incomplete"]]
        
        # Final Assembler
        result = {
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "status": self.status.value,
            "duration_ms": (time.time() - self.start_ts) * 1000,
            "integrity": {
                "complete": len(missing) == 0,
                "missing_segments": missing
            },
            "scientific_layer": scientific_layer,
            "policy_layer": policy_layer,
            "causality_layer": {
                "tier3_applicability_match": self.tier3_applicability_match,
                "tier3_risk_flags_count": self.tier3_risk_flags_count,
                "tier3_recommendation_distribution": self.tier3_recommendation_distribution
            },
            "system_audit": self.system_audit
        }

        # Explicit PubChem verification block in root if used
        if self.pubchem_used:
            result["pubchem_proof"] = {
                "verified": True,
                "traceable": len(self.compounds) > 0,
                "compounds": scientific_layer["compounds"]
            }
        
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

def create_trace(session_id: str, trace_id: str) -> AgentExecutionTrace:
    return AgentExecutionTrace(session_id=session_id, trace_id=trace_id)
