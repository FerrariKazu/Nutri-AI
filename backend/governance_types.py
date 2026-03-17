from enum import Enum

class GovernanceState(Enum):
    ALLOW_QUALITATIVE = "allow_qualitative"
    REQUIRE_QUANTITIES = "require_quantities"
    BLOCK_NUMERIC_OUTPUT = "block_numeric_output"
    BLOCK_MEDICAL = "block_medical"

class EscalationLevel(Enum):
    TIER_0 = 0  # Conversational / Lightweight
    TIER_1 = 1  # Standard Food / Generic Synthesis
    TIER_2 = 2  # Expert / Knowledge-Enriched (RAG allowed)
    TIER_3 = 3  # Scientific / Mechanistic (Tools + External APIs allowed)

# Phase 1.6 Hardening Flags
ALLOW_DEFAULT_SERVINGS = False
ALLOW_NUMERIC_HALLUCINATION = False
