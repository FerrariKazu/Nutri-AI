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
            "orchestrator", "intent_agent", "intent_classifier", "synthesis_engine",
            "presentation_agent", "rag_agent", "refinement_agent", "verifier_agent",
            "variant_selector", "explainer_agent", "counterfactual_agent",
            "interactive_explainer", "claim_verifier", "claim_extractor"
        ]
    ),
    "deepseek-v3": ModelSpec(
        name="deepseek-ai/DeepSeek-V3",
        provider="together",
        context_length=64000,
        allowed_agents=[
            "orchestrator", "intent_agent", "intent_classifier", "synthesis_engine",
            "presentation_agent", "rag_agent", "refinement_agent", "verifier_agent",
            "variant_selector", "explainer_agent", "counterfactual_agent",
            "interactive_explainer", "claim_verifier", "claim_extractor"
        ]
    ),
    "llama-3.1-70b": ModelSpec(
        name="meta-llama/Meta-Llama-3.1-70B-Instruct",
        provider="together",
        context_length=32000,
        allowed_agents=[
            "orchestrator", "intent_agent", "intent_classifier", "synthesis_engine",
            "presentation_agent", "rag_agent", "refinement_agent", "verifier_agent",
            "variant_selector", "explainer_agent", "counterfactual_agent",
            "interactive_explainer", "claim_verifier", "claim_extractor"
        ]
    )
}

def get_model_spec(agent_name: str, model_name: Optional[str] = None) -> ModelSpec:
    """
    Retrieves the ModelSpec for a specific agent.
    Defaults to DeepSeek-V3 if no model_name provided.
    """
    # 🟢 Phase 3: Default to TogetherAI (DeepSeek-V3)
    target_model = model_name or "deepseek-v3"
    
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
