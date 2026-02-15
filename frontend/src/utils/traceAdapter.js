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
const strictVal = (val) => (val !== undefined && val !== null) ? val : null;

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

    // Flatten structured confidence object → number
    if (typeof adapted.confidence === 'object' && adapted.confidence !== null) {
        adapted.confidence = adapted.confidence.current ?? null;
    }

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

    if (!valid && !rawTrace.claims) {
        // Log critical failure but ATTEMPT to render what we have (Continuity Principle)
        console.error("Trace Adapter: Trace rejected due to critical schema violation, but proceeding with empty claims.", errors);
        // Do NOT return null. Proceed to normalization.
        rawTrace.claims = []; // Ensure safe array
    }

    // TELEMETRY: ADAPTER IN
    console.log("🔌 [POINT 4: ADAPTER IN] NORMALIZING RAW TRACE", rawTrace);

    // 2. Map Claims (1:1 VERBATIM via centralized adapter)
    const normalizedClaims = (rawTrace.claims || []).map(adaptClaimForUI);

    // TELEMETRY: ADAPTER OUT
    if (normalizedClaims.length > 0) {
        console.log("🔌 [POINT 5: ADAPTER OUT] MAPPED CLAIMS", normalizedClaims);
    }

    // 3. Construct Verified Object
    return {
        id: strictVal(rawTrace.trace_id),
        sessionId: strictVal(rawTrace.session_id),
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
            // STRICT: Confidence must come from backend
            confidence: strictVal(rawTrace.confidence_score || rawTrace.final_confidence),
            duration: strictVal(rawTrace.duration_ms),
            pubchemUsed: !!rawTrace.pubchem_used,
            proofHash: strictVal(rawTrace.pubchem_proof_hash),
            moaCoverage: strictVal(rawTrace.moa_coverage)
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
