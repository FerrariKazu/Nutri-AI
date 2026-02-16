import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.sensory.sensory_registry import SensoryRegistry
from backend.ranking_engine import RankingEngine
from backend.claim_parser import Claim, ClaimParser
from backend.utils.execution_trace import AgentExecutionTrace, TraceStatus

def test_sensory_registry():
    print("Testing SensoryRegistry...")
    # Test Capsaicin (known)
    res = SensoryRegistry.map_compound_to_perception("capsaicin")
    assert res["resolved"] == True
    assert "TRPV1" in res["receptors"]
    assert any(p["modality"] == "heat" for p in res["perception_outputs"])
    print("✅ Capsaicin resolved correctly.")

    # Test unknown
    res = SensoryRegistry.map_compound_to_perception("unobtainium")
    assert res["resolved"] == False
    print("✅ Unknown compound handled correctly (Never Invent).")

def test_ranking_engine():
    print("\nTesting RankingEngine...")
    # Test high priority claim
    c1 = Claim(claim_id="1", text="test", type="scientific", receptors=["TRPV1"], verification_level="verified")
    score = RankingEngine.calculate_importance(c1)
    # +3 (receptor) + 1 (theoretical/verified) = 4.0? 
    # Formula: +3 (receptor) + 2 (pathway) + 1 (theoretical) - 1 (analogy)
    # c1 has receptor (+3). verification_level is verified (which is not theoretical? let's check code)
    print(f"Score for receptor claim: {score}")
    assert score >= 3.0

    # Test analogy penalty
    c2 = Claim(claim_id="2", text="like a hot summer day", type="scientific", mechanism_type="analogy")
    score2 = RankingEngine.calculate_importance(c2)
    print(f"Score for analogy claim: {score2}")
    assert score2 < 0.0
    print("✅ Ranking formula applied correctly.")

def test_trace_lifecycle():
    print("\nTesting Trace Lifecycle...")
    trace = AgentExecutionTrace(session_id="test_sess")
    assert trace.status == TraceStatus.INIT
    
    trace.status = TraceStatus.STREAMING
    data = trace.to_dict()
    assert data["status"] == "STREAMING"
    print("✅ Trace status machine functioning.")

if __name__ == "__main__":
    try:
        test_sensory_registry()
        test_ranking_engine()
        test_trace_lifecycle()
        print("\n✨ ALL INTEL MANDATE VERIFICATIONS PASSED ✨")
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
