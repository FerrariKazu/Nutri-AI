"""
Output Contract — Transport Layer Type Safety

Defines strict output types for agent → orchestrator → SSE boundaries.
Prevents JSON leakage, type confusion, and structured token crashes.

Rules:
    - Agents return AgentOutput with declared type
    - SSE "token" events MUST carry str content
    - SSE "data" events MUST carry dict content
    - No Any, no heuristics, no prefix detection
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Union, Dict, Any, List

logger = logging.getLogger(__name__)


class AgentOutputType(Enum):
    """Declares how agent output should be routed."""
    NARRATIVE = "narrative"      # str — streamable as token
    STRUCTURED = "structured"   # dict — must be rendered before streaming


class ContractViolationError(Exception):
    """Raised when a transport contract is violated."""
    pass


@dataclass
class AgentOutput:
    """
    Typed wrapper for all agent return values.
    
    Enforces explicit type declaration at the boundary.
    Prevents dict from leaking into token streams.
    """
    type: AgentOutputType
    content: Union[str, dict]
    agent_name: str = "unknown"

    def is_narrative(self) -> bool:
        """True if content is ready for direct token streaming."""
        return self.type == AgentOutputType.NARRATIVE and isinstance(self.content, str)

    def is_structured(self) -> bool:
        """True if content requires rendering before streaming."""
        return self.type == AgentOutputType.STRUCTURED and isinstance(self.content, dict)

    def __post_init__(self):
        """Validate type/content agreement on construction."""
        if self.type == AgentOutputType.NARRATIVE and not isinstance(self.content, str):
            raise ContractViolationError(
                f"AgentOutput NARRATIVE must have str content, got {type(self.content).__name__} "
                f"from agent '{self.agent_name}'"
            )
        if self.type == AgentOutputType.STRUCTURED and not isinstance(self.content, dict):
            raise ContractViolationError(
                f"AgentOutput STRUCTURED must have dict content, got {type(self.content).__name__} "
                f"from agent '{self.agent_name}'"
            )


# ── SSE Content Validation ──

TEXTUAL_EVENTS = frozenset({"token", "reasoning", "message"})
DATA_EVENTS = frozenset({"execution_trace", "status", "escalation", "done"})


def validate_sse_content(event_type: str, content: Any) -> None:
    """
    Validates content type for SSE emission.
    
    Type-based enforcement only. No string-prefix heuristics.
    
    Raises:
        ContractViolationError if content type violates the transport contract.
    """
    if event_type in TEXTUAL_EVENTS:
        if not isinstance(content, str):
            raise ContractViolationError(
                f"SSE '{event_type}' requires str content, got {type(content).__name__}: "
                f"{str(content)[:100]}"
            )
    elif event_type in DATA_EVENTS:
        if not isinstance(content, dict):
            raise ContractViolationError(
                f"SSE '{event_type}' requires dict content, got {type(content).__name__}: "
                f"{str(content)[:100]}"
            )


def render_structured_to_narrative(structured: dict) -> str:
    """
    Converts a structured mechanism/reasoning dict to human-readable text.
    
    This is the final safety net before SSE emission.
    If a structured output somehow reaches the presentation boundary,
    this renders it to text instead of crashing.
    """
    parts = []

    # Handle mechanistic 3-tier structure
    if "tier_1_surface" in structured:
        if structured.get("tier_1_surface"):
            parts.append(f"**What happens:** {structured['tier_1_surface']}")
        if structured.get("tier_2_process"):
            parts.append(f"**How it works:** {structured['tier_2_process']}")
        if structured.get("tier_3_molecular"):
            parts.append(f"**At the molecular level:** {structured['tier_3_molecular']}")

    # Handle causal chain
    if "causal_chain" in structured and structured["causal_chain"]:
        chain = structured["causal_chain"]
        if isinstance(chain, list):
            chain_str = " → ".join(
                step.get("cause", "?") if isinstance(step, dict) else str(step)
                for step in chain
            )
            parts.append(f"**Causal chain:** {chain_str}")

    # Handle generic mechanism dict
    if "mechanism" in structured:
        mech = structured["mechanism"]
        if isinstance(mech, str):
            parts.append(mech)
        elif isinstance(mech, dict):
            for k, v in mech.items():
                parts.append(f"**{k}:** {v}")

    # Fallback: just stringify keys
    if not parts:
        for key, value in structured.items():
            if isinstance(value, str) and value.strip():
                parts.append(f"**{key}:** {value}")

    return "\n".join(parts) if parts else str(structured)
