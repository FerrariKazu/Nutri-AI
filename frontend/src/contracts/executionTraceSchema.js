/**
 * executionTraceSchema.js
 * 
 * THE CONTRACT
 * Defines the exact shape of the backend AgentExecutionTrace.
 * 
 * @typedef {Object} Claim
 * @property {string} id
 * @property {string} text
 * @property {boolean} verified
 * @property {string} source
 * @property {number|null} confidence
 * @property {Object|null} mechanism
 * @property {string} decision
 * 
 * @typedef {Object} ExecutionTrace
 * @property {string} trace_id
 * @property {string} session_id
 * @property {number} schema_version
 * @property {'streaming'|'complete'|'failed'} status
 * @property {Object} integrity
 * @property {boolean} integrity.complete
 * @property {string[]} integrity.missing_segments
 * @property {Claim[]} claims
 * @property {number|null} confidence_score
 * @property {number|null} final_confidence
 * @property {number|null} moa_coverage
 * @property {boolean} pubchem_used
 * @property {string|null} pubchem_proof_hash
 * @property {number|null} duration_ms
 * @property {Object} tier3_risk_flags
 * @property {number} tier3_risk_flags_count
 * @property {number} tier3_applicability_match
 * @property {string[]} tier3_missing_context_fields
 * @property {Object} tier4_decision_changes
 * @property {number} tier4_session_age
 * @property {string[]} tier4_belief_revisions
 * @property {number} tier4_uncertainty_resolved_count
 * @property {boolean} tier4_saturation_triggered
 * @property {Object[]} invocations
 */

export const SCHEMA_VERSION = 2;

export const VALID_STATUSES = ['streaming', 'complete', 'failed'];

export const VALID_DECISIONS = ['ALLOW', 'WITHHOLD', 'REQUIRE_MORE_CONTEXT'];

export const VALID_CHANGE_TYPES = ['STABLE', 'UPGRADE', 'DOWNGRADE', 'NEW_DECISION', 'NEW'];
