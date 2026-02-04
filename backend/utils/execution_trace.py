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
    invocations: List[AgentInvocation] = field(default_factory=list)
    system_audit: Dict[str, Any] = field(default_factory=dict)
    
    # 📋 Claim-Level Intelligence Fields
    claims: List[Dict[str, Any]] = field(default_factory=list)
    variance_drivers: Dict[str, float] = field(default_factory=dict)
    
    # 🔬 PubChem Enforcement Fields
    pubchem_used: bool = False
    pubchem_compounds: List[CompoundTrace] = field(default_factory=list)
    confidence_score: float = 0.0 # Base confidence
    final_confidence: float = 0.0 # Uncertainty-adjusted confidence
    pubchem_proof_hash: str = ""
    enforcement_failures: List[str] = field(default_factory=list)

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
                "text": c.metadata.get("text") if c.metadata else None
            } for c in claims
        ]
        if variance_drivers:
            self.variance_drivers = variance_drivers
        
        logger.info(f"[CLAIM_TRACE] Recorded {len(self.claims)} claims with {len(self.variance_drivers)} drivers")

    def set_pubchem_enforcement(self, enforcement_meta: Dict[str, Any]):
        """
        Attach PubChem enforcement metadata to the trace.
        
        Args:
            enforcement_meta: Dictionary from FoodSynthesisEngine.synthesize()
        """
        self.pubchem_used = enforcement_meta.get("pubchem_used", False)
        self.confidence_score = enforcement_meta.get("confidence_score", 0.0)
        self.final_confidence = enforcement_meta.get("final_confidence", self.confidence_score)
        self.pubchem_proof_hash = enforcement_meta.get("pubchem_proof_hash", "")
        self.enforcement_failures = enforcement_meta.get("enforcement_failures", [])
        
        # Build compound trace list
        resolved_data = enforcement_meta.get("resolved_compounds", [])
        for rd in resolved_data:
            self.pubchem_compounds.append(CompoundTrace(
                name=rd.get("name", ""),
                cid=rd.get("cid", 0),
                endpoint="compound/cid/JSON",  # Canonical endpoint
                source="pubchem",
                cached=rd.get("cached", False),
                resolution_time_ms=rd.get("resolution_time_ms", 0),
                molecular_formula=rd.get("properties", {}).get("molecular_formula"),
                molecular_weight=rd.get("properties", {}).get("molecular_weight")
            ))
            
        logger.info(
            f"[PUBCHEM_TRACE] used={self.pubchem_used}, "
            f"confidence={self.confidence_score:.2f} (Final: {self.final_confidence:.2f}), "
            f"compounds={len(self.pubchem_compounds)}, "
            f"hash={self.pubchem_proof_hash}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trace to dictionary, including PubChem proof data.
        
        This dictionary is emitted in SSE events to the frontend.
        """
        data = asdict(self)
        
        # Add explicit PubChem verification block
        if self.pubchem_used:
            data["pubchem_verification"] = {
                "verified": True,
                "confidence": self.confidence_score,
                "proof_hash": self.pubchem_proof_hash,
                "compounds_count": len(self.pubchem_compounds),
                "failures_count": len(self.enforcement_failures)
            }
        
        # Add Claim-Level block
        if self.claims:
            verified_count = sum(1 for c in self.claims if c.get("verified"))
            data["verification_summary"] = {
                "verified_claims": verified_count,
                "unverified_claims": len(self.claims) - verified_count,
                "total_claims": len(self.claims)
            }
        
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

def create_trace(session_id: str, trace_id: str) -> AgentExecutionTrace:
    return AgentExecutionTrace(session_id=session_id, trace_id=trace_id)
