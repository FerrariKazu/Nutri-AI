"""
Pantry management tools.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# In-memory pantry storage (would be database in production)
PANTRIES: Dict[str, List[str]] = {}


def pantry_tools(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manage user pantry items.
    
    Args:
        action: Action to perform ("add", "remove", "list", "clear")
        payload: Action-specific data
            - session_id: User session ID
            - items: List of items (for add/remove)
            
    Returns:
        Dict with action result
    """
    try:
        session_id = payload.get("session_id", "default")
        
        if action == "add":
            items = payload.get("items", [])
            if session_id not in PANTRIES:
                PANTRIES[session_id] = []
            
            PANTRIES[session_id].extend(items)
            PANTRIES[session_id] = list(set(PANTRIES[session_id]))  # Remove duplicates
            
            logger.info(f"Added {len(items)} items to pantry for session {session_id}")
            return {
                "success": True,
                "action": "add",
                "items": items,
                "pantry": PANTRIES[session_id],
            }
        
        elif action == "remove":
            items = payload.get("items", [])
            if session_id in PANTRIES:
                for item in items:
                    if item in PANTRIES[session_id]:
                        PANTRIES[session_id].remove(item)
            
            logger.info(f"Removed {len(items)} items from pantry")
            return {
                "success": True,
                "action": "remove",
                "items": items,
                "pantry": PANTRIES.get(session_id, []),
            }
        
        elif action == "list":
            pantry = PANTRIES.get(session_id, [])
            return {
                "success": True,
                "action": "list",
                "pantry": pantry,
                "count": len(pantry),
            }
        
        elif action == "clear":
            PANTRIES[session_id] = []
            logger.info(f"Cleared pantry for session {session_id}")
            return {
                "success": True,
                "action": "clear",
                "pantry": [],
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
            }
            
    except Exception as e:
        logger.error(f"Error in pantry_tools: {e}")
        return {
            "success": False,
            "error": str(e),
        }
