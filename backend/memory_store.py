"""
Session memory store with JSON persistence
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import fcntl
import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class MemoryStore:
    """Session-based conversation memory with persistence"""
    
    def __init__(self):
        self.sessions_dir = config.SESSIONS_DIR
        self.sessions_dir.mkdir(exist_ok=True)
        self.max_messages = config.MAX_MEMORY_MESSAGES
    
    def _get_session_file(self, session_id: str) -> Path:
        """Get path to session file"""
        # Sanitize session ID
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.sessions_dir / f"{safe_id}.json"
    
    def _load_session(self, session_id: str) -> Dict:
        """Load session data from file"""
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return {"messages": [], "created_at": datetime.now().isoformat()}
        
        try:
            with open(session_file, 'r') as f:
                # Use file lock for concurrent access
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return {"messages": [], "created_at": datetime.now().isoformat()}
    
    def _save_session(self, session_id: str, data: Dict):
        """Save session data to file (atomic write)"""
        session_file = self._get_session_file(session_id)
        temp_file = session_file.with_suffix('.tmp')
        
        try:
            # Write to temp file
            with open(temp_file, 'w') as f:
                # Use file lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomic rename
            temp_file.replace(session_file)
            
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
            if temp_file.exists():
                temp_file.unlink()
    
    def get_history(self, session_id: str, limit: int = None) -> List[Dict]:
        """Get conversation history for session"""
        limit = limit or self.max_messages
        
        data = self._load_session(session_id)
        messages = data.get("messages", [])
        
        # Return last N messages
        return messages[-limit:]
    
    def append_message(self, session_id: str, role: str, text: str):
        """Append message to session history"""
        data = self._load_session(session_id)
        
        message = {
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        
        data["messages"].append(message)
        
        # Keep only last N messages
        if len(data["messages"]) > self.max_messages * 2:  # Keep 2x for safety
            data["messages"] = data["messages"][-self.max_messages:]
        
        data["updated_at"] = datetime.now().isoformat()
        
        self._save_session(session_id, data)
        logger.debug(f"Appended {role} message to session {session_id}")
    
    def append_user(self, session_id: str, text: str):
        """Append user message"""
        self.append_message(session_id, "user", text)
    
    def append_assistant(self, session_id: str, text: str):
        """Append assistant message"""
        self.append_message(session_id, "assistant", text)
    
    def clear_session(self, session_id: str):
        """Clear session history"""
        session_file = self._get_session_file(session_id)
        
        if session_file.exists():
            try:
                session_file.unlink()
                logger.info(f"Cleared session {session_id}")
            except Exception as e:
                logger.error(f"Error clearing session {session_id}: {e}")
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(list(self.sessions_dir.glob("*.json")))
    
    def list_sessions(self) -> List[str]:
        """List all session IDs"""
        return [f.stem for f in self.sessions_dir.glob("*.json")]


# Global instance
memory_store = None

def get_memory_store() -> MemoryStore:
    """Get or create memory store instance"""
    global memory_store
    if memory_store is None:
        memory_store = MemoryStore()
    return memory_store
