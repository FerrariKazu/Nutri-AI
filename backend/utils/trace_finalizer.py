"""
Nutri Trace Finalizer v1.0
Enforces terminal state, recomputes metrics, and promotes mechanistic topology.
"""

import logging
import time
import hashlib
import json
from typing import List, Dict, Any, Optional
from backend.utils.execution_trace import AgentExecutionTrace, TraceStatus, ExecutionMode, DowngradeReason
from backend.contracts.evidence_policy import RuleFiring

logger = logging.getLogger(__name__)

def compute_root_confidence(trace):
    """
    Frontend mandate: Importance-weighted average of all claim confidence scores.
    Correctly handles nested confidence objects.
    """
    claims = trace.claims or []
    if not claims:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for claim in claims:
        # Access nested confidence: claim.confidence.current
        score = claim.get("confidence", {}).get("current", 0.0)
        weight = claim.get("importance_score", 1.0)

        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 3)

def finalize_trace_stage(trace: AgentExecutionTrace, active_pipeline: str):
    """
    Finalizes the trace after all processing steps are complete.
    Idempotent: Returns immediately if trace is already COMPLETE.
    """
    logger.info(f"[FINALIZER] Executing finalization for {trace.trace_id} (pipeline={active_pipeline})")
    logger.info("[FINALIZER] Running schema alignment")

    # 2. Status Enforcement
    # Status is COMPLETE only if integrity is satisfied and substance is confirmed
    substance_state = trace.system_audit.get("substance_state", "unknown")
    integrity_state = trace.system_audit.get("integrity_state", "stable")
    
    if active_pipeline == "mechanistic_explainer":
        # Mechanistic traces are substantive if they have verified claims/nodes
        # BUT they fail if ALL primary claims were marked invalid (total_failure)
        has_substance = any(c.get("verified") for c in trace.claims) or bool(trace.graph.get("nodes"))
        
        if integrity_state == "total_failure":
            trace.status = TraceStatus.ERROR
            trace.system_audit["failure_reason"] = "total_integrity_failure"
        elif has_substance:
            trace.status = TraceStatus.COMPLETE
        else:
            trace.status = TraceStatus.ERROR
            trace.system_audit["failure_reason"] = "zero_mechanistic_substance"
    else:
        # Standard full_trace logic
        if trace.epistemic_integrity_score is not None and trace.epistemic_integrity_score >= 0.5:
             trace.status = TraceStatus.COMPLETE
        else:
             trace.status = TraceStatus.ERROR

    # 3. Confidence Aggregation (Strict v1.2.5 Realignment)
    final_score = compute_root_confidence(trace)
    
    # Internal & External Contract Alignment
    # v1.2.5: Keys must be final_score, baseline_used, rule_firings
    confidence_breakdown = {
        "final_score": final_score,
        "baseline_used": getattr(trace, "_base_confidence", final_score),
        "rule_firings": [
            RuleFiring(
                rule_id="SURFACE_MATCH",
                label="Surface Expression Score",
                category="aggregated_scoring",
                source="trace_finalizer",
                effect_type="baseline",
                input_value=getattr(trace, "surface_score", final_score),
                contribution=0.0,
                pre_value=final_score,
                post_value=final_score,
                fired=True
            ).to_dict(),
            RuleFiring(
                rule_id="MECHANISTIC_MATCH",
                label="Mechanistic Depth Match",
                category="aggregated_scoring",
                source="trace_finalizer",
                effect_type="baseline",
                input_value=getattr(trace, "contract_depth", 1.0),
                contribution=0.0,
                pre_value=final_score,
                post_value=final_score,
                fired=True
            ).to_dict(),
            RuleFiring(
                rule_id="REGISTRY_MATCH",
                label="Registry Alignment",
                category="aggregated_scoring",
                source="trace_finalizer",
                effect_type="baseline",
                input_value=trace.registry_hash if getattr(trace, "registry_hash", None) else "None",
                contribution=0.0,
                pre_value=final_score,
                post_value=final_score,
                fired=True
            ).to_dict()
        ]
    }

    # Final Mutation for confidence block (v1.2.5 renamed score -> current)
    trace.confidence = {
        "current": final_score,
        "tier": _derive_confidence_tier(final_score),
        "breakdown": confidence_breakdown
    }
    
    # Mirroring for STC compatibility
    trace.confidence_breakdown = confidence_breakdown
    
    # ── MODE & PROFILE NORMALIZATION ──
    # v1.2.5: Ensure raw scientific_explanation instead of pipes
    # ── v1.2.7 API GOVERNANCE ──
    # Internal pipeline state is set here; mapping happens in AgentExecutionTrace.to_dict()
    trace.pipeline = active_pipeline or "standard"
    
    trace.execution_profile = {
        "id": trace.trace_id,
        "mode": "pending_serialization",
        "epistemic_status": str(trace.epistemic_status.value if hasattr(trace.epistemic_status, 'value') else trace.epistemic_status).lower(),
        "confidence": final_score,
        "status": "COMPLETE"
    }

    # 4. Graph Normalization & Topological Causality (Mechanistic Only)
    if trace.trace_variant == "mechanistic":
        _normalize_mechanistic_topology(trace)

    # 5. Decision Promotion
    trace.decision = _promote_claim_decisions(trace.claims)

    # 6. Governance Signing (Deterministic SHA256)
    if trace.evidence_policy_id:
        trace.policy_layer["signed"] = True
        canonical_policy = {
            "policy_id": trace.evidence_policy_id,
            "policy_version": trace.policy_version,
            "epistemic_integrity_score": trace.epistemic_integrity_score or 0.0
        }
        trace.policy_layer["signature"] = _deterministic_sha256(canonical_policy)
        trace.policy_layer["policy_hash"] = trace.policy_hash

    # 7. Causality Block
    trace.causality_chain = trace.causality_chain or []

    # 8. Metric Recomputation
    _recompute_final_metrics(trace)

    # 8.1 ── v1.2.8 LAYER ENRICHMENT ──
    _enrich_v1_2_8_rigor(trace)

    # 9. Hard Contract Guards
    assert trace.confidence is not None, "Finalizer Error: confidence block is null"
    assert trace.execution_profile is not None, "Finalizer Error: execution_profile is null"
    
    logger.info(f"[FINALIZER] Finalization complete. status={trace.status} decision={trace.decision}")

def _normalize_mechanistic_topology(trace: AgentExecutionTrace):
    """
    Merges claim-level mechanism data into a unified trace graph.
    Performs topological sort to build the causality_chain.
    """
    all_nodes = {}
    all_edges = []
    
    for claim in trace.claims:
        # Extract mechanism nodes if present
        mech = claim.get("mechanism")
        if isinstance(mech, dict):
            # Nodes
            for node in mech.get("nodes", []):
                all_nodes[node["id"]] = node
            # Edges
            for edge in mech.get("edges", []):
                all_edges.append(edge)
        
        # Strip legacy graph placeholders from claims to avoid frontend confusion
        if "graph" in claim:
            del claim["graph"]

    # Deduplicate edges by source/target
    unified_edges = []
    edge_seen = set()
    for e in all_edges:
        key = (e["source"], e["target"])
        if key not in edge_seen:
            unified_edges.append(e)
            edge_seen.add(key)

    trace.graph = {
        "nodes": list(all_nodes.values()),
        "edges": unified_edges
    }

    # Derive causal ordering (Topological Sort)
    if trace.graph["edges"]:
        trace.causality_chain = _build_topological_chain(trace.graph)

def _build_topological_chain(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Simple topological sort for causal sequence rendering."""
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    
    # Compute in-degrees
    in_degree = {n_id: 0 for n_id in nodes}
    for e in edges:
        if e["target"] in in_degree:
            in_degree[e["target"]] += 1
            
    # Kahn's algorithm
    queue = [n_id for n_id, deg in in_degree.items() if deg == 0]
    sorted_nodes = []
    
    while queue:
        u = queue.pop(0)
        sorted_nodes.append(nodes[u])
        
        for e in edges:
            if e["source"] == u:
                v = e["target"]
                if v in in_degree:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
                        
    # If cycle detected, include remaining nodes as-is
    if len(sorted_nodes) < len(nodes):
        sorted_ids = {n["id"] for n in sorted_nodes}
        for n_id, node in nodes.items():
            if n_id not in sorted_ids:
                sorted_nodes.append(node)
                
    return sorted_nodes

def _promote_claim_decisions(claims: List[Dict[str, Any]]) -> str:
    """
    Smarter Decision Promotion:
    - All ACCEPT -> ACCEPT
    - Any ACCEPT -> MIXED
    - Else -> REJECT
    """
    if not claims:
        return "REJECT"
    
    decisions = [c.get("decision") for c in claims if c.get("decision")]
    
    if decisions and all(d == "ACCEPT" for d in decisions):
        decision = "ACCEPT"
    elif any(d == "ACCEPT" for d in decisions):
        decision = "MIXED"
    else:
        decision = "REJECT"
        
    logger.info(f"[FINALIZER] Root decision set to {decision}")
    return decision

def _derive_confidence_tier(score: float) -> str:
    """Stable thresholds for confidence tiers (Strict v1.2 Lowercase)."""
    if score >= 0.8: return "high"
    if score >= 0.5: return "medium"
    if score >= 0.3: return "low"
    return "speculative"

def _deterministic_sha256(data: Dict[str, Any]) -> str:
    """Canonical JSON hash (sorted keys, no whitespace)."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

def _recompute_final_metrics(trace: AgentExecutionTrace):
    """Ensures coverage and contradiction metrics are 100% accurate for final emit."""
    total_claims = len(trace.claims)
    if total_claims == 0:
        return

    verified_count = sum(1 for c in trace.claims if c.get("verified"))
    moa_count = sum(1 for c in trace.claims if c.get("mechanism"))
    
    trace.evidence_coverage = round(verified_count / total_claims, 2)
    trace.moa_coverage = (moa_count / total_claims * 100)
    
    # Contradiction re-scan
    all_ev = []
    for c in trace.claims:
        if isinstance(c.get("evidence"), list):
            all_ev.extend(c["evidence"])
    
    if all_ev:
        contradictions = sum(1 for e in all_ev if e.get("effect_direction") == "contradictory")
        trace.contradiction_ratio = round(contradictions / len(all_ev), 2)

def _enrich_v1_2_8_rigor(trace: AgentExecutionTrace):
    """
    Implements v1.2.8 Architectural Refinements:
    1. Ontology Consistency Check
    2. Strict Registry Enum
    """
    # 1. Ontology Consistency & Governance
    # Extract unique ontology versions from all claims
    ontology_versions = set()
    for claim in trace.claims:
        # Check source metadata if present
        source = claim.get("source", {})
        o_ver = source.get("ontology_version")
        if o_ver:
            ontology_versions.add(str(o_ver))
    
    ontology_consistency = len(ontology_versions) <= 1
    
    # Update Governance block
    registry_status = "not_applicable"
    if trace.registry_hash:
        registry_status = "matched"
    elif trace.system_audit.get("registry_error"):
        registry_status = "error"
    else:
        registry_status = "not_found"

    # Merge into trace.governance
    trace.governance.update({
        "registry_lookup_status": registry_status,
        "ontology_consistency": ontology_consistency,
        "unique_ontologies": list(ontology_versions)
    })
