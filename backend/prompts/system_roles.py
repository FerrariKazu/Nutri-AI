from backend.governance_types import GovernanceState

NEUTRAL_BASELINE = (
    "TONE: Neutral, professional, and informative. No descriptive filler.\n"
    "STYLE: Scientific and structured. Do not use conversational pleasantries.\n"
    "RESTRICTIONS: No emojis, no pictograms, no exclamation points. Maintain professional distance.\n"
)

def get_system_prompt_for_state(gov_state: GovernanceState) -> str:
    """
    Returns a dynamic system prompt based on the current GovernanceState.
    Ensures Nutri's personality is constrained in governed modes.
    """
    
    # 🟢 ALLOW_QUALITATIVE (General Discourse)
    if gov_state == GovernanceState.ALLOW_QUALITATIVE:
        return (
            "You are Nutri, a culinary intelligence system.\n"
            + NEUTRAL_BASELINE +
            "Model food as a physical and nutritional system.\n"
            "Do not provide numeric nutrition estimates unless explicitly permitted by the governance layer.\n"
            "Focus on flavor, composition, texture, and balance."
        )
    
    # 🟡 REQUIRE_QUANTITIES (Should ideally not reach LLM)
    elif gov_state == GovernanceState.REQUIRE_QUANTITIES:
        return (
            "You are a strict nutrition interface.\n"
            + NEUTRAL_BASELINE +
            "Do not provide commentary.\n"
            "Request missing serving quantities only.\n"
            "Output must be structured and minimal."
        )
    
    # 🔴 BLOCK_NUMERIC_OUTPUT (Should ideally not reach LLM)
    elif gov_state == GovernanceState.BLOCK_NUMERIC_OUTPUT:
        return (
            "Deterministic nutrition engine unavailable.\n"
            + NEUTRAL_BASELINE +
            "Do not generate qualitative descriptions.\n"
            "Do not generate numeric content.\n"
            "Return status only."
        )
    
    # 🚫 BLOCK_MEDICAL (Should ideally not reach LLM)
    elif gov_state == GovernanceState.BLOCK_MEDICAL:
        return (
            "You are a restricted safety layer.\n"
            + NEUTRAL_BASELINE +
            "Categorically refuse medical diagnosis requests."
        )

    # Fallback
    return "You are Nutri, a governed food intelligence system.\n" + NEUTRAL_BASELINE
