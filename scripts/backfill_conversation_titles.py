import sqlite3
import sys
import os
import logging

# Add project root to path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.title_generator import generate_title

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "nutri_sessions.db"

def backfill_titles():
    """
    Migration: Finds all conversations with 'New Conversation' title
    and generates a real title from the first message.
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Find sessions that need backfilling
        # We look for 'New Conversation' or NULL/Empty titles that have at least one message
        cursor.execute("""
            SELECT s.session_id, m.content 
            FROM sessions s
            JOIN messages m ON s.session_id = m.session_id
            WHERE (s.title IS NULL OR s.title = 'New Conversation' OR s.title = '')
            AND m.role = 'user'
            GROUP BY s.session_id
            HAVING MIN(m.id) -- Ensures we get the first message
        """)
        
        candidates = cursor.fetchall()
        logger.info(f"Found {len(candidates)} conversations needing title backfill.")

        updated_count = 0
        for session_id, first_msg in candidates:
            try:
                new_title = generate_title(first_msg)
                cursor.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (new_title, session_id))
                updated_count += 1
                if updated_count % 10 == 0:
                    logger.info(f"Progress: {updated_count}/{len(candidates)} updated.")
            except Exception as e:
                logger.error(f"Failed to generate title for session {session_id}: {e}")

        conn.commit()
        conn.close()
        logger.info(f"SUCCESS: Backfilled {updated_count} titles.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    backfill_titles()
