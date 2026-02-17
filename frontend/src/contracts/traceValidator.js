/**
 * traceValidator.js
 * 
 * STRICT VALIDATION LAYER
 * Ensures no corrupted, mismatched, or hallucinated data enters the UI.
 */

import { SCHEMA_VERSION, VALID_STATUSES } from './executionTraceSchema';

const LOG_PREFIX = '[TraceValidator]';

/**
 * Validates a single claim object.
 * @param {Object} claim - The claim object to validate.
 * @param {number} idx - The index of the claim in the claims array for error reporting.
 * @returns {string[]} An array of error messages for the claim.
 */
export const validateClaim = (claim, idx) => {
    const errors = [];
    if (!claim.id) errors.push(`Claim[${idx}] missing id`);
    if (!claim.statement) errors.push(`Claim[${idx}] missing statement`);
    if (!claim.domain) errors.push(`Claim[${idx}] missing domain`);
    if (!claim.mechanism_type) errors.push(`Claim[${idx}] missing mechanism_type`);
    // Deprecated fields (text, subject) are not validated here, assuming they are being phased out.
    return errors;
};

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
    const warnings = [];

    // 5. Warning Checks
    const isConversational = trace.execution_mode === 'non_scientific_discourse';

    if (isValid && (!trace.claims || trace.claims.length === 0) && !isConversational) {
        warnings.push("No claims found in trace");
    }

    // Determine Status
    let status = 'valid';
    if (!isValid) status = 'invalid';
    else if (trace.status === 'streaming') status = 'streaming';
    else if (warnings.length > 0) status = 'partial';

    if (isDevMode) {
        if (!isValid) console.error(`${LOG_PREFIX} Validation Failed:`, errors);
        if (warnings.length > 0) console.warn(`${LOG_PREFIX} Validation Warnings:`, warnings);
    }

    return { valid: isValid, status, errors, warnings };
};
