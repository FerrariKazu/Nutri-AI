import sys
import os
from types import SimpleNamespace

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.ranking_engine import RankingEngine, MoleculeReceptorMapper
from backend.mechanism_engine import MechanismChain

def test_ranking_and_perception():
    print("🧪 Testing Tier 2 Ranking & Perception...")
    
    # 1. Test MoleculeReceptorMapper
    claim1 = SimpleNamespace(
        claim_id="C1",
        subject="caffeine",
        text="Caffeine is bitter.",
        receptors=[],
        sensory_outcomes=[],
        property=None
    )
    
    MoleculeReceptorMapper.enrich_perception(claim1)
    
    assert "bitter" in claim1.sensory_outcomes
    assert claim1.receptors[0]["receptor"] == "TAS2R10"
    assert claim1.property == "Alkaloid"
    print("✅ MoleculeReceptorMapper: Direct match passed")
    
    # 2. Test RankingEngine
    # Case A: Low priority (heuristic, no mechanism)
    claim_low = SimpleNamespace(
        claim_id="C2",
        text="This food is good.",
        origin="model",
        verification_level="heuristic",
        mechanism=None
    )
    score_low = RankingEngine.calculate_importance(claim_low)
    
    # Case B: High priority (enriched, verified, mechanism, sensory)
    claim_high = SimpleNamespace(
        claim_id="C3",
        text="Quercetin provides a bitter notes.",
        subject="quercetin",
        origin="enriched",
        verification_level="direct",
        mechanism=SimpleNamespace(is_valid=True),
        domain="chemical"
    )
    score_high = RankingEngine.calculate_importance(claim_high)
    
    print(f"📊 Score Low: {score_low:.2f} | Score High: {score_high:.2f}")
    assert score_high > score_low
    assert score_high >= 0.8 # 0.1 (base) + 0.4 (moa) + 0.3 (direct) + 0.2 (sensory) + 0.1 (chem) = 1.0 (capped)
    print("✅ RankingEngine: Importance scoring passed")

if __name__ == "__main__":
    try:
        test_ranking_and_perception()
        print("\n✨ ALL TIER 2 BACKEND TESTS PASSED ✨")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
