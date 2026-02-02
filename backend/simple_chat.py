import re
import logging
from typing import Optional, Generator
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_CHAT = """
You are Nutri.

You are a friendly, lively, food-obsessed conversational assistant.
You specialize in food, nutrition, taste, flavor science, ingredients, cooking logic, and why food works.

IMPORTANT RULES:
- You are allowed to talk ABOUT food conceptually.
- You must NOT give recipes, step-by-step instructions, or nutrition breakdowns in this mode.
- No measurements, no cooking steps, no macros.

This mode is for:
- Greetings
- Small talk
- Explaining who you are
- Light discussion about food, flavor, or nutrition concepts

Tone:
- Warm
- Curious
- Human
- Claude-like
- Short but engaging

Examples:
- "Hi" -> Friendly greeting, mention your food focus
- "What are you for?" -> Explain your food/nutrition role
- "Why does chocolate taste bitter?" -> Conceptual explanation is OK
- "Make me a recipe" -> Politely deflect: "For recipes, just ask directly and I'll switch to full mode!"
"""

FOOD_KEYWORDS = [
    "make", "recipe", "cook", "eat", "diet", 
    "calories", "nutrition", "ingredients", 
    "dinner", "lunch", "breakfast", "snack",
    "meal", "food", "dish", "protein", "carbs"
]

CONVERSATIONAL_PATTERNS = [
    r"^\s*(hi|hello|hey|yo|sup|greetings)\b",
    r"\bwho\s+(are|r)\s+you\b",
    r"\bwhat\s+are\s+you\b",
    r"\bhow\s+are\s+you\b",
    r"\bare\s+you\s+real\b",
]

def is_fast_conversation(msg: str) -> bool:
    """
    Heuristic to determine if a message is a simple greeting/chat interaction
    that should bypass the heavy Nutri orchestrator.
    
    Returns True if safe to handle via FoodConversationAgent.
    """
    if not msg:
        return False
        
    # 1. Normalization (strip punctuation, lower case)
    clean_msg = re.sub(r"[^\w\s]", "", msg.lower()).strip()
    tokens = clean_msg.split()
    
    # 2. Negative Guardrail: Strict Food Exclusion
    # If any food keyword exists, force orchestrator (FALSE)
    if any(keyword in clean_msg for keyword in FOOD_KEYWORDS):
        return False
        
    # 3. Ultra-Fast Exit: Short greetings
    # "hi", "yo", "u there" -> <= 2 tokens usually
    if len(tokens) <= 2:
        return True
        
    # 4. Regex Patterns for specific queries
    # "who are you", "how are you doing"
    if any(re.search(p, clean_msg) for p in CONVERSATIONAL_PATTERNS):
        return True
        
    return False

class FoodConversationAgent:
    """
    Nutri's conversational agent for greetings and food concept discussions.
    Does NOT generate recipes, instructions, or nutrition breakdowns.
    Keeps Nutri's food-focused identity in all interactions.
    """
    
    def __init__(self, llm_client: LLMQwen3):
        self.llm = llm_client
        
    def generate_response(self, user_message: str) -> str:
        """
        Generates a fast conversational response.
        Explicitly disables tools/functions to prevent bias.
        """
        logger.info(f"⚡ Fast Gate: Handling message '{user_message}' via FoodConversationAgent")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_CHAT},
            {"role": "user", "content": user_message}
        ]
        
        # We use generate_text but conceptually we want to ensure
        # tools are NOT passed. The current LLMQwen3 wrapper might not 
        # expose a 'tools' arg directly, but commonly it's handled in the client.
        # Since LLMQwen3 wrappers call LlamaCppClient, and we want to be safe:
        # We rely on the fact that we are NOT passing any tool definitions here.
        
        try:
            return self.llm.generate_text(messages)
        except Exception as e:
            logger.error(f"FoodConversationAgent error: {e}")
            return "Hello! I'm Nutri. How can I help you with food today?"
