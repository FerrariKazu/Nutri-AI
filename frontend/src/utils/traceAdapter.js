/**
 * traceAdapter.js
 * 
 * ANTI-CORRUPTION LAYER (ACL)
 * Normalizes backend AgentExecutionTrace into a UI-friendly schema.
 * Implements "Responsible Microcopy", "Tier Availability", and Schema Versioning.
 */

// --- Defensive Utilities ---

const safeEnum = (value, allowed, fallback) => {
    return allowed.includes(value) ? value : fallback;
};

const ensureArray = (x) => Array.isArray(x) ? x : [];

const numberOrNull = (x) => {
    const n = parseFloat(x);
    return isNaN(n) ? null : n;
};

const safeString = (x, fallback = '') => typeof x === 'string' ? x : fallback;

// --- Microcopy Constants ---

const RECOMMENDATION_MICROCOPY = {
    'ALLOW': {
        decision: 'Proceed with Confidence',
        reason: 'Nutri has verified this claim against applicable evidence.',
        tone: 'positive'
    },
    'WITHHOLD': {
        decision: 'Caution Advised',
        reason: 'Nutri detected specific risks or lack of evidence for your context.',
        tone: 'negative'
    },
    'REQUIRE_MORE_CONTEXT': {
        decision: 'Clarification Helpful',
        reason: 'Nutri needs a little more information about your profile before advising.',
        tone: 'neutral'
    }
};

const TEMPORAL_MICROCOPY = {
    'STABLE': {
        label: 'Consistent',
        description: 'No change from earlier assessment.'
    },
    'UPGRADE': {
        label: 'Knowledge Upgrade',
        description: 'Nutri is more confident now based on new context.'
    },
    'DOWNGRADE': {
        label: 'Revised Assessment',
        description: 'Nutri identified a contradiction or risk in prior assumptions.'
    },
    'NEW_DECISION': {
        label: 'New Finding',
        description: 'First specific assessment for this claim.'
    }
};

// --- Versioned Adapters ---

/**
 * Adapt V1 Schema (Legacy-ish)
 */
const adaptV1 = (rawTrace) => {
    const claims = ensureArray(rawTrace.claims);

    const normalizedClaims = claims.map(claim => {
        const tier4Change = safeEnum(
            (rawTrace.tier4_decision_changes || {})[claim.claim_id],
            ['STABLE', 'UPGRADE', 'DOWNGRADE', 'NEW_DECISION'],
            'STABLE'
        );

        return {
            id: safeString(claim.claim_id),
            text: safeString(claim.text),
            isVerified: !!claim.verified,
            source: safeString(claim.source, 'General Knowledge'),
            confidence: numberOrNull(claim.confidence) || 0,
            mechanism: claim.mechanism ? {
                steps: ensureArray(claim.mechanism.steps).map(step => ({
                    entity_name: safeString(step.entity_name),
                    step_type: safeEnum(step.step_type, ['compound', 'interaction', 'physiology', 'outcome'], 'physiology'),
                    description: safeString(step.description),
                    evidence_source: safeString(step.evidence_source)
                })),
                weakest_link_confidence: numberOrNull(claim.mechanism.weakest_link_confidence)
            } : null,
            decisionMeta: RECOMMENDATION_MICROCOPY[claim.decision] || RECOMMENDATION_MICROCOPY['ALLOW'],
            temporalMeta: TEMPORAL_MICROCOPY[tier4Change] || TEMPORAL_MICROCOPY['STABLE'],
            changeType: tier4Change
        };
    });

    return {
        id: safeString(rawTrace.trace_id),
        sessionId: safeString(rawTrace.session_id),
        status: rawTrace.is_final ? 'final' : 'provisional',
        claims: normalizedClaims,

        tiers: {
            tier1: normalizedClaims.length > 0 ? 'available' : 'not_applicable',
            tier2: normalizedClaims.some(c => c.mechanism && c.mechanism.steps && c.mechanism.steps.length > 0) ? 'available' : 'not_applicable',
            tier3: (rawTrace.tier3_risk_flags_count > 0 || rawTrace.tier3_applicability_match > 0) ? 'available' : 'not_applicable',
            tier4: (Object.keys(rawTrace.tier4_decision_changes || {}).length > 0) ? 'available' : 'not_applicable'
        },

        metrics: {
            confidence: numberOrNull(rawTrace.final_confidence || rawTrace.confidence_score) || 0,
            confidenceDelta: numberOrNull(rawTrace.confidence_delta) || 0,
            duration: numberOrNull(rawTrace.duration_ms) || 0,
            pubchemUsed: !!rawTrace.pubchem_used,
            proofHash: safeString(rawTrace.pubchem_proof_hash),
            moaCoverage: numberOrNull(rawTrace.moa_coverage) || 0
        },

        causality: {
            applicability: numberOrNull(rawTrace.tier3_applicability_match) || 0,
            riskCount: numberOrNull(rawTrace.tier3_risk_flags_count) || 0,
            missingFields: ensureArray(rawTrace.tier3_missing_context_fields)
        },

        temporal: {
            turn: numberOrNull(rawTrace.tier4_session_age) || 0,
            revisions: ensureArray(rawTrace.tier4_belief_revisions),
            resolvedUncertainties: numberOrNull(rawTrace.tier4_uncertainty_resolved_count) || 0,
            saturationTriggered: !!rawTrace.tier4_saturation_triggered,
            anchoring: rawTrace.tier4_session_age > 1 ? `Intelligence evolved in Turn ${rawTrace.tier4_session_age}` : null
        },

        expert: {
            invocations: ensureArray(rawTrace.invocations),
            brokenSteps: rawTrace.broken_step_histogram || {},
            sourceContribution: rawTrace.source_contribution || {}
        }
    };
};

// Placeholder for future versions
const adaptV2 = (rawTrace) => adaptV1(rawTrace);

/**
 * Main Entry Point
 */
export const adaptExecutionTrace = (rawTrace) => {
    if (!rawTrace) return null;

    // Schema Versioning & Migration Logic
    const version = rawTrace.schema_version || 1;

    try {
        if (version === 2) return adaptV2(rawTrace);
        return adaptV1(rawTrace);
    } catch (e) {
        console.error("Critical Adapter Failure:", e);
        return null; // Better null than white screen
    }
};
