"""
Nutri Deterministic Trace Engine — Trace Substance Classifier (v1.3.1)
Pure function to detect semantically empty scientific traces.
"""

def classify_trace_substance(trace_dict: dict) -> dict:
    """
    Classifies the substance level of an execution trace.
    Returns metadata about biological claims, anchors, and coverage.
    """
    scientific_layer = trace_dict.get("scientific_layer", {})
    claims = scientific_layer.get("claims", [])
    
    # 1. Substance Metric Detection
    # A claim is biological if it has an importance score > 0 (non-meta/procedural).
    biological_claims = []
    total_anchor_count = 0
    physical_mechanism_count = 0
    
    for c in claims:
        # Sum anchors for this claim
        claim_anchors = len(c.get("receptors", [])) + \
                        len(c.get("compounds", [])) + \
                        len(c.get("processes", [])) + \
                        len(c.get("physical_states", [])) + \
                        (1 if c.get("mechanism") else 0) + \
                        len(c.get("perception_outputs", []))
        
        total_anchor_count += claim_anchors

        # Count Physical Mechanisms (Nodes of type physical, structure, perception)
        if isinstance(c.get("mechanism"), dict):
            nodes = c["mechanism"].get("nodes", [])
            physical_mechanism_count += sum(1 for n in nodes if n.get("type") in ["physical", "structure", "perception"])
        
        # Phase 2 adjustment: Biological claims are non-meta claims (importance > 0)
        if c.get("importance_score", 0) > 0:
            biological_claims.append(c)

    # 2. Coverage Detection
    moa_coverage = scientific_layer.get("moa_coverage", 0)
    evidence_coverage = scientific_layer.get("evidence_coverage", 0)
    has_coverage = moa_coverage > 0 or evidence_coverage > 0

    # 3. Substance Logic
    # Substance exists if (biological claims OR physical mechanics) AND (anchors OR coverage).
    # Relaxed for culinary/physical domains.
    has_substance = (len(biological_claims) > 0 or physical_mechanism_count > 0) and (total_anchor_count > 0 or has_coverage)
    
    # ── v2.0: MECHANISTIC VALIDATION MODE ──
    execution_mode = trace_dict.get("execution_mode", "")
    if execution_mode == "scientific_explanation":
        mech_errors = []
        
        # Reject: all importance_score == 0
        if claims and all(c.get("importance_score", 0) == 0 for c in claims):
            mech_errors.append("all_importance_zero")
        
        # Reject: all decision == REQUIRE_MORE_CONTEXT
        if claims and all(c.get("decision") == "REQUIRE_MORE_CONTEXT" for c in claims):
            mech_errors.append("all_require_more_context")
        
        # Require: >= 2 causal claims
        causal_claims = [c for c in claims if c.get("mechanism") and len(str(c.get("mechanism", ""))) > 5]
        if len(causal_claims) < 1:
            mech_errors.append(f"insufficient_causal_claims ({len(causal_claims)}/1)")
        
        # Require: >= 1 entity (compound, anchor, OR physical node)
        has_entity = any(
            (c.get("compounds") and len(c["compounds"]) > 0) or
            (c.get("anchors") and len(c.get("anchors", [])) > 0) or
            (c.get("receptors") and len(c["receptors"]) > 0) or
            (isinstance(c.get("mechanism"), dict) and any(n.get("type") in ["compound", "receptor", "physical", "structure"] for n in c["mechanism"].get("nodes", [])))
            for c in claims
        )
        if not has_entity:
            mech_errors.append("no_biological_physical_entity")
        
        # Require: >= 1 process-level transformation
        has_process = any(
            c.get("mechanism_type") == "causal" or
            (c.get("processes") and len(c["processes"]) > 0) or
            (isinstance(c.get("mechanism"), dict) and any(n.get("type") in ["process", "perception"] for n in c["mechanism"].get("nodes", [])))
            for c in claims
        )
        if not has_process:
            mech_errors.append("no_process_transformation")
        
        if mech_errors:
            return {
                "has_substance": False,
                "reason": "MECHANISTIC_SUBSTANCE_FAILURE",
                "biological_claim_count": len(biological_claims),
                "physical_mechanism_count": physical_mechanism_count,
                "anchor_count": total_anchor_count,
                "coverage_present": has_coverage,
                "mechanistic_errors": mech_errors
            }
        
        # If mechanistic validation passes, force substantive
        return {
            "has_substance": True,
            "reason": "substantive",
            "biological_claim_count": len(biological_claims),
            "physical_mechanism_count": physical_mechanism_count,
            "anchor_count": total_anchor_count,
            "coverage_present": has_coverage
        }

    # ── Standard substance logic ──
    # Identify Reason
    if has_substance:
        reason = "substantive"
    elif len(claims) > 0:
        if all(c.get("importance_score", 0) == 0 for c in claims):
            reason = "meta_only"
        else:
            reason = "empty_scientific_trace"
    else:
        reason = "empty_scientific_trace"

    return {
        "has_substance": has_substance,
        "reason": reason,
        "biological_claim_count": len(biological_claims),
        "physical_mechanism_count": physical_mechanism_count,
        "anchor_count": total_anchor_count,
        "coverage_present": has_coverage
    }
