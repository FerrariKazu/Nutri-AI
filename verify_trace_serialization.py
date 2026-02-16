import sys
import os
import logging
import uuid
import json

# Add backend to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)

from backend.intelligence.claim_enricher import enrich_claim
from backend.utils.execution_trace import AgentExecutionTrace

def test_trace_serialization():
    print("🚦 Testing Orchestrator Flow for Tier 2 Mechanism\n")
    
    # 1. Create Raw Claim (Parser Simulation)
    raw_claim = {
        "id": str(uuid.uuid4()),
        "statement": "Sucrose activates sweet receptors."
    }
    
    # 2. Add to Trace (Pre-Enrichment)
    print("🔹 Adding raw claim to AgentExecutionTrace...")
    trace = AgentExecutionTrace(session_id="test-session", trace_id="test-trace")
    trace.add_claims([raw_claim])
    
    # Verify pre-enrichment state
    print(f"   Trace claims count: {len(trace.claims)}")
    print(f"   Claim 0 mechanism present? {trace.claims[0].get('mechanism') is not None}")

    # 3. Enrich (Orchestrator Simulation)
    print("🔹 Running enrich_claims (Orchestrator Step)...")
    from backend.intelligence.claim_enricher import enrich_claims
    trace.claims = enrich_claims(trace.claims)
    
    # 4. Verify Post-Enrichment State
    print(f"   Trace claims count: {len(trace.claims)}")
    mech = trace.claims[0].get("mechanism")
    has_mech = mech is not None and len(mech.get("nodes", [])) > 0
    print(f"   Claim 0 mechanism present? {has_mech}")
    
    if not has_mech:
        print("❌ CRITICAL: Mechanism lost during enrichment assignment!")
        sys.exit(1)
        
    print(f"✅ Mechanism nodes: {len(mech['nodes'])}")

    # 5. Serialize
    print("🔹 Serializing trace...")
    try:
        data = trace.to_dict()
    except ValueError as e:
        print(f"❌ Serialization CRASHED: {e}")
        sys.exit(1)
        
    # 6. Verify Output
    serialized_claim = data["claims"][0]
    out_mech = serialized_claim.get("mechanism")
    
    if not out_mech:
        print("❌ Mechanism MISSING in serialized output!")
        sys.exit(1)
        
    print(f"✅ Serialized mechanism nodes: {len(out_mech.get('nodes', []))}")
    print(f"✅ HasTier2: {serialized_claim.get('hasTier2')}")
    
    # 7. Print JSON fragment for proof
    print("\n📜 JSON Fragment:")
    print(json.dumps(out_mech, indent=2))
    
    print("\n🏆 FULL PIPELINE VERIFIED!")

if __name__ == "__main__":
    test_trace_serialization()
