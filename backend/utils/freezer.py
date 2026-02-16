"""
Immutability Guard v1.0 — Physical Fact/Policy Partitioning.

Deep-freezes objects to prevent incidental or malicious mutation
by later computation layers (e.g., Policy Engine).
"""

from typing import Any, Dict, List, Tuple

def deep_freeze(obj: Any) -> Any:
    """
    Recursively freezes dicts and lists into immutable tuples/MappingProxy.
    In Python, for simplicity, we focus on making them read-only by wrapped access
    or converting them to types that do not support item assignment.
    
    For our structural partitioning, we convert:
    - Dict -> FrozenDict (custom read-only dict)
    - List -> Tuple
    """
    if isinstance(obj, dict):
        return FrozenDict({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(deep_freeze(i) for i in obj)
    return obj

class FrozenDict(dict):
    """
    A dictionary that does not allow modification.
    """
    def __setitem__(self, key, value):
        raise TypeError(f"Attempted to mutate a FROZEN factual artifact. Key: {key}")
    
    def __delitem__(self, key):
        raise TypeError(f"Attempted to delete from a FROZEN factual artifact. Key: {key}")
    
    def update(self, *args, **kwargs):
        raise TypeError("Attempted to update a FROZEN factual artifact.")
    
    def pop(self, *args, **kwargs):
        raise TypeError("Attempted to pop from a FROZEN factual artifact.")
    
    def clear(self):
        raise TypeError("Attempted to clear a FROZEN factual artifact.")

    def setdefault(self, *args, **kwargs):
        raise TypeError("Attempted to setdefault on a FROZEN factual artifact.")
