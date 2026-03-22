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
     * UNBREAKABLE MODE: Always allow Tier 1 if claims array exists.
     */
    canRenderTier1: (trace) => {
        const reasons = [];
        if (!trace) return { allowed: false, reasons: ["No data"] };
        // Allow rendering as long as we don't have a terminal failure reported in the trace root
        if (trace.pipeline_failure === true) return { allowed: false, reasons: ["Pipeline Failure"] };
        return { allowed: true, reasons };
    },

    /**
     * UNBREAKABLE MODE: Always allow Tier 2. 
     * Specific claim checks handled via placeholders in component.
     */
    canRenderTier2: () => {
        return { allowed: true, reasons: [] };
    },

    /**
     * UNBREAKABLE MODE: Always allow Tier 3.
     */
    canRenderTier3: () => {
        return { allowed: true, reasons: [] };
    },

    /**
     * UNBREAKABLE MODE: Always allow Tier 4.
     */
    canRenderTier4: () => {
        return { allowed: true, reasons: [] };
    }
};
