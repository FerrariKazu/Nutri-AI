import uuid
from backend.utils.execution_trace import AgentExecutionTrace, AgentInvocation
from types import SimpleNamespace

def test_telemetry_preservation():
    trace = AgentExecutionTrace(session_id="test_sess", trace_id="test_trace")
    
    # Create a claim object as SimpleNamespace (mimics orchestrator flow)
    claim_obj = SimpleNamespace(
        id="claim_1",
        statement="Test statement",
        domain="biological",
        importance_score=0.85,
        verified=True,
        verification_level="literature-backed",
        confidence=0.92,
        receptors=["TRPV1"],
        mechanism={"nodes": [{"id": "TRPV1", "type": "receptor"}], "edges": []}
    )
    
    # Add claim to trace
    trace.add_claims([claim_obj])
    
    # Convert to dict for serialization check
    trace_dict = trace.to_dict()
    claim_in_trace = trace_dict["claims"][0]
    
    print(f"Claim ID: {claim_in_trace['id']}")
    print(f"Verification Level: {claim_in_trace.get('verification_level')}")
    print(f"Confidence: {claim_in_trace.get('confidence')}")
    print(f"Importance Score: {claim_in_trace.get('importance_score')}")
    
    assert claim_in_trace.get('verification_level') == "literature-backed"
    assert claim_in_trace.get('confidence') == 0.92
    assert claim_in_trace.get('importance_score') == 0.85
    print("✅ Telemetry preservation verified for object inputs.")

if __name__ == "__main__":
    test_telemetry_preservation()
