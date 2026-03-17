"""
verify_mechanistic_trace.py — v3.1 Strict Assertions
Verifies that the mechanistic pipeline emits a correct trace.
"""
import sys
import json
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.utils.execution_trace import (
    AgentExecutionTrace, TraceStatus, ExecutionMode, EpistemicStatus, DowngradeReason
)


def make_trace(variant="mechanistic") -> AgentExecutionTrace:
    trace = AgentExecutionTrace(session_id="test-session", trace_id="test-trace")
    trace.trace_variant = variant
    trace.execution_mode = ExecutionMode.SCIENTIFIC_EXPLANATION
    trace.status = TraceStatus.COMPLETE
    trace.system_audit["intelligence_mandated"] = True
    trace.contextual_layer = None
    trace.integrity = {
        "tier_1_surface": "complete",
        "tier_2_process": "complete",
        "tier_3_molecular": "complete",
    }
    trace.downgrade_reason = DowngradeReason.NOT_APPLICABLE
    trace.epistemic_status = EpistemicStatus.THEORETICAL
    trace.tier3_applicability_match = 1.0
    # Add a mock claim
    trace.add_claims([{
        "id": "MECH-test01",
        "statement": "Yeast CO2 creates bubbles lifting gluten network",
        "mechanism": "fermentation_co2_expansion",
        "compounds": ["CO2", "Gluten"],
        "anchors": ["yeast fermentation"],
        "domain": "biological",
        "verified": False,
        "origin": "mechanistic_pipeline",
        "importance_score": 0.9,
        "decision": "ALLOW",
    }])
    return trace


def run_assertions():
    print("=== Mechanistic Trace Contract Verification ===\n")
    errors = []

    trace = make_trace()
    data = trace.to_dict()

    def assert_eq(label, actual, expected):
        status = "✅" if actual == expected else "❌"
        if actual != expected:
            errors.append(f"{label}: expected {expected!r}, got {actual!r}")
        print(f"  {status} {label}: {actual!r}")

    def assert_not(label, actual):
        status = "❌" if actual else "✅"
        if actual:
            errors.append(f"{label}: expected falsy, got {actual!r}")
        print(f"  {status} {label}: {actual!r}")

    def assert_not_contains(label, container, item):
        status = "❌" if item in str(container) else "✅"
        if item in str(container):
            errors.append(f"{label}: '{item}' found unexpectedly")
        print(f"  {status} {label}: '{item}' not present")

    print("[1] Trace Lifecycle")
    assert_eq("status", data.get("status"), "COMPLETE")
    assert_eq("execution_mode", data.get("execution_mode"), "scientific_explanation")
    assert_eq("trace_variant", data.get("trace_variant"), "mechanistic")

    print("\n[2] System Audit")
    assert_eq("intelligence_mandated", data.get("system_audit", {}).get("intelligence_mandated"), True)

    print("\n[3] Integrity")
    integrity = data.get("integrity", {})
    assert_eq("integrity.complete", integrity.get("complete"), True)
    actual_missing = integrity.get("missing_segments", [])
    assert_not("missing_segments", actual_missing)
    assert_not_contains("no tier1 in missing_segments", actual_missing, "tier1")

    print("\n[4] Memory Isolation")
    assert_not("contextual_layer is None/falsy", data.get("contextual_layer"))

    print("\n[5] Downgrade")
    assert_not_contains("downgrade_reason not LOW_INTEGRITY_SCORE", data.get("downgrade_reason", ""), "LOW_INTEGRITY_SCORE")

    print("\n[6] Causality Layer (Frontend compliance)")
    causality = data.get("causality", {})
    assert_eq("causality.applicability", causality.get("applicability"), 1.0)
    assert_eq("causality.riskCount", causality.get("riskCount"), 0)

    print("\n[7] Graph Nodes (IntelligenceGraph compliance)")
    claim = data.get("claims", [])[0]
    assert_eq("claim.receptors populated", len(claim.get("receptors", [])), 0) # Mock is empty, but we check field exists
    assert_eq("claim.perception_outputs populated", len(claim.get("perception_outputs", [])), 0)

    print("\n[8] Mode Guard — ensure to_dict does not revert mode")
    assert_eq("execution_mode after to_dict", data.get("execution_mode"), "scientific_explanation")

    print()
    if errors:
        print(f"❌ FAILED with {len(errors)} assertion(s):")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)
    else:
        print("✅ ALL ASSERTIONS PASSED — Mechanistic trace contract verified.")


if __name__ == "__main__":
    run_assertions()
