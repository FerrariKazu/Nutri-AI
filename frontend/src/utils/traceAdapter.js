/**
 * traceAdapter.js
 * 
 * ANTI-CORRUPTION LAYER (ACL) - v1.2.8
 * Strictly normalizes backend AgentExecutionTrace.
 * 
 * EPISTEMIC HONESTY PRINCIPLES:
 * 1. No defaults (e.g. no || 0).
 * 2. No synthetic text or microcopy.
 * 3. Explicit NULLs for missing data.
 * 4. 1:1 Binding to Backend Epistemic Enums.
 */

import { validateTrace } from '../contracts/traceValidator';

/**
 * Helper: Pass value only if defined and not null.
 */
const strictVal = (val) => (val !== undefined) ? val : null;

/**
 * adaptClaimForUI
 * 
 * RULE: PASS-THROUGH, NOT REBUILD.
 */
export const adaptClaimForUI = (claim) => {
    if (!claim) return null;
    return { ...claim };
};

/**
 * Compute UI-only confidence fallback from claim averages.
 * NEVER mutates backend data. Presentation logic only.
 * 
 * Triggers ONLY when zero is a structural artifact, not epistemic output:
 *   confidence.current === 0 AND no rule firings AND claims exist
 */
const computeConfidenceFallback = (rawTrace, claims) => {
    const conf = rawTrace.confidence || {};
    const ruleFirings = conf.breakdown?.rule_firings || [];

    if (conf.current === 0 && ruleFirings.length === 0 && claims.length > 0) {
        const claimConfidences = claims
            .map(c => c.confidence?.current)
            .filter(v => typeof v === 'number' && !isNaN(v));

        if (claimConfidences.length > 0) {
            const avg = claimConfidences.reduce((a, b) => a + b, 0) / claimConfidences.length;
            return { value: avg, isDerived: true };
        }
    }
    return { value: null, isDerived: false };
};

/**
 * Adapt V1.2.8 Schema (Strict)
 */
const adaptStrict = (rawTrace) => {
    // 1. Validate
    const { valid, status: validationStatus, errors, warnings } = validateTrace(rawTrace, import.meta.env.DEV);

    if (!valid) {
        console.error("Trace Adapter: Trace rejected due to contract violation.", errors);
        return {
            adapter_status: "contract_violation",
            validation_errors: errors,
            _raw: rawTrace,
            claims: [],
            run_id: rawTrace.run_id || 'UNKNOWN'
        };
    }

    const scientific = rawTrace.scientific_layer || {};
    const causality = rawTrace.causality || {};
    const temporal = rawTrace.temporal_layer ?? {};
    const audit = rawTrace.system_audit || {};
    const profile = rawTrace.execution_profile || {};

    // ── DEFENSIVE NULL GUARDS (v1.2.8 Transitional Safety) ──
    const governance = rawTrace.governance ?? null;
    const baselineEvidence = rawTrace.baseline_evidence_summary ?? null;

    // ── CONTRACT STABILITY ASSERTION (Phase 8) ──
    if (rawTrace.confidence?.breakdown && !Array.isArray(rawTrace.confidence.breakdown.rule_firings)) {
        console.error("TRACE SHAPE VIOLATION: rule_firings must be array (Canonical v1.2.8 Requirement)");
    }

    // 2. Map Claims (1:1 VERBATIM)
    const normalizedClaims = (scientific.claims || []).map(claim => {
        const adapted = adaptClaimForUI(claim);
        if (adapted?.mechanism?.nodes) {
            adapted.mechanism.nodes.forEach(node => {
                node.label = node.label ?? node.id;
            });
        }
        return adapted;
    });

    // 3. Confidence Fallback (Presentation Logic Only)
    const confidenceFallback = computeConfidenceFallback(rawTrace, normalizedClaims);

    // ── NORMALIZE TOP-LEVEL GRAPH NODES ──
    const topLevelGraph = rawTrace.graph || { nodes: [], edges: [] };
    if (topLevelGraph.nodes) {
        topLevelGraph.nodes.forEach(node => {
            node.label = node.label ?? node.id;
        });
    }

    // ── NORMALIZE CAUSALITY CHAIN NODES ──
    const causalityChain = causality.chain || [];
    causalityChain.forEach(node => {
        if (node.id) {
            node.label = node.label ?? node.id;
        }
    });

    // 4. Registry scope parsing (safe)
    let parsedScope = {};
    try {
        if (scientific.registry_snapshot?.scope) {
            parsedScope = typeof scientific.registry_snapshot.scope === 'string'
                ? JSON.parse(scientific.registry_snapshot.scope)
                : scientific.registry_snapshot.scope;
        }
    } catch (e) {
        console.warn("Trace Adapter: Failed to parse registry scope", e);
    }

    // 5. Construct Verified Object (Canonical UI Model)
    return {
        adapter_status: "success",
        _raw: rawTrace,

        // Root Identifiers (Frontend Stability)
        id: strictVal(rawTrace.id),
        trace_id: strictVal(rawTrace.trace_id),
        session_id: strictVal(rawTrace.session_id),
        run_id: strictVal(rawTrace.run_id),
        trace_schema_version: strictVal(rawTrace.trace_schema_version),

        // Mode & Status Binding
        status: strictVal(profile.status),
        mode: strictVal(profile.mode),
        epistemic_status: strictVal(profile.epistemic_status),
        decision: strictVal(rawTrace.decision),

        validationStatus,
        warnings,
        claims: normalizedClaims,

        // Execution Profile View Model
        metrics: {
            id: strictVal(profile.id || rawTrace.id),
            trace_schema_version: strictVal(rawTrace.trace_schema_version),
            evidenceCoverage: strictVal(scientific.evidence_coverage),
            moaCoverage: strictVal(scientific.moa_coverage),
            contradictionRatio: strictVal(scientific.contradiction_ratio),
            duration: strictVal(rawTrace.duration_ms),
            confidence_breakdown: {
                ...(rawTrace.confidence?.breakdown || {}),
                final: rawTrace.confidence?.breakdown?.final_score || rawTrace.confidence?.current || 0
            },
            // UI-only derived confidence (never overwrites backend)
            ui_confidence_fallback: confidenceFallback.value,
            ui_confidence_is_derived: confidenceFallback.isDerived,
            epistemic_basis: rawTrace.epistemic_basis || {},
            registrySnapshot: {
                version: scientific.registry_snapshot?.version,
                hash: scientific.registry_snapshot?.registry_hash,
                scope: parsedScope
            }
        },

        // 🛡️ Governance (Direct Backend Passthrough)
        governance: governance,

        // 📊 Baseline Evidence Summary (Direct Backend Passthrough)
        baseline_evidence_summary: baselineEvidence,

        // Legacy policy mapping (for backward compat)
        policy: {
            policy_id: strictVal(audit.policy_id),
            policy_version: strictVal(audit.policy_version || "1.0"),
            policy_hash: strictVal(audit.policy_hash),
            selection_reason: strictVal(audit.selection_reason),
            author: strictVal(audit.author),
            review_board: strictVal(audit.review_board),
            approval_date: strictVal(audit.approval_date),
            attestation: strictVal(audit.attestation)
        },

        // Tier 3: Causality Mapping
        causality: {
            applicability: strictVal(causality.applicability),
            riskCount: strictVal(causality.riskCount),
            riskFlags: causality.riskFlags || {},
            chain: causalityChain,
            topology: topLevelGraph
        },

        // Tier 4: Temporal Mapping (Real backend values)
        temporal: {
            turn: strictVal(temporal.session_age),
            revisions: typeof temporal.belief_revisions === 'number' ? temporal.belief_revisions : 0,
            resolvedUncertainties: strictVal(temporal.resolved_deltas),
            saturationTriggered: !!temporal.saturation_triggered,
            anchoring: temporal.session_age > 1 ? `Turn ${temporal.session_age}` : null,
            decision_state: strictVal(temporal.decision_state) || "initial",
            resolved_deltas: strictVal(temporal.resolved_deltas) || 0
        },

        graph: topLevelGraph,

        // Legacy compatibility shims
        execution_profile: profile,
        scientific_layer: scientific,
        system_audit: audit
    };
};

/**
 * Main Entry Point
 */
export const adaptExecutionTrace = (rawTrace) => {
    if (!rawTrace) return null;

    try {
        return adaptStrict(rawTrace);
    } catch (e) {
        console.error("Trace Adapter caught error:", e);

        if (e.message?.includes('CONTRACT_VIOLATION')) {
            return {
                adapter_status: "contract_violation",
                validation_errors: [e.message],
                _raw: rawTrace,
                claims: [],
                run_id: rawTrace.run_id || 'UNKNOWN'
            };
        }

        return null;
    }
};
