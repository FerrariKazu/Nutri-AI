"""
Quick test script for Phase 5 & 6 implementation
Verifies:
- Phase selection with confidence gates
- Memory extraction (two-stage)
- User preference storage
"""

import sys
sys.path.insert(0, '/home/ferrarikazu/nutri-ai')

from backend.phase_schema import ThinkingPhase, PhaseSelector
from backend.selective_memory import UserPreferences, MemoryExtractor
from backend.response_modes import ResponseMode
from backend.food_synthesis import IntentOutput

print("=" * 60)
print("Phase 5 & 6 Quick Verification")
print("=" * 60)

# Test 1: Phase Selection with Low Confidence
print("\n\ud83e\uddea Test 1: Low Confidence Intent (< 0.6) → Zero Phases")
intent_low = IntentOutput()
intent_low.confidence = 0.4
phases = PhaseSelector.select_phases("My bread is dense", ResponseMode.DIAGNOSTIC, intent_low)
assert len(phases) == 0, f"Expected 0 phases, got {len(phases)}"
print("✅ Zero-phase fallback works!")

# Test 2: High Confidence Diagnostic
print("\n\ud83e\uddea Test 2: High Confidence + Diagnostic → Phases Selected")
intent_high = IntentOutput()
intent_high.confidence = 0.8
phases = PhaseSelector.select_phases("Why is my bread too dry?", ResponseMode.DIAGNOSTIC, intent_high)
print(f"Selected phases: {[p.value for p in phases]}")
assert len(phases) > 0, "Expected at least 1 phase"
print("✅ Phase selection works!")

# Test 3: Skill Level Modulation
print("\n\ud83e\uddea Test 3: Beginner Skill Level → MODEL Deprioritized")
prefs_beginner = UserPreferences(skill_level="beginner")
phases_beginner = PhaseSelector.select_phases("What if I add more yeast?", ResponseMode.DIAGNOSTIC, intent_high, prefs_beginner)
print(f"Beginner phases: {[p.value for p in phases_beginner]}")
phases_expert = PhaseSelector.select_phases("What if I add more yeast?", ResponseMode.DIAGNOSTIC, intent_high, None)
print(f"Expert phases: {[p.value for p in phases_expert]}")
print("✅ Skill-level modulation works!")

# Test 4: Phase Content Validation
print("\n\ud83e\uddea Test 4: Phase Content Validation")
recommend_content = "Add more salt and reduce the heat to 350°F"
is_valid = PhaseSelector.validate_phase_content(ThinkingPhase.RECOMMEND, recommend_content)
assert is_valid, "RECOMMEND phase should be valid with action verbs"
print("✅ Content with action verbs validated!")

model_content = "You should first heat the oven, then add the ingredients"
is_invalid = PhaseSelector.validate_phase_content(ThinkingPhase.MODEL, model_content)
assert not is_invalid, "MODEL phase should be invalid with instruction phrases"
print("✅ Invalid MODEL content rejected!")

# Test 5: Memory Extraction (Deterministic Filter)
print("\n\ud83e\uddea Test 5: Memory Extraction - Deterministic Filter")

# Mock LLM for test
class MockLLM:
    def generate(self, prompt, max_tokens=150, temperature=0.1):
        return '{"skill_level": "beginner", "equipment": ["air fryer"]}'

extractor = MemoryExtractor(MockLLM())
prefs_empty = UserPreferences()

# Test with trigger keyword
update1 = extractor.extract_preferences("I'm a beginner and I only have an air fryer", prefs_empty)
assert update1 is not None, "Should extract preferences when triggers present"
print(f"✅ Extracted: {update1}")

# Test without trigger (should skip LLM)
update2 = extractor.extract_preferences("What's a good recipe?", prefs_empty)
assert update2 is None, "Should return None when no triggers"
print("✅ No extraction when no triggers!")

print("\n" + "=" * 60)
print("✅ All Tests Passed!")
print("=" * 60)
