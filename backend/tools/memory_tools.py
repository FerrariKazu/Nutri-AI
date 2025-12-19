"""
Memory tools for storing user preferences and corrections.
"""

import logging
from typing import Dict, Any
from backend import conversation_store

logger = logging.getLogger(__name__)


class MemoryTools:
    """Tools for managing user memory and preferences."""
    
    @staticmethod
    def save(session_id: str, key: str, value: str) -> Dict[str, Any]:
        """
        Save a preference or correction to user memory.
        
        Args:
            session_id: User session ID
            key: Memory key (e.g., "dislikes", "preference", "correction")
            value: Value to store
            
        Returns:
            Dict with save status
        """
        try:
            # Store as a system message in conversation history
            message = f"[MEMORY] {key}: {value}"
            conversation_store.append_assistant(session_id, message)
            
            logger.info(f"Saved memory for session {session_id}: {key} = {value}")
            
            return {
                "success": True,
                "key": key,
                "value": value,
                "message": f"Remembered: {key}",
            }
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    @staticmethod
    def get(session_id: str, key: str) -> Dict[str, Any]:
        """
        Retrieve a stored preference.
        
        Args:
            session_id: User session ID
            key: Memory key to retrieve
            
        Returns:
            Dict with retrieved value or None
        """
        try:
            history = conversation_store.get_history(session_id)
            
            # Search for memory entries
            for msg in reversed(history):
                content = msg.get("content", "")
                if content.startswith(f"[MEMORY] {key}:"):
                    value = content.replace(f"[MEMORY] {key}:", "").strip()
                    return {
                        "success": True,
                        "key": key,
                        "value": value,
                    }
            
            return {
                "success": False,
                "message": f"No memory found for key: {key}",
            }
            
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Global instance
memory = MemoryTools()
