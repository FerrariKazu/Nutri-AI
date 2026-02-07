import unittest
from backend.risk_engine import RiskEngine, RiskFlag, RiskAssessment


class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiskEngine()

    def test_known_risk_detection(self):
        """Test that known risks are detected."""
        assessment = self.engine.assess(
            compound_names=["fiber"],
            population="general_adults",
            rag_coverage_score=0.8
        )
        
        self.assertGreater(len(assessment.flags), 0)
        self.assertTrue(any(f.category == "digestive" for f in assessment.flags))

    def test_unknown_risk_thin_coverage(self):
        """Test that unknown_risk=True when RAG coverage is thin."""
        assessment = self.engine.assess(
            compound_names=["unknown_compound"],
            population="general_adults",
            rag_coverage_score=0.3  # < 0.5
        )
        
        self.assertTrue(assessment.unknown_risk)

    def test_unknown_risk_non_general_population(self):
        """Test that unknown_risk=True for non-general populations."""
        assessment = self.engine.assess(
            compound_names=["fiber"],
            population="pregnant",  # Not general_adults
            rag_coverage_score=0.8
        )
        
        self.assertTrue(assessment.unknown_risk)

    def test_blocking_risk_detection(self):
        """Test that moderate/high severity risks are flagged as blocking."""
        assessment = self.engine.assess(
            compound_names=["iron"],
            population="general_adults",
            rag_coverage_score=0.8
        )
        
        # Iron has high severity risk (hemochromatosis)
        self.assertTrue(assessment.has_blocking_risk())

    def test_no_risk_scenario(self):
        """Test scenario with no known risks and good coverage."""
        assessment = self.engine.assess(
            compound_names=["water"],  # No known risks
            population="general_adults",
            rag_coverage_score=0.9
        )
        
        self.assertEqual(len(assessment.flags), 0)
        self.assertFalse(assessment.unknown_risk)
        self.assertFalse(assessment.has_blocking_risk())


if __name__ == '__main__':
    unittest.main()
