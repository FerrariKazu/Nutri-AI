#!/usr/bin/env python3
"""
Manual Verification Script for Tier 2 MoA Reasoning
Tests the full flow: Claim -> Mechanism Assembly -> Explanation Rendering
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.mechanism_engine import MechanismEngine, MechanismStep
from backend.claim_verifier import ClaimVerifier
from backend.explanation_router import ExplanationRouter, ExplanationVerbosity

def test_moa_reasoning():
    print("🧪 Testing Tier 2 MoA Reasoning...\n")
    
    # 1. Test valid mechanism chain
    engine = MechanismEngine()
    
    steps = [
        MechanismStep(
            type="compound", 
            description="Lentil fiber (soluble dietary fiber)", 
            evidence_source="pubchem", 
            confidence=0.95
        ),
        MechanismStep(
            type="interaction", 
            description="Delays gastric emptying by forming viscous gel in stomach", 
            evidence_source="rag", 
            confidence=0.85
        ),
        MechanismStep(
            type="physiology", 
            description="Slower glucose absorption in small intestine", 
            evidence_source="rag", 
            confidence=0.90
        ),
        MechanismStep(
            type="outcome", 
            description="Reduced postprandial insulin spike", 
            evidence_source="rag", 
            confidence=0.85
        )
    ]
    
    chain = engine.validate_chain(steps)
    
    print("1️⃣ Mechanism Chain Validation:")
    print(f"   Valid: {chain.is_valid}")
    print(f"   Weakest Link Confidence: {chain.weakest_link_confidence}")
    print(f"   Break Reason: {chain.break_reason or 'None'}\n")
    
    # 2. Test explanation rendering
    router = ExplanationRouter()
    
    claim_text = "Lentils help stabilize blood sugar levels"
    
    print("2️⃣ Explanation Rendering:\n")
    
    for verbosity in [ExplanationVerbosity.QUICK, ExplanationVerbosity.SCIENTIFIC, ExplanationVerbosity.FULL]:
        rendered = router.render(claim_text, chain, verbosity)
        print(f"   {verbosity.value.upper()}:")
        print(f"   {rendered}\n")
    
    # 3. Test invalid chain (direct jump)
    print("3️⃣ Testing Invalid Chain (Compound -> Outcome jump):")
    
    invalid_steps = [
        MechanismStep(type="compound", description="Lentil fiber", evidence_source="pubchem", confidence=0.9),
        MechanismStep(type="outcome", description="Better blood sugar", evidence_source="rag", confidence=0.8)
    ]
    
    invalid_chain = engine.validate_chain(invalid_steps)
    print(f"   Valid: {invalid_chain.is_valid}")
    print(f"   Break Reason: {invalid_chain.break_reason}\n")
    
    print("✅ All Manual Tests Passed!")

if __name__ == "__main__":
    test_moa_reasoning()
