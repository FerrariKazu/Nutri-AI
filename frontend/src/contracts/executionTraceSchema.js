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
 * @typedef {Object} RuleFiring
 * @property {string} rule_id
 * @property {string} label
 * @property {string} category
 * @property {string} source
 * @property {string} effect_type
 * @property {any} input
 * @property {number} contribution
 * @property {number} pre_value
 * @property {number} post_value
 * @property {boolean} fired
 * 
 * @typedef {Object} GovernanceLayer
 * @property {string} policy_id
 * @property {string} ontology_version
 * @property {string} enrichment_version
 * @property {string} registry_lookup_status
 * @property {boolean} ontology_consistency
 * @property {string[]} unique_ontologies
 * @property {boolean} policy_signature_present
 * 
 * @typedef {Object} BaselineEvidenceSummary
 * @property {number} total_claims
 * @property {number} total_evidence_entries
 * @property {string} highest_study_type
 * @property {boolean} empirical_support_present
 * 
 * @typedef {Object} ExecutionTrace
 * @property {string} trace_schema_version
 * @property {Object} confidence
 * @property {Object} scientific_layer
 * @property {Object} execution_profile
 * @property {string} id
 * @property {string} trace_id
 * @property {string} session_id
 * @property {string} run_id
 * @property {string} pipeline
 * @property {string} decision
 * @property {string} epistemic_status
 * @property {string} execution_mode
 * @property {Object} governance
 * @property {Object} baseline_evidence_summary
 * @property {Object} temporal_layer
 * @property {Object} graph
 * @property {Object} system_audit
 */

export const SCHEMA_VERSION = "1.2.8";

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
