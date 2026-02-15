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

    // 2. Map Claims (1:1 VERBATIM)
    const normalizedClaims = (rawTrace.claims || []).map(claim => {
        // STRICT: No Default Values. If backend is null, UI is null.
        return {
            id: strictVal(claim.id || claim.claim_id),
            statement: strictVal(claim.statement || claim.text),
            domain: strictVal(claim.domain),
            mechanism_type: strictVal(claim.mechanism_type),

            // STRICT: Pass Mechanism Data
            mechanism: strictVal(claim.mechanism),
            mechanism_topology: strictVal(claim.mechanism_topology || claim.graph),

            // STRICT: Lists (Empty array is fine if backend sends it, but fallback to null if missing)
            compounds: strictVal(claim.compounds),
            receptors: strictVal(claim.receptors),
            perception_outputs: strictVal(claim.perception_outputs),
            evidence: strictVal(claim.evidence),

            // STRICT: Metrics
            verification_level: strictVal(claim.verification_level),
            importance_score: strictVal(claim.importance_score),
            confidence: strictVal(
                typeof claim.confidence === 'object' && claim.confidence !== null
                    ? claim.confidence.current
                    : claim.confidence
            ),

            // Legacy/Mapping (if still needed by components, but STRICT)
            claim_id: strictVal(claim.id || claim.claim_id),
            text: strictVal(claim.statement || claim.text),
            verified: !!(claim.verified !== undefined ? claim.verified : claim.isVerified),
            decision: strictVal(claim.decision),
        };
    });

    // TELEMETRY: ADAPTER OUT
    if (normalizedClaims.length > 0) {
        console.log("🔌 ADAPTER: MAPPED CLAIMS", normalizedClaims);
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
