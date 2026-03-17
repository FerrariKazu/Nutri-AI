import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.orchestrator import NutriOrchestrator
from backend.governance_types import EscalationLevel

class TestPersistenceV2(unittest.TestCase):
    def setUp(self):
        # Mock dependencies to avoid real AI calls and heavy imports
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

    def test_scientific_lock_persistence(self):
        """Verify TIER_3 persists for short follow-up questions."""
        
        # Mock BeliefState for turn 1
        bs1 = MagicMock()
        bs1.previous_tier = EscalationLevel.TIER_0.value
        
        # turn 1: Scientific query -> TIER_3
        tier_t1 = self.orchestrator._resolve_escalation_level(
            user_message="Explain the binding of ligands to caffeine receptors",
            v2_intent={"intent_category": "scientific_query"},
            preferences={"audience_mode": "scientific"},
            belief_state=bs1,
            classification_conf=0.9
        )
        self.assertEqual(tier_t1, EscalationLevel.TIER_3)
        print("✅ Step 1: Scientific query correctly escalated to TIER_3")
        
        # turn 2: Short follow-up -> should maintain TIER_3
        bs2 = MagicMock()
        bs2.previous_tier = EscalationLevel.TIER_3.value
        
        tier_t2 = self.orchestrator._resolve_escalation_level(
            user_message="And salt?",
            v2_intent={"intent_category": "scientific_query"}, # Simplified for test
            preferences={"audience_mode": "scientific"},
            belief_state=bs2,
            classification_conf=0.9
        )
        self.assertEqual(tier_t2, EscalationLevel.TIER_3)
        print("✅ Step 2: Follow-up maintained TIER_3 persistence")
        
    def test_safety_caps_prevention(self):
        """Verify safety cap prevents escalation for tiny queries from TIER_0."""
        bs = MagicMock()
        bs.previous_tier = EscalationLevel.TIER_0.value
        
        tier = self.orchestrator._resolve_escalation_level(
            user_message="Hi",
            v2_intent={"intent_category": "greeting"},
            preferences={"audience_mode": "casual"},
            belief_state=bs,
            classification_conf=1.0
        )
        self.assertEqual(tier, EscalationLevel.TIER_0)
        print("✅ Safety Cap verified for short message at TIER_0")

if __name__ == "__main__":
    unittest.main()
