import sys
import os
import logging

# Add backend to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.ERROR)

from backend.mode_classifier import classify_response_mode, is_biological_context
from backend.response_modes import ResponseMode

def test_routing_repair():
    print("🚦 Testing Routing Repair (Biological Expert Selection)\n")
    
    test_cases = [
        ("Why is sugar sweet?", ResponseMode.DIAGNOSTIC, "Mechanism Question"),
        ("What receptors does caffeine bind to?", ResponseMode.DIAGNOSTIC, "Receptor Question"),
        ("Explain the smell of rain", ResponseMode.DIAGNOSTIC, "Perception Question (Smell)"),
        ("Tell me a joke", ResponseMode.CONVERSATION, "Conversation Baseline"),
        ("I like apples", ResponseMode.CONVERSATION, "Conversation Baseline 2"),
        ("What is the mechanism of umami?", ResponseMode.DIAGNOSTIC, "Keyword 'mechanism'"),
        ("How does msg working?", ResponseMode.DIAGNOSTIC, "Causal intent 'how does' + compound 'msg' (handled by causal or bio)")
    ]
    
    failures = 0
    for query, expected_mode, desc in test_cases:
        # Test 1: is_biological_context check
        is_bio = is_biological_context(query)
        
        # Test 2: Final Classification
        mode = classify_response_mode(query, previous_mode=ResponseMode.CONVERSATION)
        
        status = "✅" if mode == expected_mode else "❌"
        print(f"{status} [{desc}] -> Query: '{query}'")
        print(f"   - Is Bio Context: {is_bio}")
        print(f"   - Result Mode: {mode.value}")
        print(f"   - Expected:    {expected_mode.value}")
        
        if mode != expected_mode:
            failures += 1
            print(f"   !!! FAILURE: Expected {expected_mode.value} but got {mode.value}")
            
    if failures == 0:
        print("\n🏆 ALL ROUTING CONTRACTS VERIFIED!")
    else:
        print(f"\n❌ {failures} ROUTING FAILURES DETECTED.")
        sys.exit(1)

if __name__ == "__main__":
    test_routing_repair()
