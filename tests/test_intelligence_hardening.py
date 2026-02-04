import pytest
from backend.claim_parser import ClaimParser
from backend.nutrition_uncertainty import UncertaintyCalculator

def test_claim_parser_splitting():
    parser = ClaimParser()
    text = "Koshari is high in fiber and supports digestion. It contains iron."
    claims = parser.parse(text)
    
    # Expected: 
    # 1. Koshari is high in fiber (quantitative)
    # 2. Koshari supports digestion (mechanistic)
    # 3. It contains iron (quantitative)
    
    texts = [c.text for c in claims]
    assert any("high in fiber" in t for t in texts)
    assert any("supports digestion" in t for t in texts)
    assert any("contains iron" in t for t in texts)
    
    # Check types
    types = [c.type for c in claims]
    assert "quantitative" in types
    assert "mechanistic" in types

def test_uncertainty_calculation():
    calc = UncertaintyCalculator()
    from types import SimpleNamespace
    
    # Mock Claims
    c1 = SimpleNamespace(claim_id="C1", confidence=1.0, verified=True)
    c2 = SimpleNamespace(claim_id="C2", confidence=0.8, verified=False)
    
    # Case 1: All high confidence
    res1 = calc.calculate([c1], [])
    assert res1.response_confidence == 1.0
    
    # Case 2: One unverified claim (weakest link)
    res2 = calc.calculate([c1, c2], [])
    # c1: 1.0, c2: 0.8 - 0.3 (unverified) = 0.5
    # response_confidence = 0.5
    assert res2.response_confidence == 0.5
    assert res2.weakest_link_id == "C2"
    
    # Case 3: Global drivers (portion ambiguity -10%)
    res3 = calc.calculate([c1], ["portion_ambiguity"])
    # 1.0 - 0.1 = 0.9
    assert res3.response_confidence == 0.9
