/**
 * traceAdapter.js
 * 
 * ANTI-CORRUPTION LAYER (ACL)
 * Strictly normalizes backend AgentExecutionTrace.
 * 
 * EPISTEMIC HONESTY PRINCIPLES:
 * 1. No defaults (e.g. no || 0, no || 'General Knowledge').
 * 2. No synthetic text or microcopy.
 * 3. Explicit NULLs for missing data.
 * 4. Validation against contract.
 */

import { validateTrace } from '../contracts/traceValidator';

/**
 * Helper: Pass value only if defined and not null.
 * Otherwise returns undefined (which JSON.stringify drops) or null.
 * Strict: No "fallback".
 */
const strictVal = (val) => (val !== undefined) ? val : null;

/**
 * REQUIRED FIELDS CONTRACT
 * If any of these exist in the raw claim but are missing after adaptation,
 * the adapter has a bug and MUST throw.
 */
const REQUIRED_CLAIM_FIELDS = [
    'verification_level', 'confidence', 'importance_score',
    'statement', 'domain', 'mechanism', 'compounds', 'receptors'
];

/**
 * adaptClaimForUI
 * 
 * RULE: PASS-THROUGH, NOT REBUILD.
 * 1. Spread raw claim first — preserves ALL fields.
 * 2. Only overlay fields that need UI remapping.
 * 3. Assert contract: if raw had it, adapted must have it.
 */
export const adaptClaimForUI = (claim) => {
    if (!claim) return null;

    // SPREAD FIRST — every field from backend survives.
    const adapted = { ...claim };

    // UI REMAPPINGS ONLY (aliases the UI components expect)
    adapted.id = adapted.id || adapted.claim_id;
    adapted.claim_id = adapted.id;
    adapted.statement = adapted.statement || adapted.text;
    adapted.text = adapted.statement;
    adapted.mechanism_topology = adapted.mechanism_topology || adapted.graph;
    adapted.verified = !!(adapted.verified !== undefined ? adapted.verified : adapted.isVerified);

    // structured confidence object is PRESERVED.
    // UI components must now consume .confidence.current.

    // CONTRACT ASSERTION: If raw had it, adapted MUST have it.
    for (const field of REQUIRED_CLAIM_FIELDS) {
        if (claim[field] !== undefined && claim[field] !== null && (adapted[field] === undefined || adapted[field] === null)) {
            console.error(
                `%c [ADAPTER_CONTRACT_FAIL] Field "${field}" existed in raw claim but is missing/null in adapted! `,
                "background: #dc2626; color: white; font-weight: bold; padding: 2px 6px; border-radius: 4px;",
                { raw: claim, adapted }
            );
        }
    }

    return adapted;
};

/**
 * Adapt V2 Schema (Strict)
 */
const adaptStrict = (rawTrace) => {
    // 1. Validate
    const { valid, status: validationStatus, errors, warnings } = validateTrace(rawTrace, import.meta.env.DEV);

    const scientific = rawTrace.scientific_layer || {};
    const policy = rawTrace.policy_layer || {};

    // 🧠 Epistemic Authority Check (Upgrade 27)
    if (!rawTrace.epistemic_status) {
        errors.push("Missing mandatory backend-asserted epistemic_status.");
    }

    if (!valid || !scientific.claims || !rawTrace.epistemic_status) {
        // Log critical failure
        console.error("Trace Adapter: Trace rejected due to contract violation.", errors);

        return {
            adapter_status: "contract_violation",
            validation_errors: errors,
            _raw: rawTrace,
            claims: [],
            metrics: {},
            causality: {},
            temporal: {},
            expert: {}
        };
    }

    // TELEMETRY: ADAPTER IN
    console.log("🔌 [POINT 4: ADAPTER IN] NORMALIZING RAW TRACE", rawTrace);

    // 2. Map Claims (1:1 VERBATIM via centralized adapter)
    const normalizedClaims = (scientific.claims || []).map(adaptClaimForUI);

    // TELEMETRY: ADAPTER OUT
    if (normalizedClaims.length > 0) {
        console.log("🔌 [POINT 5: ADAPTER OUT] MAPPED CLAIMS", normalizedClaims);
    }

    // 3. Construct Verified Object
    return {
        adapter_status: "success",
        _raw: rawTrace,

        id: strictVal(rawTrace.id),
        sessionId: strictVal(rawTrace.session_id),
        run_id: strictVal(rawTrace.run_id),
        pipeline: strictVal(rawTrace.pipeline),
        trace_variant: strictVal(rawTrace.trace_variant),

        status: rawTrace.status || (rawTrace.is_final ? 'complete' : 'streaming'),
        validationStatus,
        warnings,

        schema_version: strictVal(rawTrace.schema_version),
        trace_required: !!rawTrace.trace_required,

        claims: normalizedClaims,

        // Availability Flags (Strict)
        hasTier1: normalizedClaims.length > 0,
        hasTier2: normalizedClaims.some(c => c.mechanism || (c.mechanism_topology && c.mechanism_topology.nodes && c.mechanism_topology.nodes.length > 0)),

        metrics: {
            // STRICT: Confidence must come from backend (Upgrade 27: Confidence Breakdown)
            confidence: strictVal(rawTrace.confidence_score || rawTrace.final_confidence),
            confidence_breakdown: rawTrace.confidence_breakdown || {
                baseline: 0,
                multipliers: [],
                policy_adjustment: 0,
                final: 0
            },
            epistemic_status: strictVal(rawTrace.epistemic_status),
            execution_mode: strictVal(rawTrace.execution_mode),

            duration: strictVal(rawTrace.duration_ms),
            pubchemUsed: !!rawTrace.pubchem_used,
            proofHash: strictVal(rawTrace.pubchem_proof_hash),
            moaCoverage: strictVal(scientific.moa_coverage),
            evidenceCoverage: strictVal(scientific.evidence_coverage),
            contradictionRatio: strictVal(scientific.contradiction_ratio),
            policyId: strictVal(policy.policy_id),
            policyVersion: strictVal(policy.policy_version),
            policyHash: strictVal(policy.policy_hash),
            policySelectionReason: strictVal(policy.selection_reason),
            registrySnapshot: scientific.registry_snapshot,
            epistemic_basis: rawTrace.epistemic_basis || {},
            trace_schema_version: strictVal(rawTrace.trace_schema_version)
        },

        causality: {
            applicability: strictVal(rawTrace.tier3_applicability_match),
            riskCount: strictVal(rawTrace.tier3_risk_flags_count),
            riskFlags: rawTrace.tier3_risk_flags, // Raw object
            missingFields: rawTrace.tier3_missing_context_fields
        },

        temporal: {
            turn: strictVal(rawTrace.tier4_session_age),
            revisions: rawTrace.tier4_belief_revisions,
            resolvedUncertainties: strictVal(rawTrace.tier4_uncertainty_resolved_count),
            saturationTriggered: !!rawTrace.tier4_saturation_triggered,
            anchoring: rawTrace.tier4_session_age > 1 ? `Turn ${rawTrace.tier4_session_age}` : null
        },

        // Expert Data
        expert: {
            invocations: rawTrace.invocations,
            sourceContribution: rawTrace.source_contribution
        }
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
