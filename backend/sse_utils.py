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
        
        # Handle Enums
        import enum
        if isinstance(obj, enum.Enum):
            return obj.value
            
        # Handle objects with explicit to_dict (often more tailored for JSON)
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return safe_json(obj.to_dict(), seen.copy(), depth + 1)
                
        # Handle Pydantic models (Pydantic v2 model_dump, v1 dict)
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return safe_json(obj.model_dump(), seen.copy(), depth + 1)
        if hasattr(obj, "dict") and callable(obj.dict):
            return safe_json(obj.dict(), seen.copy(), depth + 1)
                
        # Handle Dataclasses and other objects with __dict__
        if hasattr(obj, "__dict__"):
            if type(obj).__name__ in ('module', 'type', 'function'):
                return str(obj)
            return safe_json(vars(obj), seen.copy(), depth + 1)
                
    except Exception as e:
        logger.debug(f"safe_json recursion failed for {type(obj).__name__}: {e}")
            
    # Fallback to string representation
    return str(obj)

def format_sse_event(event: str, data: Any) -> str:
    """
    ZERO-JSON SSE CONTRACT:
    - ALL events are transmitted as raw text.
    - Textual events (token, reasoning, message) transmit raw markdown.
    - Structured events are flattened into descriptive text.
    - CRITICAL: Raises RuntimeError if '{' is detected in UI-facing textual events.
    """
    try:
        if event == "ping":
            return f"event: ping\ndata: \n\n"
            
        if event == "done":
            logger.debug(f"[SSE] Formatting done event with data: {data} (type: {type(data)})")
            # If data is a dict (new contract), JSON-encode it. 
            if isinstance(data, dict):
                res = f"event: done\ndata: {json.dumps(data)}\n\n"
                logger.debug(f"[SSE] Formatted JSON done: {res.strip()}")
                return res
            res = f"event: done\ndata: {data if data else '[DONE]'}\n\n"
            logger.debug(f"[SSE] Formatted legacy done: {res.strip()}")
            return res

        # 1. Flatten Data to String
        final_text = ""
        
        # JSON-Allowed Events: These events can transmit structured data
        json_allowed_events = ("status", "error_event", "intermediate")
        
        if event in json_allowed_events and isinstance(data, (dict, list)):
            final_text = json.dumps(data)
        elif isinstance(data, str):
            final_text = data
        elif isinstance(data, dict):
            # Fallback flattening for legacy or non-JSON events
            final_text = data.get("final_answer") or data.get("message") or \
                        data.get("recipe") or data.get("content") or \
                        data.get("status") or ""
        else:
            final_text = str(data)

        # Note: 'final' is now just a signal if used, or removed.
        textual_events = ("token", "reasoning", "message")
        if event in textual_events:
            stripped = final_text.strip()
            # 2. NUCLEAR SAFETY CHECK (Zero JSON Policy)
            # We crash the server if we detect JSON structures about to be sent to the user.
            # EXCEPTION: Allow the explicit [DONE] sentinel and System Errors.
            if stripped.startswith(("{", "[")) and stripped != "[DONE]" and not stripped.startswith("[System Error") and not stripped.startswith("[Connection Error"):
                logger.error(f"🚨 NUCLEAR SAFETY VIOLATION: JSON leakage detected in {event} event!")
                logger.error(f"   Payload Sample: {stripped[:100]}")
                raise RuntimeError(f"UI SAFETY VIOLATION: JSON detected in {event} stream.")

        # 3. Multi-line SSE formatting: Each line MUST start with "data: "
        lines = final_text.split('\n')
        data_block = "\n".join([f"data: {line}" for line in lines])
        
        return f"event: {event}\n{data_block}\n\n"
        
    except Exception as e:
        if isinstance(e, RuntimeError): raise # Reraise the safety crash
        logger.error(f"SSE Formatting failure for event {event}: {e}")
        # Final fail-safe: even errors must be plain text
        return f"event: error_event\ndata: FAILED: {str(e)}\n\n"
