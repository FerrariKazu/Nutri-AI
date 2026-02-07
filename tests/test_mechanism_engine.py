import unittest
from backend.mechanism_engine import MechanismEngine, MechanismStep, MechanismChain

class TestMechanismEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MechanismEngine()

    def test_valid_chain(self):
        """Test a perfectly valid causal chain."""
        steps = [
            MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="interaction", description="Delays gastric emptying", evidence_source="rag", confidence=0.8),
            MechanismStep(type="physiology", description="Slower glucose absorption", evidence_source="rag", confidence=0.85),
            MechanismStep(type="outcome", description="Reduced insulin spike", evidence_source="rag", confidence=0.8)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertTrue(chain.is_valid)
        self.assertEqual(chain.weakest_link_confidence, 0.8)
        self.assertIsNone(chain.break_reason)

    def test_direct_jump_invalid(self):
        """Test blocking of Compound -> Outcome jumps."""
        steps = [
            MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=1.0),
            MechanismStep(type="outcome", description="Reduced insulin spike", evidence_source="rag", confidence=0.8)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        self.assertIn("Invalid Jump", chain.break_reason)

    def test_invalid_start(self):
        """Test chain must start with compound/nutrient."""
        steps = [
            MechanismStep(type="interaction", description="Delays gastric emptying", evidence_source="rag", confidence=0.8)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        self.assertIn("Chain must start with", chain.break_reason)
        
    def test_incomplete_end(self):
        """Test chain cannot end on an interaction."""
        steps = [
            MechanismStep(type="compound", description="Fiber", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="interaction", description="Binds bile acids", evidence_source="rag", confidence=0.8)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        self.assertIn("conclude", chain.break_reason)

    def test_weakest_link_calculation(self):
        """Test that confidence is the minimum of all steps."""
        steps = [
            MechanismStep(type="compound", description="X", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="interaction", description="Y", evidence_source="rag", confidence=0.5), # Weakest
            MechanismStep(type="outcome", description="Z", evidence_source="rag", confidence=0.9)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertTrue(chain.is_valid)
        self.assertEqual(chain.weakest_link_confidence, 0.5)

if __name__ == '__main__':
    unittest.main()
