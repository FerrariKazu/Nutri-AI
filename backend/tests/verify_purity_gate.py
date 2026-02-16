import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.intelligence.claim_filter import is_mechanistic, create_fallback_claim

def test_purity_gate():
    print("--- Starting Purity Gate Verification ---")
    
    # 1. Test Rejection
    bad_claims = [
        {"text": "No specification provided for this recipe."},
        {"text": "I cannot generate a mechanism for this."},
        {"text": "Please provide more information about the dish."},
        {"text": "Insufficient data to analyze chemical structure."},
        {"text": "As a result of my internal processing, I am unable to answer."}
    ]
    
    print("\n[TEST] Administrative Pattern Rejection:")
    for c in bad_claims:
        result = is_mechanistic(c)
        print(f"  TEXT: {c['text'][:40]}... -> VALID: {result}")
        assert result is False, f"Failed to reject: {c['text']}"
    
    # 2. Test Validity
    good_claims = [
        {"text": "Caffeine binds to receptors.", "compounds": ["caffeine"]},
        {"text": "Activates TAS2R10.", "receptors": ["TAS2R10"]},
        {"text": "Bitterness increases.", "perception_outputs": [{"label": "bitter"}]},
        {"text": "Maillard reaction occurs.", "domain": "process"},
        {"text": "Solubility changes.", "domain": "physical"}
    ]
    
    print("\n[TEST] Mechanistic Content Validation:")
    for c in good_claims:
        result = is_mechanistic(c)
        print(f"  TEXT: {c['text'][:40]}... -> VALID: {result}")
        assert result is True, f"Failed to accept: {c['text']}"
        
    # 3. Test Fallback
    print("\n[TEST] Fallback Generation:")
    text_with_coffee = "I am a chef and I like coffee but I cannot tell you why."
    fallback = create_fallback_claim(text_with_coffee)
    print(f"  Input: '{text_with_coffee}'")
    print(f"  Fallback Statement: {fallback.get('statement')}")
    print(f"  Fallback Compounds: {fallback.get('compounds')}")
    assert "caffeine" in fallback.get("compounds", []), "Fallback failed to identify caffeine in coffee text"
    
    text_vague = "This is a generic query with no compounds."
    fallback_vague = create_fallback_claim(text_vague)
    print(f"  Input: '{text_vague}'")
    print(f"  Fallback Statement: {fallback_vague.get('statement')}")
    assert fallback_vague.get("domain") == "physical", "Generic fallback domain should be physical"

    print("\n--- Purity Gate Verification SUCCESSFUL ---")

if __name__ == "__main__":
    try:
        test_purity_gate()
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        sys.exit(1)
