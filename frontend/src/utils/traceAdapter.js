/**
 * traceAdapter.js
 * 
 * ANTI-CORRUPTION LAYER (ACL) - v1.3 Refactor
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
 * Adapt V1.3 Schema (Strict)
 */
const adaptStrict = (rawTrace) => {
    // 1. Validate
    const { valid, status: validationStatus, errors, warnings } = validateTrace(rawTrace, import.meta.env.DEV);

    if (!valid || !rawTrace.epistemic_status) {
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
    const temporal = rawTrace.temporal_layer || {};
    const audit = rawTrace.system_audit || {};
    const profile = rawTrace.execution_profile || {};

    // 2. Map Claims (1:1 VERBATIM)
    const normalizedClaims = (scientific.claims || []).map(adaptClaimForUI);

    // 3. Construct Verified Object (Canonical UI Model)
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
            epistemic_basis: rawTrace.epistemic_basis || {},
            registrySnapshot: {
                version: scientific.registry_snapshot?.version,
                hash: scientific.registry_snapshot?.registry_hash,
                scope: scientific.registry_snapshot?.scope
                    ? (typeof scientific.registry_snapshot.scope === 'string'
                        ? JSON.parse(scientific.registry_snapshot.scope)
                        : scientific.registry_snapshot.scope)
                    : {}
            }
        },

        // Policy Authority Binding (Mapped from system_audit)
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
            chain: causality.chain || []
        },

        // Tier 4: Temporal Mapping
        temporal: {
            turn: strictVal(temporal.session_age),
            revisions: temporal.belief_revisions || [],
            resolvedUncertainties: strictVal(temporal.uncertainty_resolved_count),
            saturationTriggered: !!temporal.saturation_triggered,
            anchoring: temporal.session_age > 1 ? `Turn ${temporal.session_age}` : null
        },

        // Legacy compatibility shims (to be removed once components fully migrate)
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

        // If it's a contract violation (from throw), return a structured error
        if (e.message?.includes('CONTRACT_VIOLATION')) {
            return {
                adapter_status: "contract_violation",
                validation_errors: [e.message],
                _raw: rawTrace,
                claims: [],
                run_id: rawTrace.run_id || 'UNKNOWN'
            };
        }

        // Generic fallback for unexpected crashes
        return null;
    }
};
