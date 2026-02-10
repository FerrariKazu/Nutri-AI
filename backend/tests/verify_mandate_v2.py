import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.intelligence_classifier import IntelligenceClassifier
from backend.sensory.sensory_registry import SensoryRegistry

def test_classifier():
    print("\n🔬 Testing Intelligence Classifier...")
    
    scenarios = [
        ("How does capsaicin work?", True),
        ("Explain the reaction between acid and baking soda", True),
        ("What triggers the TRPV1 receptor?", True),
        ("Why is my bread not rising?", True),
        ("Tell me a joke", False),
        ("Hello", False),
        ("Who are you?", False),
        ("fermentation process", True),
        ("add salt to taste", True), # "salt" is a compound, so trace is acceptable/expected now
        ("Cut the carrots into cubes", False) # Purely procedural
    ]
    
    passed = 0
    for query, expected in scenarios:
        result = IntelligenceClassifier.requires_trace(query)
        status = "✅" if result == expected else "❌"
        if result != expected:
            print(f"{status} Query: '{query}' | Expected: {expected} | Got: {result}")
        else:
            passed += 1
            
    print(f"Classifier Results: {passed}/{len(scenarios)} passed")
    if passed != len(scenarios):
        raise Exception("Classifier verification failed")

def test_registry_expansion():
    print("\n🧬 Testing Sensory Registry Expansion...")
    
    # Test cases for new compounds
    test_compounds = [
        ("caffeine", "TAS2R10"),
        ("allyl_isothiocyanate", "TRPA1"),
        ("inosine_monophosphate", "TAS1R1"),
        ("saccharin", "TAS1R2"),
        ("lactic_acid", "OTOP1")
    ]
    
    passed = 0
    for compound, expected_receptor in test_compounds:
        result = SensoryRegistry.map_compound_to_perception(compound)
        
        if not result["resolved"]:
            print(f"❌ {compound}: Not resolved")
            continue
            
        receptors = result["receptors"]
        if expected_receptor in receptors:
            # print(f"✅ {compound} -> {receptors}")
            passed += 1
        else:
            print(f"❌ {compound}: Expected {expected_receptor}, got {receptors}")
            
    print(f"Registry Results: {passed}/{len(test_compounds)} compound checks passed")
    if passed != len(test_compounds):
        raise Exception("Registry verification failed")

if __name__ == "__main__":
    try:
        test_classifier()
        test_registry_expansion()
        print("\n✨ ALL MANDATE V2 VERIFICATIONS PASSED ✨")
    except Exception as e:
        print(f"\n💀 VERIFICATION FAILED: {e}")
        sys.exit(1)
