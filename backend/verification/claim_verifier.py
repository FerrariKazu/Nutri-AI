"""
Nutri Phase 4: Chemistry Claim Verification Engine

Verifies scientific claims in synthesized recipes against retrieved knowledge.
Acts as a gatekeeper to ensure no hallucinated chemistry or physically impossible claims.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add project root to path for direct execution
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class ClaimStatus(str, Enum):
    """Status of a verified claim."""
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"
    UNSUPPORTED = "unsupported"
    INCORRECT = "incorrect"
    IRRELEVANT = "irrelevant"


class RecommendedAction(str, Enum):
    """Action recommended for a claim."""
    KEEP = "keep"
    SOFTEN = "soften"
    REPHRASE = "rephrase"
    REMOVE = "remove"


@dataclass
class VerifiedClaim:
    """A single scientific claim with verification status."""
    claim: str
    status: ClaimStatus
    confidence: Literal["high", "medium", "low"]
    justification: str
    recommended_action: RecommendedAction
    original_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status.value,
            "confidence": self.confidence,
            "justification": self.justification,
            "recommended_action": self.recommended_action.value,
            "original_text": self.original_text
        }


@dataclass
class VerificationReport:
    """Report containing all verified claims and overall assessment."""
    verified_claims: List[VerifiedClaim]
    flagged_claims: List[VerifiedClaim]
    overall_confidence: Literal["high", "medium", "low"]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "flagged_claims": [c.to_dict() for c in self.flagged_claims],
            "overall_confidence": self.overall_confidence,
            "warnings": self.warnings
        }


# =============================================================================
# CLAIM EXTRACTOR
# =============================================================================

EXTRACTOR_PROMPT = """You are a scientific claim extractor for a food chemistry system.

Your task is to extract ATOMIC scientific claims from the provided text.

Extract claims related to:
- Chemical reactions (e.g., Maillard, caramelization)
- Physical changes (e.g., gelatinization, denaturation)
- Nutritional values (e.g., protein content, mineral presence)
- Functional roles of ingredients

Rules:
- Extract ONLY explicit claims.
- Split compound sentences into atomic claims.
- Ignore generic cooking instructions ("chop the onions").
- Ignore subjective flavor descriptions ("tastes good").

Return valid JSON list of strings:
[
  "Rice starch gelatinizes at 65–70°C",
  "Maillard reactions occur at 140–160°C"
]"""


class ClaimExtractor:
    """Extracts atomic scientific claims from text."""

    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = LLMQwen3(model_name=model_name)
        logger.info("ClaimExtractor initialized")

    def extract(self, text: str) -> List[str]:
        """Extract scientific claims from text."""
        if not text or not text.strip():
            return []

        messages = [
            {"role": "system", "content": EXTRACTOR_PROMPT},
            {"role": "user", "content": f"Extract scientific claims from:\n\n{text}"}
        ]

        try:
            response = self.llm.generate_text(
                messages=messages,
                max_new_tokens=1024,
                temperature=0.1
            )
            return self._parse_json(response)
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    def _parse_json(self, response: str) -> List[str]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return []


# =============================================================================
# CLAIM VERIFIER
# =============================================================================

VERIFIER_PROMPT = """You are a food chemistry QA specialist. Verify the following claim against the provided scientific context.

Claim: "{claim}"

Context:
{context}

You must evaluate the claim based on these STRICT rules:

1. **Thermal Relevance**: If it involves enzymes (e.g., lipase, protease) and cooking >60°C, it is IRRELEVANT (enzymes denature).
2. **Causality**: If the mechanism doesn't affect texture, flavor, or nutrition, it is WEAK or IRRELEVANT.
3. **In-Vitro Rule**: Theoretical or in-vitro mechanisms must be labeled UNCERTAIN.
4. **Scope**: Nutrition claims must be ESTIMATES. Precise claims without source are UNCERTAIN.

Classify the claim:
- **supported**: Explicitly backed by context or basic food science facts.
- **uncertain**: Plausible but not strictly proven by context or theoretical.
- **unsupported**: Contradicted by context or no evidence found.
- **incorrect**: Factually wrong (e.g., widely known physics violation).
- **irrelevant**: Technically true but doesn't matter (e.g., denatured enzymes).

Return JSON:
{{
  "status": "supported | uncertain | unsupported | incorrect | irrelevant",
  "confidence": "high | medium | low",
  "justification": "Scientific explanation of the verdict",
  "recommended_action": "keep | soften | rephrase | remove"
}}"""


class ClaimVerifier:
    """Verifies claims against scientific knowledge."""

    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = LLMQwen3(model_name=model_name)
        self.extractor = ClaimExtractor(model_name=model_name)
        logger.info("ClaimVerifier initialized")

    def verify(self, text: str, retriever: Any) -> VerificationReport:
        """
        Verify all claims in the text.
        
        Args:
            text: content to verify (recipe + explanation)
            retriever: FoodSynthesisRetriever instance
        """
        claims = self.extractor.extract(text)
        if not claims:
            return VerificationReport([], [], "high", ["No scientific claims found to verify."])

        verified_claims = []
        flagged_claims = []
        
        for claim_text in claims:
            # Retrieve evidence
            docs = retriever.retrieve(claim_text, top_k=3)
            context = "\n".join([d.text for d in docs])
            
            # Verify
            verification = self._verify_single_claim(claim_text, context)
            
            if verification.status in [ClaimStatus.INCORRECT, ClaimStatus.UNSUPPORTED, ClaimStatus.IRRELEVANT]:
                flagged_claims.append(verification)
            elif verification.status == ClaimStatus.UNCERTAIN and verification.confidence == "low":
                flagged_claims.append(verification)
            else:
                verified_claims.append(verification)

        # Determine overall confidence
        overall_confidence = "high"
        if any(c.status == ClaimStatus.INCORRECT for c in flagged_claims):
            overall_confidence = "low"
        elif len(flagged_claims) > len(verified_claims) or any(c.status == ClaimStatus.UNSUPPORTED for c in flagged_claims):
            overall_confidence = "medium"

        warnings = [f"Flagged: {c.claim} ({c.status.value})" for c in flagged_claims]

        return VerificationReport(
            verified_claims=verified_claims,
            flagged_claims=flagged_claims,
            overall_confidence=overall_confidence,
            warnings=warnings
        )

    def _verify_single_claim(self, claim: str, context: str) -> VerifiedClaim:
        messages = [
            {"role": "system", "content": VERIFIER_PROMPT.format(claim=claim, context=context)},
            {"role": "user", "content": "Verify this claim."}
        ]
        
        try:
            response = self.llm.generate_text(messages, max_new_tokens=512, temperature=0.0)
            data = self._parse_json(response)
            
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus(data.get("status", "uncertain")),
                confidence=data.get("confidence", "low"),
                justification=data.get("justification", "Analysis failed"),
                recommended_action=RecommendedAction(data.get("recommended_action", "check")),
                original_text=claim
            )
        except Exception as e:
            logger.error(f"Verification extraction failed for '{claim}': {e}")
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus.UNCERTAIN,
                confidence="low",
                justification=f"Verification failed: {e}",
                recommended_action=RecommendedAction.CHECK
            )

    def _parse_json(self, response: str) -> Dict[str, Any]:
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        return {}


# =============================================================================
# MAIN (Test)
# =============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Claim Verification Engine Test")
    
    # Mock retriever
    class MockRetriever:
        def retrieve(self, query, top_k=3):
            from backend.food_synthesis import RetrievedDocument  # Lazy import for test
            return [RetrievedDocument(
                text="Starch gelatinization typically occurs between 60-70C in wheat.",
                score=0.9,
                doc_type="chemistry",
                source="test"
            )]

    verifier = ClaimVerifier()
    text = "Wheat starch gelatinizes at 65C. Rosemary inhibits enzymes at 200C."
    
    report = verifier.verify(text, MockRetriever())
    print("\nReport:")
    print(json.dumps(report.to_dict(), indent=2))
