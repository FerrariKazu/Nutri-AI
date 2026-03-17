import re
import logging
from typing import Optional
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

def generate_title(first_message: str) -> str:
    """
    Generates a concise 4-6 word title for a conversation.
    Tries LLM first, falls back to deterministic extraction.
    """
    title = None
    
    # Option B: LLM Generation (Better)
    try:
        llm = LLMQwen3(agent_name="orchestrator")
        prompt = f"Generate a concise 4-6 word title for this conversation based on the first message: \"{first_message[:200]}\". Return ONLY the title text, no quotes, no punctuation."
        messages = [{"role": "user", "content": prompt}]
        
        # We use generate_text (non-streaming)
        title = llm.generate_text(messages)
        if title:
            title = title.strip().replace('"', '').replace("'", "")
            title = _clean_title(title)
            logger.info(f"[TITLE] LLM generated title: {title}")
    except Exception as e:
        logger.warning(f"[TITLE] LLM generation failed, falling back: {e}")

    # Option A: Deterministic Fallback
    if not title:
        title = _extract_fallback_title(first_message)
        logger.info(f"[TITLE] Fallback generated title: {title}")

    return title

def _clean_title(title: str) -> str:
    """Enforces: 4-6 words, Capitalized, No punctuation, No trailing period."""
    # Strip all punctuation
    title = re.sub(r'[^\w\s]', '', title)
    
    # Capitalize each word (standard title case) or just the whole thing? Spec says "Capitalized".
    # I'll capitalize the first letter of each word for a proper title look.
    words = [w.capitalize() for w in title.split()]
    
    # Enforce 4-6 words
    if len(words) < 4:
        # If too short, just keep them all
        pass
    elif len(words) > 6:
        words = words[:6]
        
    return " ".join(words)

def _extract_fallback_title(text: str) -> str:
    """Deterministic extraction logic (Option A)."""
    # Strip common starters
    text = re.sub(r'^(hi|hello|hey|nutri|can you|please|i want to|tell me about)\s+', '', text, flags=re.IGNORECASE)
    
    # Clean and split
    words = re.findall(r'\w+', text)
    
    # Take 4-6 words
    title_words = words[:6]
    if len(title_words) < 4 and len(words) >= 4:
        title_words = words[:4] # Should be covered by words[:6] anyway
        
    res = " ".join([w.capitalize() for w in title_words])
    return res if res else "New Conversation"
