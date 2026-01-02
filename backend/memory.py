"""
Nutri Session Memory System
Handles SQLite-backed persistence for user-assistant interaction history.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SessionMemoryStore:
    """Manages session-scoped memory for historical context injection."""
    
    def __init__(self, db_path: str = "nutri_sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT CHECK(role IN ('user', 'assistant')),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def create_session(self, session_id: str):
        """Ensures a session exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,))
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str):
        """Adds a message to the session history."""
        self.create_session(session_id)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            conn.commit()

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieves the most recent messages for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    def get_context_string(self, session_id: str, limit: int = 5) -> str:
        """Constructs a context string for Phase 1/2 injection."""
        history = self.get_history(session_id, limit)
        if not history:
            return ""
        
        context_parts = ["Previous Interaction Context:"]
        for msg in history:
            role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)

    def clear_session(self, session_id: str):
        """Deletes all messages for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()
