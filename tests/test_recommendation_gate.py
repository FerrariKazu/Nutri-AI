import unittest
from backend.recommendation_gate import RecommendationGate, RecommendationDecision, RecommendationResult
from backend.applicability_profile import ApplicabilityMatch
from backend.risk_engine import RiskAssessment, RiskFlag


class TestRecommendationGate(unittest.TestCase):
    def setUp(self):
        self.gate = RecommendationGate()

    def test_explanatory_claim_allowed(self):
        """Explanatory claims should bypass strict gating."""
        # Even with invalid mechanism and risks
        match = ApplicabilityMatch(exact_match=False, partial_match=False, missing_fields=["population"], confidence_score=0.0)
        risk = RiskAssessment(flags=[], confidence=0.0, unknown_risk=True)
        
        result = self.gate.evaluate(
            mechanism_valid=False,
            applicability_match=match,
            risk_assessment=risk,
            claim_type="explanatory"
        )
        
        self.assertEqual(result.decision, RecommendationDecision.ALLOW)
        self.assertEqual(result.reason, "safe_to_discuss_only")

    def test_blocking_risk_withholds(self):
        """Moderate/high risks should WITHHOLD recommendation."""
        match = ApplicabilityMatch(exact_match=True, partial_match=False, missing_fields=[], confidence_score=1.0)
        risk = RiskAssessment(
            flags=[RiskFlag(category="metabolic", description="Test risk", severity="moderate")],
            confidence=0.8,
            unknown_risk=False
        )
        
        result = self.gate.evaluate(
            mechanism_valid=True,
            applicability_match=match,
            risk_assessment=risk,
            claim_type="action-implying"
        )
        
        self.assertEqual(result.decision, RecommendationDecision.WITHHOLD)
        self.assertEqual(result.reason, "identified_risk")

    def test_unknown_risk_requires_context(self):
        """Unknown risk should require more context."""
        match = ApplicabilityMatch(exact_match=True, partial_match=False, missing_fields=[], confidence_score=1.0)
        risk = RiskAssessment(flags=[], confidence=0.3, unknown_risk=True)
        
        result = self.gate.evaluate(
            mechanism_valid=True,
            applicability_match=match,
            risk_assessment=risk,
            claim_type="action-implying"
        )
        
        self.assertEqual(result.decision, RecommendationDecision.REQUIRE_MORE_CONTEXT)

    def test_partial_match_requires_context(self):
        """Partial applicability match should require more context."""
        match = ApplicabilityMatch(exact_match=False, partial_match=True, missing_fields=["dietary_context"], confidence_score=0.5)
        risk = RiskAssessment(flags=[], confidence=0.8, unknown_risk=False)
        
        result = self.gate.evaluate(
            mechanism_valid=True,
            applicability_match=match,
            risk_assessment=risk,
            claim_type="action-implying"
        )
        
        self.assertEqual(result.decision, RecommendationDecision.REQUIRE_MORE_CONTEXT)
        self.assertEqual(result.reason, "population_mismatch")

    def test_all_checks_passed_allows(self):
        """Perfect conditions should ALLOW recommendation."""
        match = ApplicabilityMatch(exact_match=True, partial_match=False, missing_fields=[], confidence_score=1.0)
        risk = RiskAssessment(flags=[], confidence=0.9, unknown_risk=False)
        
        result = self.gate.evaluate(
            mechanism_valid=True,
            applicability_match=match,
            risk_assessment=risk,
            claim_type="action-implying"
        )
        
        self.assertEqual(result.decision, RecommendationDecision.ALLOW)
        self.assertEqual(result.reason, "mechanism_strong")


if __name__ == '__main__':
    unittest.main()
