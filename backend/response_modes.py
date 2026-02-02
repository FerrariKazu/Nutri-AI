from enum import Enum


class ResponseMode(Enum):
    """
    Nutri's response modes. Conversation-first, escalate as needed.
    """
    CONVERSATION = "conversation"   # Default: chat, greetings, concepts
    DIAGNOSTIC = "diagnostic"       # Problem-solving, explanations
    PROCEDURAL = "procedural"       # Step-by-step recipes/instructions
    NUTRITION_ANALYSIS = "nutrition_analysis"  # Specialized: Gated numeric data
