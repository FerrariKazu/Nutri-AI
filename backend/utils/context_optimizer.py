import logging

logger = logging.getLogger(__name__)

class ContextOptimizer:
    """
    Optimizes conversation context for the LLM by trimming,
    summarizing, or ranking relevant information to fit token limits.
    """
    
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        logger.info(f"🧠 ContextOptimizer initialized with {max_tokens} token limit")

    def optimize(self, messages: list) -> list:
        """
        Trims message history to stay within token limits.
        (Simple implementation: keep system message + last N messages)
        """
        if len(messages) <= 10:
            return messages
            
        system_message = [m for m in messages if m.get("role") == "system"]
        recent_messages = messages[-9:]
        
        optimized = system_message + recent_messages
        logger.debug(f"Optimized context: kept {len(optimized)}/{len(messages)} messages")
        return optimized
