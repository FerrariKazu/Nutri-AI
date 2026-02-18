/**
 * executionTraceSchema.js
 * 
 * THE CONTRACT (v1.3)
 * Defines the exact shape of the backend AgentExecutionTrace.
 * 
 * @typedef {Object} Claim
 * @property {string} id
 * @property {string} statement
 * @property {string} domain
 * @property {string} mechanism_type
 * @property {string[]} compounds
 * @property {string[]} receptors
 * @property {Object[]} perception_outputs
 * @property {Object[]} evidence
 * @property {string} verification_level
 * @property {number} importance_score
 * @property {string|null} notes
 * @property {Object} mechanistic_anchors
 * 
 * @typedef {Object} ExecutionTrace
 * @property {string} id
 * @property {string} session_id
 * @property {string} run_id
 * @property {string} pipeline
 * @property {number} trace_schema_version
 * @property {string} execution_mode
 * @property {string} epistemic_status
 * @property {Object} epistemic_basis
 * @property {string} domain_type
 * @property {string} visibility_level
 * @property {number} domain_confidence
 * @property {number|null} epistemic_integrity_score
 * @property {string|null} downgrade_reason
 * @property {Object} confidence_breakdown
 * @property {Object} registry_snapshot
 * @property {Object} scientific_layer
 * @property {Object} policy_layer
 * @property {Object} causality_layer
 * @property {Object} temporal_layer
 * @property {Object|null} contextual_layer
 * @property {Object|null} surface_validation
 * @property {Object|null} contract_validation
 * @property {number} duration_ms
 * @property {string} status
 */

export const SCHEMA_VERSION = "1.3.1";

export const VALID_STATUSES = ['INIT', 'STREAMING', 'ENRICHING', 'VERIFIED', 'COMPLETE', 'ERROR'];

export const EPISTEMIC_COLORS = {
    'empirical_verified': '#22c55e', // Green
    'mechanistically_supported': '#10b981', // Emerald
    'convergent_support': '#3b82f6', // Blue
    'theoretical': '#f59e0b', // Amber
    'insufficient_evidence': '#ef4444', // Red
    'not_applicable': '#94a3b8', // Muted
    'fallback_execution': '#6366f1' // Indigo
};
