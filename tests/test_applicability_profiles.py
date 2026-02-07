import unittest
from backend.applicability_profile import ApplicabilityProfile, ApplicabilityMatch, compute_applicability_match


class TestApplicabilityProfiles(unittest.TestCase):
    def test_empty_profile_is_general(self):
        """Empty profile should be treated as generally applicable."""
        profile = ApplicabilityProfile()
        self.assertTrue(profile.is_empty())
        
        match = compute_applicability_match(profile, {})
        self.assertTrue(match.exact_match)
        self.assertEqual(match.confidence_score, 1.0)
        self.assertEqual(len(match.missing_fields), 0)

    def test_exact_match(self):
        """Exact context match should result in exact_match=True."""
        profile = ApplicabilityProfile(
            population={"general_adults"},
            dietary_context={"omnivorous"}
        )
        
        user_context = {
            "population": "general_adults",
            "dietary_context": "omnivorous"
        }
        
        match = compute_applicability_match(profile, user_context)
        self.assertTrue(match.exact_match)
        self.assertFalse(match.partial_match)
        self.assertEqual(match.confidence_score, 1.0)

    def test_partial_match(self):
        """Partial context match should result in partial_match=True."""
        profile = ApplicabilityProfile(
            population={"general_adults"},
            dietary_context={"vegetarian"}
        )
        
        user_context = {
            "population": "general_adults"
            # dietary_context missing
        }
        
        match = compute_applicability_match(profile, user_context)
        self.assertFalse(match.exact_match)
        self.assertTrue(match.partial_match)
        self.assertEqual(match.confidence_score, 0.5)  # 1 of 2 fields matched
        self.assertIn("dietary_context", match.missing_fields)

    def test_missing_critical_fields(self):
        """Missing critical fields should be tracked."""
        profile = ApplicabilityProfile(
            population={"diabetics"},
            dose_constraints="≥10g fiber/day"
        )
        
        user_context = {}  # No context provided
        
        match = compute_applicability_match(profile, user_context)
        self.assertFalse(match.exact_match)
        self.assertFalse(match.partial_match)
        self.assertEqual(match.confidence_score, 0.0)
        self.assertIn("population", match.missing_fields)
        self.assertIn("dose_info", match.missing_fields)


if __name__ == '__main__':
    unittest.main()
