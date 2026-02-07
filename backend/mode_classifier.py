"""
Mode Classifier with Stickiness and Explore-First Logic

Key features:
1. Mode stickiness - once escalated, stay until topic shifts
2. Explore vs Execute - diagnostic before procedural
3. Topic shift detection - reset mode on explicit shifts
"""

from backend.response_modes import ResponseMode


def is_topic_shift(message: str) -> bool:
    """Detect explicit topic changes or emotional resets."""
    msg_lower = message.lower()
    
    # Standard topic shifts
    topic_phrases = [
        "by the way", "new question", "unrelated", "different topic",
        "something else", "changing topics", "anyway", "never mind",
        "forget that", "actually", "on another note", "anyway"
    ]
    
    # Emotional resets (downgrade to conversation)
    emotional_resets = [
        "forget it", "doesn't matter", "whatever", "moving on",
        "drop it", "stop that", "different subject"
    ]
    
    return any(phrase in msg_lower for phrase in topic_phrases + emotional_resets)


def asks_for_nutrition(message: str) -> bool:
    """Detect explicit request for numeric nutrition analysis."""
    msg_lower = message.lower()
    numeric_triggers = [
        "calories", "macros", "how many grams", "kcal", 
        "protein count", "carb count", "fat content", "nutrition facts",
        "exact nutrition", "how many mg", "scoville"
    ]
    return any(phrase in msg_lower for phrase in numeric_triggers)


def asks_for_health(message: str) -> bool:
    """Detect qualitative health/wellness questions."""
    msg_lower = message.lower()
    qualitative_triggers = [
        "healthy", "low carb", "high protein", "light meal",
        "nutritious", "good for me", "unhealthy", "balanced"
    ]
    return any(phrase in msg_lower for phrase in qualitative_triggers)


def is_causal_intent(message: str) -> bool:
    """
    Detect causal/mechanistic questions requiring MoA reasoning.
    These questions demand causal explanation, not mere correlation.
    """
    msg_lower = message.lower()
    causal_triggers = [
        "why does", "why do", "why is", "how does", "how do",
        "what makes", "what causes", "effect of", "impact of",
        "leads to", "results in", "helps with", "reduces",
        "improves", "benefits", "mechanism", "science behind"
    ]
    return any(phrase in msg_lower for phrase in causal_triggers)


def asks_for_steps(message: str) -> bool:
    """Detect explicit request for procedural output."""
    return any(
        phrase in message.lower()
        for phrase in [
            "how do i", "give me steps", "walk me through",
            "recipe for", "make me", "step by step", "can you make",
            "show me how", "teach me to", "instructions for"
        ]
    )


import logging

logger = logging.getLogger(__name__)

# ... (helper functions remain same) ...

def classify_response_mode(
    message: str,
    intent=None,
    previous_mode: ResponseMode = ResponseMode.CONVERSATION
) -> ResponseMode:
    """
    Determine response mode with stickiness, logging, and soft decay.
    """
    msg_lower = message.lower()
    
    # helper for logging
    def log_decision(decision: str, reason: str):
        logger.info(f"🧠 Mode Transition: {previous_mode.value} -> {decision} | Reason: {reason}")

    # --- SOFT DECAY CHECKS ---
    # If the message is very short/generic, we might drift back to conversation
    # unless we are in the middle of a procedure.
    is_low_relevance = len(message.split()) < 3 and not any(
        x in msg_lower for x in ["yes", "no", "next", "continue", "more", "ok"]
    )

    # --- MODE STICKINESS ---
    
    # NUTRITION_ANALYSIS: Sticky until shift
    if previous_mode == ResponseMode.NUTRITION_ANALYSIS:
        if is_topic_shift(message):
            log_decision("conversation", "Topic shift detected")
            return ResponseMode.CONVERSATION
        if is_low_relevance:
             # Decay if user disengages
            log_decision("conversation", "Soft confidence decay (low relevance input)")
            return ResponseMode.CONVERSATION
            
        log_decision("nutrition_analysis", "Sticky maintenance")
        return ResponseMode.NUTRITION_ANALYSIS

    # PROCEDURAL: Highly sticky, usually takes explicit exit to leave
    if previous_mode == ResponseMode.PROCEDURAL:
        if is_topic_shift(message):
            log_decision("conversation", "Topic shift detected")
            return ResponseMode.CONVERSATION
        if asks_for_nutrition(message):
            log_decision("nutrition_analysis", "Explicit nutrition request")
            return ResponseMode.NUTRITION_ANALYSIS
        
        log_decision("procedural", "Sticky maintenance")
        return ResponseMode.PROCEDURAL

    # DIAGNOSTIC: Moderate stickiness
    if previous_mode == ResponseMode.DIAGNOSTIC:
        if is_topic_shift(message):
            log_decision("conversation", "Topic shift detected")
            return ResponseMode.CONVERSATION
            
        if is_low_relevance:
            # Soft decay: If user just says "cool" after a diagnostic, better to resume chat
            log_decision("conversation", "Soft confidence decay (low relevance input)")
            return ResponseMode.CONVERSATION
            
        if asks_for_nutrition(message):
            log_decision("nutrition_analysis", "Explicit nutrition request")
            return ResponseMode.NUTRITION_ANALYSIS
            
        if asks_for_steps(message):
            log_decision("procedural", "Explicit step request")
            return ResponseMode.PROCEDURAL
            
        # Check if we should maintain diagnostic mode (is input still problem-solving?)
        # If no diagnostic markers and no obvious follow-up, drift.
        # But we assume maintenance for continuity unless it looks like a drift.
        log_decision("diagnostic", "Sticky maintenance")
        return ResponseMode.DIAGNOSTIC

    # --- FRESH CLASSIFICATION (from CONVERSATION) ---

    if asks_for_nutrition(message):
        log_decision("nutrition_analysis", "Fresh triggers: Nutrition")
        return ResponseMode.NUTRITION_ANALYSIS

    if asks_for_steps(message):
        log_decision("procedural", "Fresh triggers: Steps")
        return ResponseMode.PROCEDURAL

    diagnostic_phrases = [
        "why is", "what went wrong", "too dry", "too salty", "too sweet",
        "didn't rise", "turned out", "not right", "problem with", "issue with",
        "my cake", "my bread", "my soup", "my dish", "overcooked", "undercooked",
        "burned", "didn't work", "failed", "ruined", "disaster",
        "grainy", "lumpy", "watery", "soupy", "bland", "rubbery", "tough",
        "greasy", "oily", "flat", "dense", "gummy", "bitter", "sour",
        "raw", "mushy", "soggy", "broken", "curdled", "split"
    ]
    if any(phrase in msg_lower for phrase in diagnostic_phrases):
        log_decision("diagnostic", "Fresh triggers: Diagnostic phrases")
        return ResponseMode.DIAGNOSTIC
    
    if asks_for_health(message):
        log_decision("diagnostic", "Fresh triggers: Health (mapped to Diagnostic)")
        return ResponseMode.DIAGNOSTIC

    if intent and hasattr(intent, 'goal'):
        if intent.goal == "optimize_nutrition":
             if asks_for_nutrition(message):
                 log_decision("nutrition_analysis", "Intent: Optimize + Numeric request")
                 return ResponseMode.NUTRITION_ANALYSIS
             log_decision("diagnostic", "Intent: Optimize (Conceptual)")
             return ResponseMode.DIAGNOSTIC

        if intent.goal in {"modify_recipe", "troubleshoot", "diagnose"}:
            if asks_for_steps(message):
                log_decision("procedural", "Intent: Modify/Troubleshoot + Steps")
                return ResponseMode.PROCEDURAL
            log_decision("diagnostic", "Intent: Modify/Troubleshoot")
            return ResponseMode.DIAGNOSTIC

    log_decision("conversation", "Default")
    return ResponseMode.CONVERSATION
