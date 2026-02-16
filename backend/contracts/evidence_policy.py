"""
Evidence Policy Contract v1.0
Immutable, versioned, hashable policy artifacts.

This is the SSOT for all confidence computation in Nutri.
No component may compute confidence outside this contract.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyRule:
    """A single, named rule within a policy."""
    rule_id: str
    description: str
    category: str  # "study_type_weight" | "sample_size_bonus" | "recency_bonus" | "retraction_penalty" | "contradiction_penalty"
    parameters: tuple  # Frozen — must be tuple of (key, value) pairs for hashability

    def get_params(self) -> Dict[str, Any]:
        """Convert frozen parameters back to a dict for computation."""
        return dict(self.parameters)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "category": self.category,
            "parameters": dict(self.parameters)
        }


@dataclass(frozen=True)
class EvidencePolicy:
    """
    Versioned, hashable policy artifact.
    Must be immutable at runtime.
    """
    policy_id: str
    version: str
    published_at: str  # ISO 8601
    
    # Governance Metadata (Vulnerability #1)
    author: str
    review_board: str
    approval_date: str
    
    # Identity Binding (Gap 1)
    policy_document_hash: str   # SHA256 of the logic definition
    attestation: str            # Formal signature or audit statement
    baseline_score: float  # Starting score before rules apply
    tie_break_logic: str  # "highest_grade_wins" | "most_recent_wins" | "largest_n_wins"
    
    tier_thresholds: Tuple[Tuple[float, str], ...]  # Tuple of (threshold, tier_name) pairs
    rule_set: Tuple[PolicyRule, ...]  # Tuple of PolicyRule (frozen for hashability)
    
    supersedes: Optional[str] = None

    def validate(self):
        """
        Hard-validation of policy integrity.
        Fails if mandatory governance fields are missing or if hash is mismatched.
        """
        if not self.author or not self.review_board or not self.approval_date:
            raise RuntimeError(f"Policy {self.policy_id} is lacking mandatory governance metadata.")
        
        if not self.policy_document_hash or not self.attestation:
            raise RuntimeError(f"Policy {self.policy_id} is missing identity binding (hash/attestation).")
        
        # Verify internal hash consistency
        actual_hash = self._compute_logic_hash()
        if actual_hash != self.policy_document_hash:
            raise RuntimeError(
                f"Policy {self.policy_id} TEMPER DETECTED: "
                f"Declared hash {self.policy_document_hash} does not match computed logic hash {actual_hash}."
            )

    def _compute_logic_hash(self) -> str:
        """Compute deterministic SHA-256 hash of policy content (excluding governance metadata)."""
        logic_dict = {
            "policy_id": self.policy_id,
            "version": self.version,
            "published_at": self.published_at,
            "rule_set": [r.to_dict() for r in self.rule_set],
            "tier_thresholds": dict(self.tier_thresholds),
            "tie_break_logic": self.tie_break_logic,
            "baseline_score": self.baseline_score
        }
        canonical = json.dumps(logic_dict, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def get_rules(self) -> List[PolicyRule]:
        return list(self.rule_set)

    def get_tier_thresholds(self) -> Dict[float, str]:
        return dict(self.tier_thresholds)

    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash of policy content."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "published_at": self.published_at,
            "policy_hash": self.compute_hash() if False else "deferred",  # Avoid recursion
            "rule_set": [r.to_dict() for r in self.rule_set],
            "tier_thresholds": dict(self.tier_thresholds),
            "tie_break_logic": self.tie_break_logic,
            "baseline_score": self.baseline_score
        }

    def to_dict_with_hash(self) -> Dict[str, Any]:
        """Full serialization including hash (for trace embedding)."""
        d = self.to_dict()
        # Compute hash from the hashless dict
        canonical = json.dumps(d, sort_keys=True, default=str)
        d["policy_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return d


@dataclass(frozen=True)
class RuleFiring:
    """Record of a single rule execution within a confidence computation."""
    rule_id: str
    category: str
    input_value: Any  # What the rule evaluated
    contribution: float  # Score delta from this rule
    fired: bool  # Whether the rule actually contributed


@dataclass
class ConfidenceBreakdown:
    """
    Structural explainability object.
    No summarization. No natural language. Pure structural reasoning.
    """
    policy_id: str
    policy_version: str
    policy_hash: str
    final_score: float
    tier: str
    baseline_used: float
    rule_firings: List[RuleFiring] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "final_score": self.final_score,
            "tier": self.tier,
            "baseline_used": self.baseline_used,
            "rule_firings": [
                {
                    "rule_id": rf.rule_id,
                    "category": rf.category,
                    "input": rf.input_value,
                    "contribution": rf.contribution,
                    "fired": rf.fired
                }
                for rf in self.rule_firings
            ]
        }
