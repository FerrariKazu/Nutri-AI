import unittest
import json
import hashlib
from typing import List
from backend.contracts.evidence_schema import EvidenceRecord, StudyType, EffectDirection, EvidenceGrade
from backend.contracts.evidence_policy import EvidencePolicy, PolicyRule
from backend.intelligence.weighting_engine import PolicyEngine
from backend.policies.default_policy_v1 import NUTRI_EVIDENCE_V1

class TestPolicyReproducibility(unittest.TestCase):
    def setUp(self):
        self.mock_claim = {"id": "test_1", "statement": "Test claim"}
        self.mock_evidence = [
            EvidenceRecord(
                id="ev_1",
                claim_id="test_1",
                source_identifier="PMID: 1",
                study_type=StudyType.RCT,
                experimental_model="Human",
                n=500,
                effect_direction=EffectDirection.POSITIVE,
                publication_year=2022,
                evidence_grade=EvidenceGrade.STRONG
            )
        ]

    def test_reproducibility(self):
        """Invariant: Same Input + Same Policy = Identical Output."""
        res1 = PolicyEngine.execute(self.mock_claim, self.mock_evidence, NUTRI_EVIDENCE_V1)
        res2 = PolicyEngine.execute(self.mock_claim, self.mock_evidence, NUTRI_EVIDENCE_V1)
        
        dict1 = res1.to_dict()
        dict2 = res2.to_dict()
        
        self.assertEqual(dict1, dict2)
        print("PASS: Bit-for-bit reproducibility verified.")

    def test_crash_on_missing_policy(self):
        """Invariant: Failure Doctrine - Hard stop if policy missing."""
        with self.assertRaises(RuntimeError) as cm:
            PolicyEngine.execute(self.mock_claim, self.mock_evidence, None)
        
        self.assertIn("Policy artifact is None", str(cm.exception))
        print("PASS: Hard stop on missing policy verified.")

    def test_structural_breakdown(self):
        """Invariant: Pure structural reasoning in breakdown."""
        res = PolicyEngine.execute(self.mock_claim, self.mock_evidence, NUTRI_EVIDENCE_V1)
        breakdown = res.to_dict()
        
        self.assertEqual(breakdown["policy_id"], NUTRI_EVIDENCE_V1.policy_id)
        self.assertEqual(breakdown["final_score"], res.final_score)
        
        # Verify rule firings
        categories = [rf["category"] for rf in breakdown["rule_firings"]]
        self.assertIn("study_type_weight", categories)
        self.assertIn("sample_size_bonus", categories)
        
        # Verify RCT weight (0.4) + baseline (0.1) + sample size (0.1 for n=500) + recency (0.1 for 2022) = 0.7
        self.assertEqual(res.final_score, 0.7)
        print(f"PASS: Structural breakdown verified. Score: {res.final_score}")

    def test_policy_hash_consistency(self):
        """Invariant: Policy hash is deterministic."""
        hash1 = NUTRI_EVIDENCE_V1.compute_hash()
        hash2 = NUTRI_EVIDENCE_V1.compute_hash()
        self.assertEqual(hash1, hash2)
        print(f"PASS: Policy hash consistency verified. Hash: {hash1}")

if __name__ == "__main__":
    unittest.main()
