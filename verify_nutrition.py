
import sys
import os
from unittest.mock import MagicMock
sys.path.append(os.getcwd())

# Mock LLM dependencies to avoid ImportErrors
sys.modules['backend.llm_qwen3'] = MagicMock()
sys.modules['backend.llm'] = MagicMock()
sys.modules['backend.llm.factory'] = MagicMock()
sys.modules['ollama'] = MagicMock()

from backend.mode_classifier import classify_response_mode
from backend.response_modes import ResponseMode
# Now import NutriEngine (it will use the mocks)
from backend.nutri_engine import NutriEngine
import re

def test_classifier():
    print("--- Testing Mode Classification ---")
    
    # 1. Casual Chat
    mode = classify_response_mode("How do I make spicy carbonara?")
    print(f"Casual: {mode} (Expected: PROCEDURAL or CONVERSATION) -> {'✅' if mode in [ResponseMode.PROCEDURAL, ResponseMode.CONVERSATION] else '❌'}")

    # 2. Qualitative Health
    mode = classify_response_mode("Is this healthy?")
    print(f"Health: {mode} (Expected: DIAGNOSTIC) -> {'✅' if mode == ResponseMode.DIAGNOSTIC else '❌'}")

    # 3. Numeric Request
    mode = classify_response_mode("How many calories are in this?")
    print(f"Calories: {mode} (Expected: NUTRITION_ANALYSIS) -> {'✅' if mode == ResponseMode.NUTRITION_ANALYSIS else '❌'}")

def test_leakage_detector():
    print("\n--- Testing Numeric Leakage Detector (Mode-Aware) ---")
    
    # Mock engine without LLM for unit test of validator
    engine = NutriEngine(None, None)
    
    test_cases = [
        # (Text, Mode, ShouldStrip)
        ("This dish has 500 kcal.", ResponseMode.CONVERSATION, True),
        ("You should add 20g of protein.", ResponseMode.PROCEDURAL, True), # Explicit nutrient name -> Block
        ("It's roughly ~700 calories.", ResponseMode.DIAGNOSTIC, True),
        ("The Scoville units are around 50000.", ResponseMode.CONVERSATION, True),
        
        # Culinary Contexts
        ("Add 500g flour.", ResponseMode.PROCEDURAL, False), # Should allow in Procedural
        ("Mix 20g of sugar.", ResponseMode.PROCEDURAL, False), # Should allow in Procedural
        ("It looks like 50g.", ResponseMode.CONVERSATION, True), # Suspicious in Conversation -> Block
        ("It contains 50g of sugar.", ResponseMode.CONVERSATION, True), # "contains" + "sugar" + Conversation -> Block (ambiguous logic fallback blocks non-procedural)
                                                                        
        
        # Testing the "sugar" keyword logic
        ("Add 50g sugar.", ResponseMode.PROCEDURAL, False), # "sugar" allowed in procedural now.
    ]
    
    for text, mode, should_strip in test_cases:
        governed = engine._apply_nutrition_governance(text, mode)
        detected = governed != text
        
        status = "✅" if (detected == should_strip) else "❌"
        print(f"[{mode.value}] '{text}' -> Detected: {detected} | Result: {governed[:30]}... {status}")

def test_regression_scenarios():
    print("\n--- Testing Regression Scenarios ---")
    
    # 1. "How do I make spicy carbonara?" -> No numbers
    # We can't easily test the output content without the LLM, but we can test the mode.
    mode = classify_response_mode("How do I make spicy carbonara?")
    print(f"Regression 1 (Carbonara): Mode {mode} (Expected PROCEDURAL/CONVERSATION) -> {'✅' if mode in [ResponseMode.PROCEDURAL, ResponseMode.CONVERSATION] else '❌'}")
    
    # 2. "How many calories per serving?" -> NUTRITION_ANALYSIS
    mode = classify_response_mode("How many calories per serving?")
    print(f"Regression 2 (Calories): Mode {mode} (Expected NUTRITION_ANALYSIS) -> {'✅' if mode == ResponseMode.NUTRITION_ANALYSIS else '❌'}")

    # 3. "Is this healthy?" -> DIAGNOSTIC (Qualitative)
    mode = classify_response_mode("Is this healthy?")
    print(f"Regression 3 (Healthy): Mode {mode} (Expected DIAGNOSTIC) -> {'✅' if mode == ResponseMode.DIAGNOSTIC else '❌'}")


if __name__ == "__main__":
    test_classifier()
    test_leakage_detector()
    test_regression_scenarios()
