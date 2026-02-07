import pytest
from backend.explanation_router import ExplanationRouter, ExplanationVerbosity
from backend.decision_comparator import DecisionDelta

def test_memory_compression_stable():
    router = ExplanationRouter()
    
    delta = DecisionDelta(
        claim_id="test",
        change_type="STABLE",
        previous="allow",
        current="allow",
        reason="Reason",
        turn_changed=3
    )
    
    rendered = router.render(
        text="Lentils are good",
        mechanism=None,
        verbosity=ExplanationVerbosity.QUICK,
        decision_delta=delta
    )
    
    assert "assessment remains stable" in rendered
    assert "mechanism" not in rendered.lower() # Since we don't pass mechanism details here anyway, but check length
    assert len(rendered) < 100

def test_memory_compression_full_verbosity_bypass():
    # If user asks for FULL details, don't compress
    router = ExplanationRouter()
    delta = DecisionDelta(claim_id="t", change_type="STABLE", previous="allow", current="allow", reason="R", turn_changed=1)
    
    # Mocking mechanism rendering would be complex, but we can check it doesn't return the stability message alone
    # We'll just verify it doesn't return the compression string if verbosity is FULL
    rendered = router.render(
        text="Text",
        mechanism=None,
        verbosity=ExplanationVerbosity.FULL,
        decision_delta=delta
    )
    assert "assessment remains stable" not in rendered
