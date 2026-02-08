"""
Nutri Agent Execution Trace

Provides structured observability for multi-agent workflows.
Tracks every invocation, model used, and reasoning step.
"""

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)

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
    start_ts: float = field(default_factory=time.time)
    schema_version: int = 1  # Contract version for UI adaptation
    invocations: List[AgentInvocation] = field(default_factory=list)
    system_audit: Dict[str, Any] = field(default_factory=dict)
    
    # 📋 Claim-Level Intelligence Fields
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
        logger.info(f"[AGENT_TRACE] {invocation.agent_name} | {invocation.status} | {invocation.duration_ms:.2f}ms")
    
    def set_claims(self, claims: List[Any], variance_drivers: Dict[str, float] = None):
        """
        Record verified claims and variance drivers.
        """
        self.claims = [
            {
                "claim_id": c.claim_id,
                "verified": c.verified,
                "source": c.source,
                "confidence": c.confidence,
                "text": c.metadata.get("text") if c.metadata else None,
                "mechanism": c.mechanism.to_dict() if hasattr(c, "mechanism") and c.mechanism else None
            } for c in claims
        ]
        if variance_drivers:
            self.variance_drivers = variance_drivers
        
        # Phase 3: Calculate MoA Metrics
        claims_with_valid_moa = sum(
            1 for c in claims 
            if hasattr(c, "mechanism") and c.mechanism and c.mechanism.is_valid
        )
        self.moa_coverage = (claims_with_valid_moa / len(claims) * 100) if claims else 0.0
        
        # Track broken steps
        self.broken_step_histogram = {}
        for c in claims:
            if hasattr(c, "mechanism") and c.mechanism and not c.mechanism.is_valid:
                # Try to identify which step type caused the break
                if c.mechanism.break_reason:
                    # Simple heuristic: extract step type from break reason
                    for step_type in ["compound", "interaction", "physiology", "outcome"]:
                        if step_type in c.mechanism.break_reason.lower():
                            self.broken_step_histogram[step_type] = self.broken_step_histogram.get(step_type, 0) + 1
                            break
        
        # Track source contribution per step
        self.source_contribution = {}
        for c in claims:
            if hasattr(c, "mechanism") and c.mechanism and c.mechanism.steps:
                for step in c.mechanism.steps:
                    source = step.evidence_source
                    self.source_contribution[source] = self.source_contribution.get(source, 0) + 1
        
        logger.info(f"[CLAIM_TRACE] Recorded {len(self.claims)} claims with {len(self.variance_drivers)} drivers")
        logger.info(f"[MOA_METRICS] Coverage: {self.moa_coverage:.1f}%, Broken: {self.broken_step_histogram}, Sources: {self.source_contribution}")
    
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
        Convert trace to dictionary, including PubChem proof data.
        """
        data = asdict(self)
        
        # Explicit PubChem verification block in root if used
        if self.pubchem_used:
            data["pubchem_proof"] = {
                "verified": True,
                "traceable": len(self.compounds) > 0,
                "compounds": data.get("compounds", [])
            }
        
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

def create_trace(session_id: str, trace_id: str) -> AgentExecutionTrace:
    return AgentExecutionTrace(session_id=session_id, trace_id=trace_id)
