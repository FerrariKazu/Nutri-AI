"""
Conversation memory store for session-based chat history.

Maintains a rolling window of the last 20 messages per session with
automatic cleanup of idle sessions after 1 hour.
"""

import time
from typing import Dict, List, Optional
from collections import deque
import threading
import logging

logger = logging.getLogger(__name__)

# Configuration
MAX_MESSAGES_PER_SESSION = 20
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

# In-memory storage
# Structure: {session_id: {"messages": deque, "last_access": timestamp}}
_sessions: Dict[str, Dict] = {}
_lock = threading.Lock()


def _cleanup_expired_sessions():
    """Remove sessions that haven't been accessed in SESSION_TIMEOUT_SECONDS."""
    current_time = time.time()
    expired = []
    
    with _lock:
        for session_id, session_data in _sessions.items():
            if current_time - session_data["last_access"] > SESSION_TIMEOUT_SECONDS:
                expired.append(session_id)
        
        for session_id in expired:
            del _sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")


def get_history(session_id: str) -> List[Dict[str, str]]:
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    _cleanup_expired_sessions()
    
    with _lock:
        if session_id not in _sessions:
            return []
        
        _sessions[session_id]["last_access"] = time.time()
        return list(_sessions[session_id]["messages"])


def append_user(session_id: str, message: str):
    """
    Add a user message to session history.
    
    Args:
        session_id: Unique session identifier
        message: User message content
    """
    _append_message(session_id, "user", message)


def append_assistant(session_id: str, message: str):
    """
    Add an assistant message to session history.
    
    Args:
        session_id: Unique session identifier
        message: Assistant message content
    """
    _append_message(session_id, "assistant", message)


def _append_message(session_id: str, role: str, content: str):
    """Internal helper to append a message to session history."""
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {
                "messages": deque(maxlen=MAX_MESSAGES_PER_SESSION),
                "last_access": time.time()
            }
        
        _sessions[session_id]["messages"].append({
            "role": role,
            "content": content
        })
        _sessions[session_id]["last_access"] = time.time()


def clear_history(session_id: str):
    """
    Clear all conversation history for a session.
    
    Args:
        session_id: Unique session identifier
    """
    with _lock:
        if session_id in _sessions:
            del _sessions[session_id]
            logger.info(f"Cleared history for session: {session_id}")


def format_history_for_prompt(session_id: str) -> str:
    """
    Format conversation history as a string for LLM prompt.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Formatted conversation history string
    """
    history = get_history(session_id)
    
    if not history:
        return "(No previous conversation)"
    
    formatted_lines = []
    for msg in history:
        role = msg["role"].upper()
        content = msg["content"]
        formatted_lines.append(f"{role}: {content}")
    
    return "\n".join(formatted_lines)


def get_session_count() -> int:
    """
    Get the number of active sessions.
    
    Returns:
        Number of active sessions
    """
    _cleanup_expired_sessions()
    with _lock:
        return len(_sessions)
