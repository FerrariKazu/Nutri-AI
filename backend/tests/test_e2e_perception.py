import sys
import os
import asyncio
import json
from types import SimpleNamespace

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.ranking_engine import MoleculeReceptorMapper, RankingEngine
from backend.utils.execution_trace import create_trace
from backend.claim_verifier import ClaimVerifier, ClaimVerification

async def test_e2e_data_emission():
    print("🧪 Simulating E2E Trace Generation for Perception UI...")
    
    # 1. Mock a claim as if it came from verification
    claim = SimpleNamespace(
        claim_id="C1",
        text="Caffeine triggers bitterness in coffee.",
        subject="caffeine",
        type="mechanistic"
    )
    
    # Simulate verifier
    verifier = ClaimVerifier()
    # Manual verification simulation to bypass actual PubChem network calls if possible
    # but let's just create a ClaimVerification record
    
    verification = ClaimVerification(
        claim_id=claim.claim_id,
        text=claim.text,
        subject=claim.subject,
        verified=True,
        source="pubchem",
        evidence={"cid": 2519},
        confidence=1.0,
        explanation="Verified via PubChem",
        domain="chemical",
        verification_level="direct",
        origin="enriched"
    )
    
    # Apply Tier 2 Enrichment (as done in ClaimVerifier)
    MoleculeReceptorMapper.enrich_perception(verification)
    verification.importance_score = RankingEngine.calculate_importance(verification)
    
    print(f"✅ Enrichment: Receptors={verification.receptors}, Sensory={verification.sensory_outcomes}")
    
    # 2. Create Trace and Set Claims
    trace = create_trace("test_session", "trace_123")
    trace.set_claims([verification])
    
    # 3. Get Serialized Dict
    trace_dict = trace.to_dict()
    
    # 4. Assertions
    generated_claim = trace_dict["claims"][0]
    print(f"📊 Generated Trace Claim: {json.dumps(generated_claim, indent=2)}")
    
    assert "receptors" in generated_claim
    assert "sensory_outcomes" in generated_claim
    assert len(generated_claim["receptors"]) > 0
    assert len(generated_claim["sensory_outcomes"]) > 0
    
    print("\n✨ BACKEND DATA EMISSION VERIFIED ✨")

if __name__ == "__main__":
    asyncio.run(test_e2e_data_emission())
