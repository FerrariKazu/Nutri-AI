import unittest
from unittest.mock import MagicMock
from backend.claim_verifier import ClaimVerifier, ClaimVerification
from backend.mechanism_engine import MechanismChain, MechanismStep

class TestClaimBinding(unittest.TestCase):
    def setUp(self):
        self.mock_pubchem = MagicMock()
        self.mock_usda = MagicMock()
        self.verifier = ClaimVerifier(pubchem_client=self.mock_pubchem, usda_client=self.mock_usda)
        
    def test_mechanism_binding_passed(self):
        """Test that a verified claim gets a mechanism attached."""
        # Setup mock return from PubChem
        self.mock_pubchem.resolve_compound.return_value = (123, {"MolecularFormula": "Fe"})
        
        # Test input claim
        mock_claim = MagicMock()
        mock_claim.claim_id = "1"
        mock_claim.text = "Iron is good"
        mock_claim.type = "quantitative" # Allowed source: pubchem
        
        # Run verification
        result = self.verifier.verify_single_claim(mock_claim)
        
        # Assertions
        self.assertTrue(result.verified)
        self.assertEqual(result.source, "pubchem")
        self.assertIsNotNone(result.mechanism)
        self.assertIsInstance(result.mechanism, MechanismChain)
        self.assertFalse(result.mechanism.is_valid) # Since assemble_chain is placeholder
        self.assertIn("MoA incomplete", result.explanation)

    def test_heuristic_no_mechanism(self):
        """Test that heuristic claims do not trigger mechanism engine (or fail gracefully)."""
        # Test input claim with NO verified keywords
        mock_claim = MagicMock()
        mock_claim.claim_id = "2"
        mock_claim.text = "Magic beans are magic"
        mock_claim.type = "heuristic"
        
        result = self.verifier.verify_single_claim(mock_claim)
        
        self.assertFalse(result.verified)
        self.assertEqual(result.source, "heuristic")
        # Depending on implementation, mechanism might be None or not attempted
        self.assertIsNone(result.mechanism) 

if __name__ == '__main__':
    unittest.main()
