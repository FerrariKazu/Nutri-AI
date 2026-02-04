"""
Nutri Model Registry (Single Source of Truth)

Enforces strict model selection and prevents legacy/unregistered model usage.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ModelSpec:
    name: str
    provider: str  # "llama_cpp" | "ollama"
    context_length: int
    allowed_agents: List[str]

# CANONICAL MODEL REGISTRY
# All production models must be registered here.
MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "qwen3-4b": ModelSpec(
        name="qwen3-4b",
        provider="llama_cpp",
        context_length=32768,
        allowed_agents=[
            "orchestrator",
            "intent_agent",
            "synthesis_engine",
            "presentation_agent",
            "rag_agent",
            "refinement_agent",
            "verifier_agent",
            "variant_selector",
            "explainer_agent",
            "counterfactual_agent",
            "interactive_explainer"
        ]
    )
}

def get_model_spec(agent_name: str, model_name: Optional[str] = None) -> ModelSpec:
    """
    Retrieves the ModelSpec for a specific agent.
    If no model_name is provided, it defaults to the primary production model.
    
    Hard failures:
    1. Requested model not in registry.
    2. Agent not authorized to use the model.
    """
    # 🟢 Default to Qwen3-4B for production
    target_model = model_name or "qwen3-4b"
    
    if target_model not in MODEL_REGISTRY:
        error_msg = f"❌ [REGISTRY] Hard Failure: Model '{target_model}' not found in registry."
        logger.critical(error_msg)
        raise RuntimeError(error_msg)
    
    spec = MODEL_REGISTRY[target_model]
    
    if agent_name not in spec.allowed_agents:
        error_msg = f"❌ [REGISTRY] Hard Failure: Agent '{agent_name}' not authorized for model '{target_model}'."
        logger.critical(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info(f"✅ [REGISTRY] Agent '{agent_name}' matched with '{target_model}' ({spec.provider})")
    return spec

def list_registered_models() -> List[str]:
    return list(MODEL_REGISTRY.keys())
