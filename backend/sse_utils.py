import json
import logging
from typing import Any

from backend.contracts.output_contract import ContractViolationError, validate_sse_content

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
    Formats a message into an SSE-compatible string.
    ENVELOPE: {"type": event, "content": data, "seq": ...}
    Strict Policy: For textual events (token, reasoning, message), content MUST be a raw string.
    """
    try:
        if event == "ping":
            return "event: ping\ndata: \n\n"
            
        # 1. Standardize Envelope
        # If data is already a dict, we assume it's the full item with seq and ts.
        payload = data if isinstance(data, dict) else {"type": event, "content": data}
        
        # 2. Identity Enforcement (User Request: stream_id is MANDATORY)
        stream_id = payload.get("stream_id")
        if event != "error_event": # Allow simple error_event without ID for fallback
            assert stream_id is not None, f"SSE {event} must include stream_id"
        
        # 3. Token Content Enforcement — Type-based only, no prefix heuristics
        content = payload.get("content", "")
        try:
            validate_sse_content(event, content)
        except ContractViolationError as cve:
            logger.critical(f"🚨 [TRANSPORT_VIOLATION] {cve}")
            raise

        # 5. Serialize THE ENTIRE ENVELOPE to JSON
        json_envelope = json.dumps(safe_json(payload))
        
        # [TRACE_AUDIT] Transport Validation
        try:
            # Inspect the final serialized data
            final_payload = json.loads(json_envelope)
            if event == "execution_trace":
                trace_data = final_payload.get("content")
                if trace_data:
                    scientific = trace_data.get("scientific_layer", {})
                    claims = scientific.get("claims", [])
                    keys = list(trace_data.keys())
                    logger.info(f"[TRACE_AUDIT] 🚀 SSE SENT: Event={event}, Claims={len(claims)}, Status={trace_data.get('epistemic_status')}")
                    logger.info(f"[TRACE_AUDIT] Keys: {keys}")
                    if "epistemic_status" not in keys:
                        logger.error(f"[TRACE_AUDIT] 🚨 MISSING: epistemic_status! Keys={keys}")
        except Exception as ae:
            logger.debug(f"[TRACE_AUDIT] Failed: {ae}")
            pass

        return f"event: {event}\ndata: {json_envelope}\n\n"
        
    except Exception as e:
        if isinstance(e, (RuntimeError, AssertionError)): raise 
        logger.error(f"SSE Formatting failure for event {event}: {e}")
        error_json = json.dumps({"type": "error", "content": str(e)})
        return f"event: error_event\ndata: {error_json}\n\n"
