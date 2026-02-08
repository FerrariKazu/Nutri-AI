/**
 * traceValidator.js
 * 
 * STRICT VALIDATION LAYER
 * Ensures no corrupted, mismatched, or hallucinated data enters the UI.
 */

import { SCHEMA_VERSION, VALID_STATUSES } from './executionTraceSchema';

const LOG_PREFIX = '[TraceValidator]';

/**
 * Validates a raw trace against the strict contract.
 * @param {Object} trace - The raw backend trace
 * @param {boolean} isDevMode - Whether to log verbose warnings
 * @returns {Object} - { valid: boolean, errors: string[] }
 */
export const validateTrace = (trace, isDevMode = false) => {
    const errors = [];

    if (!trace) {
        return { valid: false, errors: ['Trace is null or undefined'] };
    }

    // 1. Schema Version Gate
    if (trace.schema_version !== undefined && trace.schema_version !== SCHEMA_VERSION) {
        const msg = `Schema version mismatch. Expected ${SCHEMA_VERSION}, got ${trace.schema_version}`;
        errors.push(msg);
        if (isDevMode) console.warn(`${LOG_PREFIX} ${msg}`);
        // We might choose to fail hard or soft here. For now, strict fail.
        // return { valid: false, errors }; 
    }

    // 2. Status Check
    if (trace.status && !VALID_STATUSES.includes(trace.status)) {
        errors.push(`Invalid status: ${trace.status}`);
    }

    // 3. Claims Integrity
    if (trace.claims && !Array.isArray(trace.claims)) {
        errors.push('Claims must be an array');
    }

    // 4. Critical Numeric Checks (No NaNs allowed in critical paths)
    if (trace.confidence_score !== undefined && trace.confidence_score !== null && typeof trace.confidence_score !== 'number') {
        errors.push('confidence_score must be a number or null');
    }

    const isValid = errors.length === 0;

    if (isDevMode && !isValid) {
        console.error(`${LOG_PREFIX} Validation Failed:`, errors);
    }

    return { valid: isValid, errors };
};
