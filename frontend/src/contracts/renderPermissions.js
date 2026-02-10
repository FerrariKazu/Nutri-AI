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
        const reasons = [];
        if (!trace) { reasons.push("Trace missing"); return { allowed: false, reasons }; }
        if (!trace.claims || !Array.isArray(trace.claims) || trace.claims.length === 0) {
            reasons.push("No verification claims found");
            return { allowed: false, reasons };
        }
        return { allowed: true, reasons };
    },

    /**
     * Can we render Tier 2 (Mechanism)?
     * Req: At least one claim has a non-empty mechanism.
     */
    canRenderTier2: (trace) => {
        const reasons = [];
        if (!trace || !trace.claims) { reasons.push("No claims"); return { allowed: false, reasons }; }

        const hasMechanism = trace.claims.some(c =>
            c.mechanism &&
            Array.isArray(c.mechanism.steps) &&
            c.mechanism.steps.length > 0
        );

        if (!hasMechanism) reasons.push("No mechanism steps found in any claim");
        return { allowed: hasMechanism, reasons };
    },

    /**
     * Can we render Tier 3 (Causality)?
     * Req: Causality metrics exist.
     */
    canRenderTier3: (trace) => {
        const reasons = [];
        if (!trace) { reasons.push("Trace missing"); return { allowed: false, reasons }; }

        const hasMetrics = (
            trace.tier3_risk_flags_count !== undefined ||
            trace.tier3_applicability_match !== undefined ||
            (trace.tier3_missing_context_fields && trace.tier3_missing_context_fields.length > 0)
        );

        if (!hasMetrics) reasons.push("No causality metrics available");
        return { allowed: hasMetrics, reasons };
    },

    /**
     * Can we render Tier 4 (Temporal)?
     * Req: Temporal fields exist.
     */
    canRenderTier4: (trace) => {
        const reasons = [];
        if (!trace) { reasons.push("Trace missing"); return { allowed: false, reasons }; }

        const hasTemporal = (
            trace.tier4_session_age !== undefined ||
            trace.tier4_decision_changes !== undefined
        );

        if (!hasTemporal) reasons.push("No temporal data available");
        return { allowed: hasTemporal, reasons };
    }
};
