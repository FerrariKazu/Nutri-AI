/**
 * renderPermissions.js
 * 
 * RENDERING PERMISSION MODEL
 * Central defines WHO gets to render WHAT.
 * 
 * Principles:
 * - Presence != Permission
 * - Data must be Valid AND Complete to render.
 * - Partial/Corrupt data -> Deny Permission (Render Unavailable state).
 */

export const renderPermissions = {
    /**
     * Can we render Tier 1 (Evidence)?
     * Req: Claims exist and are array.
     */
    canRenderTier1: (trace) => {
        if (!trace || !trace.claims) return false;
        return Array.isArray(trace.claims) && trace.claims.length > 0;
    },

    /**
     * Can we render Tier 2 (Mechanism)?
     * Req: At least one claim has a non-empty mechanism.
     */
    canRenderTier2: (trace) => {
        if (!trace || !trace.claims) return false;
        return trace.claims.some(c =>
            c.mechanism &&
            Array.isArray(c.mechanism.steps) &&
            c.mechanism.steps.length > 0
        );
    },

    /**
     * Can we render Tier 3 (Causality)?
     * Req: Causality metrics exist.
     */
    canRenderTier3: (trace) => {
        // We render Tier 3 container always if trace exists, but inner content depends on data.
        // This gate is for specific sub-sections or the whole card if we want to collapse empty tier 3.
        if (!trace) return false;

        // If all Tier 3 metrics are missing/zero/null, maybe we shouldn't render?
        // But Tier 3 includes risk flags. 
        // Let's check for existence of keys.
        return (
            trace.tier3_risk_flags_count !== undefined ||
            trace.tier3_applicability_match !== undefined ||
            (trace.tier3_missing_context_fields && trace.tier3_missing_context_fields.length > 0)
        );
    },

    /**
     * Can we render Tier 4 (Temporal)?
     * Req: Temporal fields exist.
     */
    canRenderTier4: (trace) => {
        if (!trace) return false;
        return (
            trace.tier4_session_age !== undefined ||
            trace.tier4_decision_changes !== undefined
        );
    }
};
