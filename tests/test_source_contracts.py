import unittest
from backend.mechanism_engine import MechanismEngine, MechanismStep, MechanismChain


class TestMoAEnforcement(unittest.TestCase):
    def setUp(self):
        self.engine = MechanismEngine()

    def test_source_contract_violation_pubchem_on_outcome(self):
        """Test that PubChem cannot be used as source for outcome steps."""
        steps = [
            MechanismStep(type="compound", description="Fiber", evidence_source="pubchem", confidence=0.9),
            MechanismStep(type="interaction", description="Binds bile acids", evidence_source="rag", confidence=0.8),
            MechanismStep(type="outcome", description="Lower cholesterol", evidence_source="pubchem", confidence=0.9)  # VIOLATION
        ]
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        self.assertIn("Evidence type violation", chain.break_reason)
        self.assertIn("outcome", chain.break_reason.lower())

    def test_source_contract_violation_rag_on_compound(self):
        """Test that RAG cannot be used as source for compound steps."""
        steps = [
            MechanismStep(type="compound", description="Lycopene", evidence_source="rag", confidence=0.9),  # VIOLATION
            MechanismStep(type="outcome", description="Antioxidant effect", evidence_source="rag", confidence=0.8)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        self.assertIn("Evidence type violation", chain.break_reason)
        self.assertIn("compound", chain.break_reason.lower())

    def test_valid_source_contracts(self):
        """Test that valid source assignments pass validation."""
        steps = [
            MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=0.95),
            MechanismStep(type="interaction", description="Delays gastric", evidence_source="rag", confidence=0.85),
            MechanismStep(type="physiology", description="Slower glucose", evidence_source="rag", confidence=0.90),
            MechanismStep(type="outcome", description="Reduced spike", evidence_source="rag", confidence=0.85)
        ]
        chain = self.engine.validate_chain(steps)
        self.assertTrue(chain.is_valid)

    def test_usda_allowed_for_compound(self):
        """Test that USDA is allowed as evidence source for compound steps."""
        steps = [
            MechanismStep(type="compound", description="Spinach iron", evidence_source="usda", confidence=0.95),
            MechanismStep(type="outcome", description="Better iron levels", evidence_source="rag", confidence=0.8)
        ]
        # This should fail transition validation (compound -> outcome) but NOT source validation
        chain = self.engine.validate_chain(steps)
        self.assertFalse(chain.is_valid)
        # Should fail on jump, not source
        self.assertIn("Invalid Jump", chain.break_reason)


if __name__ == '__main__':
    unittest.main()
