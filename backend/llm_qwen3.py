"""
Qwen3 LLM Engine (Facade)
Acts as a shim to route requests to the active LLM Backend
via the LLMFactory. Preserves API compatibility for the codebase.
"""

from typing import List, Dict, Optional
from backend.llm.factory import LLMFactory

class LLMQwen3:
    """Facade for LLM Client (Backwards Compatibility Shim)"""
    
    def __init__(self, agent_name: str = "orchestrator", model_name: Optional[str] = None):
        self.client = LLMFactory.create_client(agent_name, model_name)
        self.model_name = self.client.model_name if hasattr(self.client, 'model_name') else "unknown" 

    def stream_text(self, *args, **kwargs):
        """Delegate streaming to active backend"""
        return self.client.stream_text(*args, **kwargs)

    def generate_text(self, *args, **kwargs):
        """Delegate generation to active backend"""
        # Note: LlamaCppClient.generate_text might not take boundary_token yet, 
        # but propagating kwargs is safer for future-proofing.
        return self.client.generate_text(*args, **kwargs)

    def health_check(self):
        """Delegate health check"""
        return self.client.health_check()
