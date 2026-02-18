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
            claims: []
        };
    }

    const scientific = rawTrace.scientific_layer || {};
    const policy = rawTrace.policy_layer || {};
    const causality = rawTrace.causality_layer || {};

    // 2. Map Claims (1:1 VERBATIM)
    const normalizedClaims = (scientific.claims || []).map(adaptClaimForUI);

    // 3. Construct Verified Object
    return {
        adapter_status: "success",
        _raw: rawTrace,

        id: strictVal(rawTrace.id),
        session_id: strictVal(rawTrace.session_id),
        run_id: strictVal(rawTrace.run_id),
        pipeline: strictVal(rawTrace.pipeline),

        status: strictVal(rawTrace.status),
        validationStatus,
        warnings,

        trace_schema_version: strictVal(rawTrace.trace_schema_version),
        execution_mode: strictVal(rawTrace.execution_mode),
        epistemic_status: strictVal(rawTrace.epistemic_status),
        epistemic_basis: rawTrace.epistemic_basis || {},

        domain_type: strictVal(rawTrace.domain_type),
        visibility_level: strictVal(rawTrace.visibility_level),
        domain_confidence: strictVal(rawTrace.domain_confidence),
        epistemic_integrity_score: strictVal(rawTrace.epistemic_integrity_score),
        downgrade_reason: strictVal(rawTrace.downgrade_reason),

        claims: normalizedClaims,

        metrics: {
            confidence_breakdown: rawTrace.confidence_breakdown || null,
            duration: strictVal(rawTrace.duration_ms),
            moa_coverage: strictVal(scientific.moa_coverage),
            evidence_coverage: strictVal(scientific.evidence_coverage),
            contradiction_ratio: strictVal(scientific.contradiction_ratio),
            registry_snapshot: scientific.registry_snapshot || {}
        },

        policy: {
            id: strictVal(policy.policy_id),
            version: strictVal(policy.policy_version),
            hash: strictVal(policy.policy_hash),
            reason: strictVal(policy.selection_reason)
        },

        causality: {
            applicability: strictVal(causality.tier3_applicability_match),
            riskCount: strictVal(causality.tier3_risk_flags_count),
            distribution: causality.tier3_recommendation_distribution
        },

        contextual: rawTrace.contextual_layer || null,
        surface_validation: rawTrace.surface_validation || null,
        contract_validation: rawTrace.contract_validation || null,
        system_audit: rawTrace.system_audit || {}
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
        console.error("Trace Adapter Crashed:", e);
        return null;
    }
};
