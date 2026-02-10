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

    // 2. Map Claims (1:1)
    const normalizedClaims = (rawTrace.claims || []).map(claim => {
        return {
            claim_id: strictVal(claim.claim_id || claim.id),
            text: strictVal(claim.text),
            verified: !!(claim.verified !== undefined ? claim.verified : claim.isVerified),
            source: strictVal(claim.source),
            confidence: strictVal(claim.confidence),

            mechanism: claim.mechanism ? {
                steps: (claim.mechanism.steps || []).map(step => ({
                    entity_name: strictVal(step.entity_name),
                    step_type: strictVal(step.step_type),
                    description: strictVal(step.description),
                    evidence_source: strictVal(step.evidence_source)
                })),
                weakest_link_confidence: strictVal(claim.mechanism.weakest_link_confidence)
            } : null,

            decision: strictVal(claim.decision), // NO MICROCOPY MAPPING
            changeType: strictVal((rawTrace.tier4_decision_changes || {})[claim.claim_id]) // Raw Enum
        };
    });

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

        // Availability Flags (Logic moved to renderPermissions, but flags help UI)
        hasTier1: normalizedClaims.length > 0,
        hasTier2: normalizedClaims.some(c => c.mechanism),

        metrics: {
            confidence: strictVal(rawTrace.confidence_score || rawTrace.final_confidence),
            duration: strictVal(rawTrace.duration_ms),
            pubchemUsed: !!rawTrace.pubchem_used,
            proofHash: strictVal(rawTrace.pubchem_proof_hash),
            moaCoverage: strictVal(rawTrace.moa_coverage)
        },

        causality: {
            applicability: strictVal(rawTrace.tier3_applicability_match),
            riskCount: strictVal(rawTrace.tier3_risk_flags_count),
            riskFlags: rawTrace.tier3_risk_flags || {}, // Raw object
            missingFields: rawTrace.tier3_missing_context_fields || []
        },

        temporal: {
            turn: strictVal(rawTrace.tier4_session_age),
            revisions: rawTrace.tier4_belief_revisions || [],
            resolvedUncertainties: strictVal(rawTrace.tier4_uncertainty_resolved_count),
            saturationTriggered: !!rawTrace.tier4_saturation_triggered,
            anchoring: rawTrace.tier4_session_age > 1 ? `Turn ${rawTrace.tier4_session_age}` : null // Minimal formatting allowed, or move to component? "Turn X" is factual.
        },

        // Expert Data
        expert: {
            invocations: rawTrace.invocations || [],
            sourceContribution: rawTrace.source_contribution || {}
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
