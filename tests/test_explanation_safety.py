import unittest
from backend.explanation_router import ExplanationRouter, ExplanationVerbosity
from backend.mechanism_engine import MechanismStep, MechanismChain


class TestExplanationSafety(unittest.TestCase):
    def setUp(self):
        self.router = ExplanationRouter()

    def test_no_new_facts_valid_rendering(self):
        """Test that valid rendering passes no-new-facts check."""
        steps = [
            MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="interaction", description="Delays gastric emptying", evidence_source="rag", confidence=0.8),
            MechanismStep(type="outcome", description="Reduced insulin spike", evidence_source="rag", confidence=0.8)
        ]
        chain = MechanismChain(steps=steps, is_valid=True)
        chain.weakest_link_confidence = 0.8
        
        claim = "Lentils help stabilize blood sugar"
        
        # Should not raise (all entities from chain)
        rendered = self.router.render(claim, chain, ExplanationVerbosity.SCIENTIFIC)
        self.assertIsNotNone(rendered)

    def test_entity_extraction(self):
        """Test that _extract_entities correctly extracts words from mechanism."""
        steps = [
            MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="outcome", description="Better blood sugar", evidence_source="rag", confidence=0.8)
        ]
        chain = MechanismChain(steps=steps, is_valid=True)
        
        entities = self.router._extract_entities(chain)
        self.assertIn("lentil", entities)
        self.assertIn("fiber", entities)
        self.assertIn("blood", entities)
        self.assertIn("sugar", entities)

    def test_fallback_on_invalid_chain(self):
        """Test that router returns base claim when chain is invalid."""
        chain = MechanismChain(steps=[], is_valid=False, break_reason="Empty")
        claim = "Test claim"
        
        rendered = self.router.render(claim, chain, ExplanationVerbosity.FULL)
        self.assertEqual(rendered, claim)


if __name__ == '__main__':
    unittest.main()
