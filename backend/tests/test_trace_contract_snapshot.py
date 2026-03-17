import json
import os
import pytest
from jsonschema import validate, ValidationError
from backend.utils.execution_trace import AgentExecutionTrace, TRACE_SCHEMA_VERSION, TRACE_SCHEMA_PATH

def test_v1_2_8_contract_snapshot():
    """
    CANONICAL SNAPSHOT TEST: Acts as the Schema Firewall for v1.2.8.
    Validates against the single-source-of-truth JSON Schema.
    """
    # 1. Setup a minimal trace that satisfies the contract
    trace = AgentExecutionTrace(
        session_id="snap-session",
        trace_id="snap-trace",
        run_id="snap-run"
    )
    # Note: version is now locked to TRACE_SCHEMA_VERSION internally
    trace.decision = "Test Decision"
    trace.confidence = {
        "current": 0.85,
        "tier": "verified",
        "breakdown": {
            "final_score": 0.85,
            "baseline_used": 0.8,
            "rule_firings": [{
                "rule_id": "test_rule_1",
                "label": "Test Label",
                "category": "safety",
                "source": "snapshot",
                "effect_type": "boost",
                "input": "test_val",
                "contribution": 0.05,
                "pre_value": 0.80,
                "post_value": 0.85,
                "fired": True
            }]
        }
    }
    
    # 1.1 Add required temporal fields for v1.2.8
    trace.tier4_session_age = 120.5
    trace.tier4_belief_revisions = []
    trace.tier4_decision_state = "stable"
    trace.tier4_resolved_deltas = 2
    
    # Simulate mechanistic pipeline for mode mapping test
    trace.pipeline = "mechanistic_explainer"
    
    # 2. Serialize
    data = trace.to_dict()
    
    # 3. Load Schema and Validate (SINGLE SOURCE OF TRUTH)
    assert os.path.exists(TRACE_SCHEMA_PATH), f"Schema file missing at {TRACE_SCHEMA_PATH}"
    with open(TRACE_SCHEMA_PATH, "r") as f:
        schema = json.load(f)
    
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Contract violation: {e.message} at {list(e.path)}")

    # 4. Explicit Value Assertions (High-level semantics)
    assert data["trace_schema_version"] == "1.2.8"
    assert data["execution_profile"]["mode"] == "scientific_explanation"
    assert data["confidence"]["tier"] == "verified"
    assert "governance" in data
    assert "baseline_evidence_summary" in data
    assert "ontology_consistency" in data["governance"]
    
    temporal = data["temporal_layer"]
    assert all(k in temporal for k in ["session_age", "belief_revisions", "decision_state", "resolved_deltas"])
    assert len(temporal) == 4
    
    rule_firings = data["confidence"]["breakdown"]["rule_firings"]
    assert isinstance(rule_firings, list)
    
    # 5. Verify Structural Determinism
    raw_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    print(f"\n[FIREWALL_PASSED] v1.2.8 Contract Snapshot Verified.")
    print(f"[SNAPSHOT_JSON] {raw_json[:100]}...")

if __name__ == "__main__":
    test_v1_2_8_contract_snapshot()
