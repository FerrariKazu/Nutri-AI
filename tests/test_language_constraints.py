import unittest
from backend.explanation_router import LanguagePolicy


class TestLanguageConstraints(unittest.TestCase):
    def test_banned_phrases_allow_decision(self):
        """ALLOW decision should not flag any phrases."""
        text = "You should eat this. It will definitely help."
        violations = LanguagePolicy.check_banned_phrases(text, "allow")
        
        self.assertEqual(len(violations), 0)

    def test_banned_phrases_withhold_decision(self):
        """WITHHOLD decision should flag banned phrases."""
        text = "You should eat this for guaranteed results."
        violations = LanguagePolicy.check_banned_phrases(text, "withhold")
        
        self.assertGreater(len(violations), 0)
        self.assertIn("you should", violations)
        self.assertIn("guaranteed", violations)

    def test_banned_phrases_require_context_decision(self):
        """REQUIRE_MORE_CONTEXT decision should flag banned phrases."""
        text = "This will always improve your health."
        violations = LanguagePolicy.check_banned_phrases(text, "require_more_context")
        
        self.assertGreater(len(violations), 0)
        self.assertIn("this will", violations)
        self.assertIn("always", violations)

    def test_for_decision_returns_correct_phrases(self):
        """for_decision should return appropriate phrase sets."""
        allow_phrases = LanguagePolicy.for_decision("allow")
        self.assertIn("may help", allow_phrases)
        
        withhold_phrases = LanguagePolicy.for_decision("withhold")
        self.assertIn("cannot recommend", withhold_phrases)
        
        context_phrases = LanguagePolicy.for_decision("require_more_context")
        self.assertIn("depends on", context_phrases)

    def test_safe_language_not_flagged(self):
        """Safe conditional language should not be flagged."""
        text = "This may help and could support better health depending on individual factors."
        violations = LanguagePolicy.check_banned_phrases(text, "require_more_context")
        
        self.assertEqual(len(violations), 0)


if __name__ == '__main__':
    unittest.main()
