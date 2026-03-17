import logging
import sys

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test Cases
test_cases = [
    # 🚫 Non-Scientific
    ("Hello", False),
    ("Hi", False),
    ("Good morning", False),
    ("Thanks Nutri", False),
    ("ok", False),
    ("Is this thing working?", False), # Might be tricky, but no keywords
    
    # ✅ Scientific
    ("Analyze caffeine", True),
    ("What are the effects of sugar?", True),
    ("Is protein good for muscle?", True),
    ("Vitamin deficiency symptoms", True),
    ("Does coffee cause anxiety?", True),
    ("Tell me about metabolism", True),
    ("Is toxicity a concern?", True)
]

def _is_scientific_intent(user_message: str) -> bool:
    """
    Heuristic detection for scientific vs. general discourse.
    (Phase 7 Implementation COPY for Verification)
    """
    scientific_keywords = [
        "analyze", "effect", "impact", "mechanism", "pathway",
        "study", "caffeine", "sugar", "protein", "vitamin",
        "deficiency", "symptom", "cause", "biological", "chemical",
        "metabolism", "nutrient", "dose", "toxicity", "interaction"
    ]
    
    if not user_message:
        return False
        
    # 1. Length Heuristic (Too short = likely chat)
    if len(user_message.split()) < 2:
        return False
        
    # 2. Keyword Presence
    lower_msg = user_message.lower()
    has_keyword = any(k in lower_msg for k in scientific_keywords)
    
    # 3. Explicit Greeting Exclusion
    greetings = ["hello", "hi", "good morning", "thanks", "thank you", "hey"]
    is_greeting = any(lower_msg.strip().startswith(g) for g in greetings)
    
    if is_greeting and not has_keyword:
        return False
        
    return True # Default to scientific to avoid false negatives

def verify_boundary_logic():
    print("🧪 Verifying Scientific Intent Logic (Isolated)...")
    passed = 0
    failed = 0
    
    for msg, expected in test_cases:
        result = _is_scientific_intent(msg)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | Input: '{msg}' -> Got: {result} (Expected: {expected})")
        sys.stdout.flush()
    
    print(f"\nResults: {passed} Passed, {failed} Failed")
    sys.stdout.flush()
    if failed > 0:
        raise AssertionError(f"{failed} test cases failed")

if __name__ == "__main__":
    verify_boundary_logic()
