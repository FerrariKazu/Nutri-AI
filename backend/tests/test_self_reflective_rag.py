"""Tests for Self-Reflective RAG — Phase 4"""

import time
import pytest
from unittest.mock import MagicMock, patch

from backend.retrieval.self_reflective_rag import (
    evaluate_answer,
    run_reflective_pipeline,
    _parse_reflection_response,
    MAX_TOTAL_LATENCY,
)


class TestReflectionParsing:

    def test_parse_sufficient(self):
        raw = "DECISION: SUFFICIENT\nCONFIDENCE: 0.95"
        decision, confidence = _parse_reflection_response(raw)
        assert decision == "SUFFICIENT"
        assert abs(confidence - 0.95) < 1e-3

    def test_parse_insufficient(self):
        raw = "DECISION: INSUFFICIENT_CONTEXT\nCONFIDENCE: 0.72"
        decision, confidence = _parse_reflection_response(raw)
        assert decision == "INSUFFICIENT_CONTEXT"
        assert abs(confidence - 0.72) < 1e-3

    def test_parse_hallucination(self):
        raw = "DECISION: HALLUCINATION_RISK\nCONFIDENCE: 0.88"
        decision, confidence = _parse_reflection_response(raw)
        assert decision == "HALLUCINATION_RISK"
        assert abs(confidence - 0.88) < 1e-3

    def test_parse_garbage_defaults(self):
        raw = "I think the answer is fine."
        decision, confidence = _parse_reflection_response(raw)
        assert decision == "SUFFICIENT"  # safe default
        assert confidence == 0.5


class TestEvaluateAnswer:

    def test_evaluate_sufficient(self):
        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = "DECISION: SUFFICIENT\nCONFIDENCE: 0.9"

        result = evaluate_answer(
            query="What is inosinate?",
            answer="Inosinate is an umami compound.",
            context_chunks=[{"text": "Inosinate produces umami taste."}],
            llm_client=mock_llm,
        )

        assert result["decision"] == "SUFFICIENT"
        assert result["confidence"] > 0.8

    def test_evaluate_insufficient(self):
        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = "DECISION: INSUFFICIENT_CONTEXT\nCONFIDENCE: 0.65"

        result = evaluate_answer(
            query="What is inosinate?",
            answer="Some answer",
            context_chunks=[{"text": "Short chunk."}],
            llm_client=mock_llm,
        )

        assert result["decision"] == "INSUFFICIENT_CONTEXT"


class TestReflectivePipeline:

    def test_sufficient_returns_original(self):
        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = "DECISION: SUFFICIENT\nCONFIDENCE: 0.95"

        result = run_reflective_pipeline(
            query="test",
            initial_answer="Original answer",
            context_chunks=[{"text": "Context."}],
            llm_client=mock_llm,
        )

        assert result["answer"] == "Original answer"
        assert result["decision"] == "SUFFICIENT"
        assert result["second_retrieval"] is False

    def test_insufficient_triggers_second_pass(self):
        mock_llm = MagicMock()
        mock_llm.generate_text.side_effect = [
            "DECISION: INSUFFICIENT_CONTEXT\nCONFIDENCE: 0.7",  # evaluation
            "Expanded answer with more context",  # regeneration
        ]

        mock_hybrid = MagicMock()
        mock_hybrid.search.return_value = {
            "results": [{"text": "Extra context chunk"}],
            "telemetry": {},
        }

        result = run_reflective_pipeline(
            query="test",
            initial_answer="Weak answer",
            context_chunks=[{"text": "Minimal context."}],
            hybrid_retriever=mock_hybrid,
            llm_client=mock_llm,
        )

        assert result["second_retrieval"] is True
        assert result["decision"] == "INSUFFICIENT_CONTEXT"
        mock_hybrid.search.assert_called_once()
        # Verify second pass params
        call_kwargs = mock_hybrid.search.call_args[1]
        assert call_kwargs["k_vector"] == 40
        assert call_kwargs["enable_taste_boost"] is False
        assert call_kwargs["enable_semantic_dedup"] is True

    def test_hallucination_triggers_strict_regen(self):
        mock_llm = MagicMock()
        mock_llm.generate_text.side_effect = [
            "DECISION: HALLUCINATION_RISK\nCONFIDENCE: 0.85",  # evaluation
            "Strict regenerated answer",  # strict regen
        ]

        result = run_reflective_pipeline(
            query="test",
            initial_answer="Hallucinated answer",
            context_chunks=[{"text": "Actual context."}],
            llm_client=mock_llm,
        )

        assert result["decision"] == "HALLUCINATION_RISK"
        assert result["answer"] == "Strict regenerated answer"
        assert result["second_retrieval"] is False

    def test_latency_guard_skips_reflection(self):
        mock_llm = MagicMock()

        # Simulate pipeline that already exceeded latency budget
        old_start = time.perf_counter() - MAX_TOTAL_LATENCY - 1.0

        result = run_reflective_pipeline(
            query="test",
            initial_answer="Original",
            context_chunks=[{"text": "Context."}],
            llm_client=mock_llm,
            pipeline_start_time=old_start,
        )

        assert result["answer"] == "Original"
        assert result["telemetry"].get("reflection_skipped") is True
        mock_llm.generate_text.assert_not_called()
