import unittest
from backend.response_modes import ResponseMode
from backend.verification.trace_domain_classifier import (
    classify_trace_domain_preliminary,
    classify_trace_domain_final
)

class TestTraceDomainClassifier(unittest.TestCase):

    # ── PASS 1: Preliminary Classification Tests ──

    def test_pass1_explicit_scientific_keywords(self):
        """Bio keywords should trigger SCIENTIFIC domain with high confidence."""
        msg = "What is the mechanism of caffeine on adenosine receptors?"
        domain, vis, conf, reason = classify_trace_domain_preliminary(msg, ResponseMode.CONVERSATION)
        self.assertEqual(domain, "scientific")
        self.assertEqual(vis, "expanded")
        self.assertGreaterEqual(conf, 0.95)
        self.assertIn("bio_keywords", reason)

    def test_pass1_mode_based_scientific(self):
        """Scientific modes should trigger SCIENTIFIC domain."""
        msg = "Analyze this meal."
        # Even without bio keywords, the mode drives it
        domain, vis, conf, reason = classify_trace_domain_preliminary(msg, ResponseMode.NUTRITION_ANALYSIS)
        self.assertEqual(domain, "scientific")
        self.assertEqual(vis, "expanded")
        self.assertEqual(conf, 0.85)
        self.assertIn("response_mode", reason)

    def test_pass1_procedural_provisional(self):
        """Procedural mode defaults to provisional CONTEXTUAL (hidden)."""
        msg = "How do I cook pasta?"
        domain, vis, conf, reason = classify_trace_domain_preliminary(msg, ResponseMode.PROCEDURAL)
        self.assertEqual(domain, "contextual")
        self.assertEqual(vis, "hidden")
        self.assertEqual(conf, 0.60)
        self.assertIn("provisional_procedural", reason)

    def test_pass1_conversation_default(self):
        """General chat defaults to provisional CONTEXTUAL."""
        msg = "Hello there"
        domain, vis, conf, reason = classify_trace_domain_preliminary(msg, ResponseMode.CONVERSATION)
        self.assertEqual(domain, "contextual")
        self.assertEqual(vis, "hidden")
        self.assertEqual(conf, 0.60)

    # ── PASS 2: Final Classification Tests (Monotonicity) ──

    def test_pass2_scientific_sticky(self):
        """SCIENTIFIC domain is sticky, can never be downgraded."""
        # Preliminary said scientific
        domain, vis, conf, reason = classify_trace_domain_final(
            preliminary_domain="scientific",
            preliminary_confidence=0.95,
            has_enriched_claims=False, # Even if no claims found!
            enriched_claim_count=0,
            belief_state_active=False,
            has_prior_claims=False
        )
        self.assertEqual(domain, "scientific")
        self.assertEqual(vis, "expanded")
        self.assertEqual(conf, 0.95) # Maintains confidence

    def test_pass2_upgrade_contextual_to_scientific(self):
        """Contextual upgrades to SCIENTIFIC if unexpected claims appear."""
        domain, vis, conf, reason = classify_trace_domain_final(
            preliminary_domain="contextual",
            preliminary_confidence=0.60,
            has_enriched_claims=True,
            enriched_claim_count=3,
            belief_state_active=False,
            has_prior_claims=False
        )
        self.assertEqual(domain, "scientific")
        self.assertEqual(vis, "expanded")
        self.assertEqual(conf, 0.80)
        self.assertIn("upgraded_to_scientific", reason)

    def test_pass2_upgrade_contextual_to_hybrid_belief(self):
        """Contextual upgrades to HYBRID if claims + belief state active."""
        domain, vis, conf, reason = classify_trace_domain_final(
            preliminary_domain="contextual",
            preliminary_confidence=0.60,
            has_enriched_claims=True,
            enriched_claim_count=2,
            belief_state_active=True,
            has_prior_claims=False
        )
        self.assertEqual(domain, "hybrid")
        self.assertEqual(vis, "collapsible")
        self.assertEqual(conf, 0.75)
        self.assertIn("upgraded_to_hybrid", reason)

    def test_pass2_upgrade_contextual_to_hybrid_prior(self):
        """Contextual upgrades to HYBRID if prior claims exist (even without current claims)."""
        domain, vis, conf, reason = classify_trace_domain_final(
            preliminary_domain="contextual",
            preliminary_confidence=0.60,
            has_enriched_claims=False,
            enriched_claim_count=0,
            belief_state_active=False,
            has_prior_claims=True
        )
        self.assertEqual(domain, "hybrid")
        self.assertEqual(vis, "collapsible")
        self.assertEqual(conf, 0.70)
        self.assertIn("upgraded_to_hybrid", reason)

    def test_pass2_hybrid_monotonic(self):
        """HYBRID cannot downgrade to CONTEXTUAL."""
        domain, vis, conf, reason = classify_trace_domain_final(
            preliminary_domain="hybrid", # Suppose Pass 1 logic allowed this (hypothetical)
            preliminary_confidence=0.70,
            has_enriched_claims=False,
            enriched_claim_count=0,
            belief_state_active=False,
            has_prior_claims=False
        )
        self.assertEqual(domain, "hybrid")
        self.assertEqual(vis, "collapsible")
        self.assertEqual(conf, 0.70)

if __name__ == '__main__':
    unittest.main()
