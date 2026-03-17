import json
import asyncio
from backend.utils.execution_trace import create_trace, EpistemicStatus, ExecutionMode
from backend.sensory.sensory_registry import SensoryRegistry

async def verify_epistemic_precision():
    print("🧪 Verifying Scientific Precision Refinements...")
    
    # 1. Test Registry Scope & Hash
    snapshot = SensoryRegistry.get_registry_snapshot()
    print(f"✅ Registry Snapshot: v{snapshot['version']}")
    print(f"   Full Hash: {snapshot['hash']}")
    assert len(snapshot['hash']) == 64, "Hash should be full SHA256 (64 chars)"
    assert snapshot['version'] == "1.3", "Registry version should be 1.3"
    assert "scope" in snapshot, "Missing scope in registry snapshot"
    print(f"   Scope: {snapshot['scope']['entity_counts']}")

    # 2. Test Trace Serialization with Refinements
    trace = create_trace("test_session", "tr_test_123")
    trace.run_id = "run_test_abc"
    trace.evidence_policy_id = "policy_test_v1"
    trace.policy_version = "1.0"
    
    # Simulate version locking
    trace.lock_versions(snapshot["version"], snapshot["hash"], "ONT-2026")
    
    # Use refined status
    trace.epistemic_status = EpistemicStatus.CONVERGENT_SUPPORT
    trace.epistemic_basis = {
        "evidence_present": True,
        "mechanism_complete": True,
        "registry_valid": True,
        "policy_intervention": False
    }
    trace.execution_mode = ExecutionMode.FULL_TRACE
    trace.confidence_breakdown = {
        "baseline": 0.9,
        "multipliers": [{"label": "RCT (n=128)", "value": 0.05}],
        "policy_adjustment": 0.0,
        "final": 0.95
    }
    trace.registry_scope = snapshot["scope"]
    
    trace_dict = trace.to_dict()
    print("✅ Trace Serialization (Precision v1.3):")
    print(f"   epistemic_status: {trace_dict.get('epistemic_status')}")
    print(f"   epistemic_basis: {json.dumps(trace_dict.get('epistemic_basis'))}")
    print(f"   trace_schema_version: {trace_dict.get('trace_schema_version')}")
    print(f"   confidence_breakdown: {json.dumps(trace_dict.get('confidence_breakdown'))}")

    assert trace_dict.get("epistemic_status") == "convergent_support"
    assert trace_dict.get("trace_schema_version") == "1.3"
    assert trace_dict.get("epistemic_basis", {}).get("evidence_present") is True
    assert "scientific_layer" in trace_dict
    assert trace_dict["scientific_layer"]["registry_snapshot"]["registry_hash"] == snapshot["hash"]

    print("\n✨ All scientific precision checks passed!")

if __name__ == "__main__":
    asyncio.run(verify_epistemic_precision())
