"""
Nutri Intelligence Schema Authority v1.2
Single Source of Truth (SSOT) for Intelligence Panel Contracts.
Ensures backend output perfectly matches frontend render requirements.
"""

from enum import Enum
from typing import List, Dict, Any

class Domain(str, Enum):
    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    STRUCTURAL = "structural"
    NUTRITIONAL = "nutritional"

class EvidenceLevel(str, Enum):
    HEURISTIC = "heuristic"
    THEORETICAL = "theoretical"
    EMPIRICAL = "empirical"
    CONSENSUS = "consensus"

class Origin(str, Enum):
    MODEL = "model"         # Pure LLM output
    EXTRACTED = "extracted" # Parser detected
    ENRICHED = "enriched"   # Registry backed

# ConfidenceScale DELETED — all confidence defaults now live exclusively
# in the policy artifact (backend/policies/default_policy_v1.py).
# Any code referencing ConfidenceScale must be redirected to the PolicyEngine.

# Minimum requirements for a claim to be considered "Renderable"
MIN_RENDER_REQUIREMENTS = {
    "graph": {"min_nodes": 1, "min_edges": 1},
    "perception": {"required_keys": ["label", "type"]},
    "confidence": {"required_keys": ["current", "tier", "policy_id", "policy_version"]}
}

ONTOLOGY_VERSION = "1.3"
REGISTRY_SOURCE_DEFAULT = "Derived from Nutri Core Ontology"
