/**
 * traceValidator.js
 * 
 * STRICT VALIDATION LAYER - v1.3 Alignment
 * Ensures no corrupted, mismatched, or hallucinated data enters the UI.
 */

import { SCHEMA_VERSION } from './executionTraceSchema';

const LOG_PREFIX = '[TraceValidator]';

/**
 * Validates a raw trace against the strict v1.3 contract.
 */
export const validateTrace = (trace, isDevMode = false) => {
    const errors = [];

    if (!trace) {
        return { valid: false, errors: ['Trace is null or undefined'] };
    }

    // 1. Schema Version Gate (Hard Fail)
    if (trace.trace_schema_version !== SCHEMA_VERSION) {
        const msg = `Schema version mismatch. Expected ${SCHEMA_VERSION}, got ${trace.trace_schema_version || trace.schema_version}`;
        if (isDevMode) console.error(`${LOG_PREFIX} ${msg}`);
        throw new Error(msg);
    }

    // 2. Mandatory v1.2.8 Roots
    const mandatory = ['trace_schema_version', 'run_id', 'trace_id', 'id'];
    mandatory.forEach(field => {
        if (trace[field] === undefined || trace[field] === null) {
            errors.push(`Missing mandatory root field: ${field}`);
        }
    });

    // 2.5 Deep Structural Assertions
    if (!trace.execution_profile || typeof trace.execution_profile !== "object") {
        errors.push("Missing or invalid execution_profile block.");
    } else {
        if (typeof trace.execution_profile.id !== "string") errors.push("Missing execution_profile.id");
        if (typeof trace.execution_profile.mode !== "string") errors.push("Missing execution_profile.mode");
        if (typeof trace.execution_profile.epistemic_status !== "string") errors.push("Missing execution_profile.epistemic_status");

        const allowedModes = [
            "scientific_explanation", "conversation", "moderation", "technical",
            "full_trace", "error", "pending_serialization", "standard", "non_scientific_discourse"
        ];
        if (!allowedModes.includes(trace.execution_profile.mode)) {
            errors.push(`Invalid execution_profile.mode: ${trace.execution_profile.mode}`);
        }
    }

    if (!trace.confidence || typeof trace.confidence !== "object") {
        errors.push("Missing or invalid confidence block.");
    } else {
        if (typeof trace.confidence.current !== "number") errors.push("Missing or invalid confidence.current (must be number)");

        const strictTiers = ["speculative", "moderate", "strong", "verified", "invalid", "theoretical"];
        if (typeof trace.confidence.tier !== "string" || !strictTiers.includes(trace.confidence.tier)) {
            errors.push(`Invalid confidence.tier: ${trace.confidence.tier} - must be exact backend match.`);
        }

        if (!trace.confidence.breakdown || typeof trace.confidence.breakdown.final_score !== "number") {
            errors.push("Missing confidence.breakdown.final_score (must be number)");
        }
    }

    // 3. Mode-Specific Validation
    const effectiveMode = trace.execution_profile?.mode || '';
    const isConversational = effectiveMode === 'conversation' || trace.domain_type === 'contextual';

    if (!isConversational) {
        const scientific = trace.scientific_layer || {};
        if (!scientific.claims || !Array.isArray(scientific.claims)) {
            errors.push('Scientific trace missing claims array');
        }
    }

    const isValid = errors.length === 0;
    const warnings = [];

    if (isValid && !isConversational) {
        const scientific = trace.scientific_layer || {};
        if ((scientific.claims || []).length === 0) {
            warnings.push("No claims found in scientific trace");
        }
    }

    let status = 'valid';
    if (!isValid) status = 'invalid';
    else if (warnings.length > 0) status = 'partial';

    if (isDevMode && !isValid) {
        console.error(`${LOG_PREFIX} Validation Failed:`, errors);
    }

    return { valid: isValid, status, errors, warnings };
};
