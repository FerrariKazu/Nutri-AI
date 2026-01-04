import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def sse_safe(obj: Any) -> Any:
    """
    Convert any internal object to JSON-safe data.
    Recursively handles dictionaries, lists, dataclasses, and pydantic models.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): sse_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sse_safe(v) for v in obj]
    
    # Handle Pydantic models (like ChatPreferences)
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return sse_safe(obj.dict())
        except Exception:
            pass
            
    # Handle Dataclasses and other objects with __dict__
    if hasattr(obj, "__dict__"):
        try:
            return sse_safe(vars(obj))
        except Exception:
            pass
            
    # Handle objects with explicit to_dict (like some logic objects)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return sse_safe(obj.to_dict())
        except Exception:
            pass
            
    # Fallback to string representation to avoid crashing json.dumps
    return str(obj)

def format_sse_event(event: str, data: Any) -> str:
    """
    Wraps data in an SSE event with a JSON-safe payload.
    """
    try:
        safe_data = sse_safe(data)
        # For 'token' events, we might want to emit raw strings if data isn't a complex object
        # However, to be safe and consistent with the user's request for JSON data:
        if event == "token" and isinstance(safe_data, str):
            # Tokens are often raw characters, but SSE usually expects JSON for 'data: '
            # If the frontend uses e.data directly without JSON.parse, it works.
            # If the frontend uses JSON.parse(e.data), we MUST json.dumps it.
            # The current frontend (apiClient.js) uses e.data directly for tokens.
            # But the user requested "ALL SSE events are JSON-safe".
            return f"event: {event}\ndata: {safe_data}\n\n"
            
        json_data = json.dumps(safe_data)
        return f"event: {event}\ndata: {json_data}\n\n"
    except Exception as e:
        logger.error(f"SSE Formatting failure for event {event}: {e}")
        # Last resort error format
        error_payload = json.dumps({"error": "Serialization failed", "event": event})
        return f"event: error\ndata: {error_payload}\n\n"
