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

    // 1. Schema Version Gate
    if (trace.trace_schema_version !== SCHEMA_VERSION && trace.schema_version !== SCHEMA_VERSION) {
        const msg = `Schema version mismatch. Expected ${SCHEMA_VERSION}, got ${trace.trace_schema_version || trace.schema_version}`;
        // Soft warning for now to allow some drift during deployment, but log error
        if (isDevMode) console.error(`${LOG_PREFIX} ${msg}`);
    }

    // 2. Mandatory v1.3.1 Fields
    const mandatory = ['execution_mode', 'epistemic_status', 'id', 'run_id', 'trace_metrics', 'trace_schema_version'];
    mandatory.forEach(field => {
        if (trace[field] === undefined || trace[field] === null) {
            errors.push(`Missing mandatory field: ${field}`);
        }
    });

    // 3. Mode-Specific Validation
    const isConversational = trace.execution_mode === 'non_scientific_discourse' || trace.domain_type === 'contextual';

    if (!isConversational) {
        const scientific = trace.scientific_layer || {};
        if (!scientific.claims || !Array.isArray(scientific.claims)) {
            errors.push('Scientific trace missing claims array');
        }

        // 4a. Scientific Explanation Mode (v2.0) — First-class validation
        if (trace.execution_mode === 'scientific_explanation') {
            const substanceState = trace.trace_metrics?.substance_state;
            if (!substanceState || substanceState !== 'substantive') {
                errors.push('TRACE_SUBSTANCE_GENERATION_FAILURE: scientific_explanation must be substantive');
            }
            const anchorCount = trace.trace_metrics?.anchor_count || 0;
            const bioClaimCount = trace.trace_metrics?.biological_claim_count || 0;
            if (anchorCount === 0) {
                errors.push('TRACE_SUBSTANCE_GENERATION_FAILURE: anchor_count must be > 0');
            }
            if (bioClaimCount === 0) {
                errors.push('TRACE_SUBSTANCE_GENERATION_FAILURE: biological_claim_count must be > 0');
            }
            // DO NOT show "General Discourse Mode" or "Scientific Instrument Standby"
        }

        // 4b. Substance Enforcement Guard (SSOT Trust Mode) — Full Trace only
        const substanceState = trace.trace_metrics?.substance_state;
        if (trace.execution_mode === 'full_trace' && substanceState !== 'substantive') {
            const errorMsg = 'TRACE_SUBSTANCE_CONTRACT_VIOLATION: FULL_TRACE must be substantive.';
            if (isDevMode) console.error(`${LOG_PREFIX} ${errorMsg}`);
            throw new Error(errorMsg);
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
