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
    
    def __init__(self, db_path: str = "nutri_sessions.db", decay_hours: int = 12):
        self.db_path = db_path
        self.decay_hours = decay_hours
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Sessions table with last_active
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    title TEXT,
                    response_mode TEXT DEFAULT 'conversation',
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Check if title column exists (migration for existing DBs)
            try:
                cursor.execute("SELECT title FROM sessions LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")

            # Messages table with conversation_id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    conversation_id TEXT,
                    role TEXT CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()
            
            # User preferences table (USER-SCOPED)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    skill_level TEXT,
                    equipment TEXT,
                    dietary_constraints TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Session context table (SESSION-SCOPED, ephemeral)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    current_dish TEXT,
                    key_ingredients TEXT,
                    technique TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Link sessions to users
            try:
                cursor.execute("SELECT user_id FROM sessions LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
            
            conn.commit()

    def check_and_reset_decay(self, session_id: str) -> bool:
        """
        Checks if session has decayed. If so, clears history and returns True.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT last_active_at FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            if not row or not row['last_active_at']:
                return False
                
            try:
                last_active = datetime.fromisoformat(row['last_active_at'])
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to parse timestamp for {session_id}: {row['last_active_at']}. Error: {e}")
                # If we can't parse it, treat it as "just now" so we don't crash or prematurely reset
                self._update_activity(session_id)
                return False
            delta = datetime.now() - last_active
            
            if delta.total_seconds() > (self.decay_hours * 3600):
                logger.info(f"⏳ Session {session_id} decayed (last active: {last_active}). Resetting...")
                self.clear_session(session_id)
                return True
        return False

    def _update_activity(self, session_id: str):
        """Updates last_active_at and ensures session exists."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check if exists
            cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO sessions (session_id, conversation_id, last_active_at) VALUES (?, ?, ?)",
                    (session_id, session_id, now)
                )
            else:
                cursor.execute(
                    "UPDATE sessions SET last_active_at = ? WHERE session_id = ?",
                    (now, session_id)
                )
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str):
        """Adds a message to the session history and updates activity."""
        self._update_activity(session_id)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Get conversation_id and title
            cursor.execute("SELECT conversation_id, title FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            conv_id = row[0] if row else session_id
            current_title = row[1] if row else None
            
            # Simple Deterministic Title Generation
            if not current_title and role == 'user':
                # First 7 words
                words = content.split()
                new_title = " ".join(words[:7])
                if len(words) > 7:
                    new_title += "..."
                
                # Update title
                cursor.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (new_title, session_id))

            cursor.execute(
                "INSERT INTO messages (session_id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
                (session_id, conv_id, role, content)
            )
            conn.commit()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns all sessions ordered by last_active DESC."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.session_id, s.title, s.last_active_at, m.content as last_message, s.response_mode
                FROM sessions s
                LEFT JOIN messages m ON m.id = (
                    SELECT id FROM messages 
                    WHERE session_id = s.session_id 
                    ORDER BY id DESC LIMIT 1
                )
                ORDER BY s.last_active_at DESC
            """)
            
            rows = cursor.fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "title": row["title"] or "New Conversation",
                    "last_active": row["last_active_at"],
                    "preview": (row["last_message"][:60] + "...") if row["last_message"] else "Empty chat",
                    "mode": row["response_mode"]
                }
                for row in rows
            ]

    def get_history(self, session_id: str, limit: int = 15) -> List[Dict[str, str]]:
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

    def get_messages(self, session_id: str, limit: int = 15) -> List[Dict[str, str]]:
        """Alias for get_history (used by NutriEngine)."""
        return self.get_history(session_id, limit)

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

    def get_conversation(self, session_id: str) -> Dict[str, Any]:
        """Returns the canonical state of a conversation."""
        self.check_and_reset_decay(session_id)
        history = self.get_history(session_id)
        mode = self.get_response_mode(session_id)
        
        return {
            "session_id": session_id,
            "messages": history,
            "current_mode": mode.value if hasattr(mode, 'value') else mode,
            "memory_scope": "session"
        }

    def clear_session(self, session_id: str):
        """Deletes all messages for a session and resets metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute(
                "UPDATE sessions SET conversation_id = ?, response_mode = 'conversation', last_active_at = ? WHERE session_id = ?",
                (session_id, datetime.now().isoformat(), session_id)
            )
            conn.commit()

    # --- Mode Tracking ---
    
    def get_response_mode(self, session_id: str):
        """Get the current response mode for session."""
        from backend.response_modes import ResponseMode
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT response_mode FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return ResponseMode.CONVERSATION
            
            mode_str = row['response_mode']
            try:
                return ResponseMode(mode_str)
            except ValueError:
                return ResponseMode.CONVERSATION

    def set_response_mode(self, session_id: str, mode):
        """Update the response mode for session."""
        from backend.response_modes import ResponseMode
        mode_val = mode.value if isinstance(mode, ResponseMode) else str(mode)
        
        self._update_activity(session_id)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET response_mode = ? WHERE session_id = ?",
                (mode_val, session_id)
            )
            conn.commit()
        logger.debug(f"Session {session_id}: Mode set to {mode_val}")

    # --- User Preferences (USER-SCOPED) ---
    
    def get_user_id(self, session_id: str) -> Optional[str]:
        """Get user_id associated with this session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return row['user_id'] if row and row['user_id'] else None
    
    def set_user_id(self, session_id: str, user_id: str):
        """Associate a user_id with this session."""
        self._update_activity(session_id)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET user_id = ? WHERE session_id = ?",
                (user_id, session_id)
            )
            conn.commit()
        logger.debug(f"Session {session_id}: Linked to user {user_id}")
    
    def get_preferences(self, user_id: str):
        """Retrieve persistent user preferences by user_id."""
        from backend.selective_memory import UserPreferences
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return UserPreferences()
            
            return UserPreferences(
                skill_level=row['skill_level'],
                equipment=json.loads(row['equipment']) if row['equipment'] else [],
                dietary_constraints=json.loads(row['dietary_constraints']) if row['dietary_constraints'] else []
            )
    
    def update_preferences(self, user_id: str, prefs: Dict[str, Any]):
        """Update user preferences (merge, don't replace)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get existing preferences
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Merge with existing
                current_skill = existing[1]  # skill_level
                current_equipment = json.loads(existing[2]) if existing[2] else []
                current_dietary = json.loads(existing[3]) if existing[3] else []
                
                new_skill = prefs.get('skill_level', current_skill)
                new_equipment = prefs.get('equipment', current_equipment)
                new_dietary = prefs.get('dietary_constraints', current_dietary)
                
                # Merge equipment and dietary (deduplicate)
                if isinstance(new_equipment, list) and current_equipment:
                    new_equipment = list(set(current_equipment + new_equipment))
                if isinstance(new_dietary, list) and current_dietary:
                    new_dietary = list(set(current_dietary + new_dietary))
                
                cursor.execute("""
                    UPDATE user_preferences 
                    SET skill_level = ?, equipment = ?, dietary_constraints = ?, updated_at = ?
                    WHERE user_id = ?
                """, (
                    new_skill,
                    json.dumps(new_equipment) if new_equipment else None,
                    json.dumps(new_dietary) if new_dietary else None,
                    datetime.now().isoformat(),
                    user_id
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO user_preferences (user_id, skill_level, equipment, dietary_constraints, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    prefs.get('skill_level'),
                    json.dumps(prefs.get('equipment', [])) if prefs.get('equipment') else None,
                    json.dumps(prefs.get('dietary_constraints', [])) if prefs.get('dietary_constraints') else None,
                    datetime.now().isoformat()
                ))
            
            conn.commit()
        logger.info(f"[MEMORY] Updated preferences for user {user_id}: {prefs}")
    
    # --- Session Context (SESSION-SCOPED) ---
    
    def get_context(self, session_id: str):
        """Retrieve ephemeral session context."""
        from backend.selective_memory import SessionContext
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_context WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            if not row:
                return SessionContext()
            
            return SessionContext(
                current_dish=row['current_dish'],
                key_ingredients=json.loads(row['key_ingredients']) if row['key_ingredients'] else [],
                technique=row['technique']
            )
    
    def update_context(self, session_id: str, context):
        """Replace session context (not merged). Guard: only overwrite if context is non-null."""
        if context is None:
            return  # Don't wipe valid context with empty extraction
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Upsert (replace if exists)
            cursor.execute("""
                INSERT OR REPLACE INTO session_context 
                (session_id, current_dish, key_ingredients, technique, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                context.current_dish,
                json.dumps(context.key_ingredients) if context.key_ingredients else None,
                context.technique,
                datetime.now().isoformat()
            ))
            
            conn.commit()
        logger.debug(f"[MEMORY] Updated context for session {session_id}")
