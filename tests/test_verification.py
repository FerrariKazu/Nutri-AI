"""
Tests for Phase 4: Chemistry Claim Verification.

Covers:
- Claim extraction
- Claim verification with scientific rules
- Report generation
- Pipeline integration
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.verification.claim_verifier import (
    ClaimVerifier, ClaimExtractor, ClaimStatus, RecommendedAction
)

# Configure logging
logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    with patch('backend.verification.claim_verifier.LLMQwen3') as MockLLM:
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_retriever():
    """Mock retriever."""
    mock = MagicMock()
    # Default behavior: return some dummy doc
    from backend.food_synthesis import RetrievedDocument
    mock.retrieve.return_value = [
        RetrievedDocument(text="Scientific context...", score=0.9, doc_type="chemistry", source="test")
    ]
    return mock


class TestClaimExtraction:
    """Tests for ClaimExtractor."""

    def test_extract_claims(self, mock_llm):
        """Test basic claim extraction."""
        mock_llm.generate_text.return_value = '["Starch gelatinizes at 65C", "Proteins denature at 60C"]'
        
        extractor = ClaimExtractor()
        claims = extractor.extract("Text with claims")
        
        assert len(claims) == 2
        assert "Starch gelatinizes at 65C" in claims

    def test_empty_text(self, mock_llm):
        """Test empty text handling."""
        extractor = ClaimExtractor()
        claims = extractor.extract("")
        assert claims == []


class TestClaimVerificationRules:
    """Tests for mandatory scientific verification rules."""

    def test_thermal_relevance_rule(self, mock_llm, mock_retriever):
        """Enzymes > 60C should be IRRELEVANT."""
        verifier = ClaimVerifier()
        
        # Mock extractor to return the specific claim
        verifier.extractor.extract = MagicMock(return_value=["Lipase is active at 100C"])
        
        # Mock verifier LLM response to simulate rule application
        mock_llm.generate_text.return_value = '''{
            "status": "irrelevant",
            "confidence": "high",
            "justification": "Enzymes denature above 60C",
            "recommended_action": "remove"
        }'''
        
        report = verifier.verify("Recipe text", mock_retriever)
        
        assert len(report.flagged_claims) == 1
        claim = report.flagged_claims[0]
        assert claim.status == ClaimStatus.IRRELEVANT
        assert claim.recommended_action == RecommendedAction.REMOVE

    def test_supported_claim(self, mock_llm, mock_retriever):
        """Correct starch gelatinization should be SUPPORTED."""
        verifier = ClaimVerifier()
        verifier.extractor.extract = MagicMock(return_value=["Starch gelatinizes at 65C"])
        
        mock_llm.generate_text.return_value = '''{
            "status": "supported",
            "confidence": "high",
            "justification": "Matches retrieved context",
            "recommended_action": "keep"
        }'''
        
        report = verifier.verify("Recipe text", mock_retriever)
        
        assert len(report.verified_claims) == 1
        assert report.verified_claims[0].status == ClaimStatus.SUPPORTED

    def test_overconfident_mineral_claim(self, mock_llm, mock_retriever):
        """Precise mineral claims without source should be UNCERTAIN."""
        verifier = ClaimVerifier()
        verifier.extractor.extract = MagicMock(return_value=["Contains exactly 5mg iron"])
        
        mock_llm.generate_text.return_value = '''{
            "status": "uncertain",
            "confidence": "low",
            "justification": "Precision implies measurement not estimation",
            "recommended_action": "soften"
        }'''
        
        report = verifier.verify("Recipe text", mock_retriever)
        
        # Uncertain + low confidence should be flagged
        assert len(report.flagged_claims) == 1
        assert report.flagged_claims[0].status == ClaimStatus.UNCERTAIN

    def test_unsupported_flavor_chem(self, mock_llm, mock_retriever):
        """Unsupported flavor chemistry should be FLAGGED/UNSUPPORTED."""
        verifier = ClaimVerifier()
        verifier.extractor.extract = MagicMock(return_value=["Quantum spin affects flavor"])
        
        mock_llm.generate_text.return_value = '''{
            "status": "unsupported",
            "confidence": "high",
            "justification": "No scientific basis",
            "recommended_action": "remove"
        }'''
        
        report = verifier.verify("Recipe text", mock_retriever)
        
        assert len(report.flagged_claims) == 1
        assert report.flagged_claims[0].status == ClaimStatus.UNSUPPORTED


class TestPipelineIntegration:
    """Test integration with NutriPipeline."""

    def test_pipeline_verify_method(self, mock_llm):
        """Verify pipeline has verify method and calls verifier."""
        from backend.food_synthesis import NutriPipeline, SynthesisResult
        
        # Mock dependencies
        with patch('backend.food_synthesis.FoodSynthesisRetriever'):
            with patch('backend.food_synthesis.FoodSynthesisEngine'):
                with patch('backend.food_synthesis.ClaimVerifier') as MockVerifier:
                    pipeline = NutriPipeline(use_phase2=False)
                    
                    # Create dummy result
                    result = SynthesisResult(
                        recipe="Recipe",
                        retrieved_documents=[],
                        intent=None,
                        phase=1
                    )
                    
                    # Call verify
                    pipeline.verify(result)
                    
                    # Check verifier was called
                    assert pipeline._verifier.verify.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
