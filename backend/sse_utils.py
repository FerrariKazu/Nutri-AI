import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def safe_json(obj: Any, seen: set = None, depth: int = 0) -> Any:
    """
    Guarantees JSON-safe output for ALL internal objects.
    Recursively handles dictionaries, lists, dataclasses, and pydantic models.
    Prevents infinite recursion and limits depth.
    """
    if seen is None:
        seen = set()
    
    if obj is None:
        return None
    
    # Basic types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Avoid infinite recursion and too much depth
    obj_id = id(obj)
    if obj_id in seen or depth > 10:
        return f"[Circular or Too Deep: {type(obj).__name__}]"
    
    seen.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            return {str(k): safe_json(v, seen.copy(), depth + 1) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [safe_json(v, seen.copy(), depth + 1) for v in obj]
        
        # Handle Pydantic models (Pydantic v2 model_dump, v1 dict)
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return safe_json(obj.model_dump(), seen.copy(), depth + 1)
        if hasattr(obj, "dict") and callable(obj.dict):
            # Special case: don't call .dict() if it's not a Pydantic-like thing?
            # Usually safe for Pydantic.
            return safe_json(obj.dict(), seen.copy(), depth + 1)
                
        # Handle Dataclasses and other objects with __dict__
        if hasattr(obj, "__dict__"):
            # Avoid vars(module) or vars(type)
            if type(obj).__name__ in ('module', 'type', 'function'):
                return str(obj)
            return safe_json(vars(obj), seen.copy(), depth + 1)
                
        # Handle objects with explicit to_dict
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return safe_json(obj.to_dict(), seen.copy(), depth + 1)
                
    except Exception:
        pass # Fallback below
            
    # Fallback to string representation
    return str(obj)

def format_sse_event(event: str, data: Any) -> str:
    """
    Wraps data in an SSE event with a JSON-safe payload.
    """
    try:
        # Pings might have empty data
        if event == "ping":
            return f"event: ping\ndata: {{}}\n\n"
            
        safe_data = safe_json(data)
        json_data = json.dumps(safe_data)
        return f"event: {event}\ndata: {json_data}\n\n"
    except Exception as e:
        logger.error(f"SSE Formatting failure for event {event}: {e}")
        error_payload = json.dumps({"error": "Serialization failed", "event": event})
        return f"event: error_event\ndata: {error_payload}\n\n"
