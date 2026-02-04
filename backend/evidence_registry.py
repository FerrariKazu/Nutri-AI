from enum import Enum
from typing import List

class SourcePriority(Enum):
    PUBCHEM = 1
    USDA = 2
    PEER_REVIEWED_RAG = 3
    HEURISTIC = 4

SOURCE_PRIORITY = {
    "pubchem": SourcePriority.PUBCHEM,
    "usda": SourcePriority.USDA,
    "peer_reviewed_rag": SourcePriority.PEER_REVIEWED_RAG,
    "heuristic": SourcePriority.HEURISTIC
}

def is_higher_priority(source_a: str, source_b: str) -> bool:
    """
    Returns True if source_a has higher priority than source_b.
    (Lower enum value means higher priority)
    """
    val_a = SOURCE_PRIORITY.get(source_a, SourcePriority.HEURISTIC).value
    val_b = SOURCE_PRIORITY.get(source_b, SourcePriority.HEURISTIC).value
    return val_a < val_b

def get_priority_level(source: str) -> int:
    return SOURCE_PRIORITY.get(source, SourcePriority.HEURISTIC).value
