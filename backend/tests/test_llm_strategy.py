"""Tests for Local-Only LLM Strategy — Phase 4"""

import pytest
from unittest.mock import MagicMock, patch
from backend.llm.factory import LLMFactory
from backend.llm.local_llama_client import LocalLlamaClient
from backend.retrieval.self_reflective_rag import evaluate_answer

class TestLLMStrategy:

    def test_factory_returns_local_client(self):
        """Verify factory returns LocalLlamaClient by default."""
        client = LLMFactory.create_client(agent_name="test_agent")
        assert isinstance(client, LocalLlamaClient)
        assert client.model_name == "qwen3-4b"

    def test_factory_caching(self):
        """Verify factory correctly caches clients."""
        client1 = LLMFactory.create_client(agent_name="agent1")
        client2 = LLMFactory.create_client(agent_name="agent2")
        assert client1 is client2  # Should be the same instance for local_llama:default

    @patch("backend.llm.local_llama_client.LocalLlamaClient.generate_text")
    def test_reflection_uses_factory_client(self, mock_generate):
        """Verify evaluate_answer uses local client from factory if none provided."""
        mock_generate.return_value = "DECISION: SUFFICIENT\nCONFIDENCE: 1.0"
        
        # We don't pass llm_client, so it should use the factory
        result = evaluate_answer(
            query="test",
            answer="test",
            context_chunks=[]
        )
        
        assert result["decision"] == "SUFFICIENT"
        mock_generate.assert_called_once()
