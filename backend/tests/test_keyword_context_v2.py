import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.orchestrator import NutriOrchestrator
from backend.governance_types import EscalationLevel

class TestKeywordContextV2(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        deps = [
            'backend.orchestrator.NutriPipeline',
            'backend.orchestrator.MetaLearner',
            'backend.orchestrator.IntentDetector',
            'backend.orchestrator.LLMQwen3',
            'backend.orchestrator.ExplanationRouter',
            'backend.orchestrator.NutriEngine',
            'backend.orchestrator.BeliefState'
        ]
        self.patches = [patch(d) for d in deps]
        for p in self.patches:
            p.start()
            
        self.orchestrator = NutriOrchestrator(MagicMock())

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_contextual_keywords_culinary(self):
        """Verify 'bind' in a culinary context does NOT escalate to TIER_3."""
        # "bind a roast" -> Culinary context
        # Scoring: +1 length (>20), but no sci context.
        bs = MagicMock()
        bs.previous_tier = EscalationLevel.TIER_0.value
        tier = self.orchestrator._resolve_escalation_level(
            user_message="How do I bind a roast for cooking?",
            v2_intent={"intent_category": "recipe_query"},
            preferences={"audience_mode": "casual"},
            belief_state=bs,
            classification_conf=0.9
        )
        # Score should be ~1 (+1 length). Needs 3 for TIER_2, 5 for TIER_3.
        self.assertLess(tier.value, EscalationLevel.TIER_2.value)
        print(f"✅ Culinary 'bind' correctly kept at {tier.name}")

    def test_contextual_keywords_scientific(self):
        """Verify 'bind' in a scientific context triggers TIER_3."""
        # "bind to receptor" + Sci Mode
        # Scoring: +2 sci keyword, +2 sci mode, +1 length = 5 (TIER_3 floor)
        bs = MagicMock()
        bs.previous_tier = EscalationLevel.TIER_0.value
        tier = self.orchestrator._resolve_escalation_level(
            user_message="How does caffeine bind to the adenosine receptor?",
            v2_intent={"intent_category": "scientific_query"},
            preferences={"audience_mode": "scientific"},
            belief_state=bs,
            classification_conf=0.9
        )
        self.assertEqual(tier, EscalationLevel.TIER_3)
        print("✅ Scientific 'bind' correctly escalated to TIER_3")

    def test_nutrition_keywords(self):
        """Verify nutrition keywords trigger TIER_2."""
        bs = MagicMock()
        bs.previous_tier = EscalationLevel.TIER_0.value
        # "calories" + "protein" + length = 3 -> TIER_2
        tier = self.orchestrator._resolve_escalation_level(
            user_message="What are the calories and protein in this recipe?",
            v2_intent={"intent_category": "nutrition_query"},
            preferences={"audience_mode": "casual"},
            belief_state=bs,
            classification_conf=0.9
        )
        self.assertEqual(tier, EscalationLevel.TIER_2)
        print("✅ Nutrition keywords triggered TIER_2")

    def test_ambiguity_fallback(self):
        """Verify low confidence forces TIER_1_CLARIFICATION (effectively TIER_1)."""
        bs = MagicMock()
        bs.previous_tier = EscalationLevel.TIER_0.value
        tier = self.orchestrator._resolve_escalation_level(
            user_message="Something vague",
            v2_intent={"intent_category": "unknown"},
            preferences={"audience_mode": "casual"},
            belief_state=bs,
            classification_conf=0.4 # < 0.6
        )
        self.assertEqual(tier, EscalationLevel.TIER_1)
        print("✅ Low confidence forced TIER_1 fallback")

if __name__ == "__main__":
    unittest.main()
