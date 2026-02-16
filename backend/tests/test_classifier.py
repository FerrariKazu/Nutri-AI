import sys
import os

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.intelligence_classifier import is_intelligence_required

def test_classifier():
    print("🧪 Testing IntelligenceClassifier triggers...")
    
    # Cases that SHOULD trigger
    case1 = "Why is coffee bitter?"
    case2 = "How does caffeine affect me?"
    case3 = "Does this contain antioxidants?"
    case4 = "Tell me about the umami in this dish."
    
    assert is_intelligence_required(case1) == True, f"Failed Case 1: {case1}"
    assert is_intelligence_required(case2) == True, f"Failed Case 2: {case2}"
    assert is_intelligence_required(case3) == True, f"Failed Case 3: {case3}"
    assert is_intelligence_required(case4) == True, f"Failed Case 4: {case4}"
    
    # Case that SHOULD NOT trigger
    case5 = "What is the best way to cook eggs?"
    assert is_intelligence_required(case5) == False, f"Failed Case 5: {case5}"
    
    print("\n✨ ALL CLASSIFIER TESTS PASSED ✨")

if __name__ == "__main__":
    try:
        test_classifier()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
