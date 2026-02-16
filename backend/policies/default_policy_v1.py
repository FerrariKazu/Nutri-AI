"""
Default Evidence Policy v1.0 — NUTRI_EVIDENCE_V1
First concrete policy artifact for Nutri.

All values previously hardcoded in WeightingEngine are now declared here.
This is the ONLY place where scoring weights, thresholds, and penalties exist.
"""

from backend.contracts.evidence_policy import EvidencePolicy, PolicyRule

NUTRI_EVIDENCE_V1 = EvidencePolicy(
    policy_id="NUTRI_EVIDENCE_V1",
    version="1.0",
    published_at="2026-02-16T00:00:00Z",
    
    # Governance Metadata (Phase 1)
    author="SIMULATED_GOVERNANCE_BOARD",
    review_board="SIMULATED_GOVERNANCE_BOARD",
    approval_date="2026-02-15",
    
    # Identity Binding (Phase 1 / Gap 1)
    # This hash protects against manual tampering with rule weights.
    policy_document_hash="71121b26c693f262",
    attestation="SIMULATED_ATTESTATION: Validated against Nutri Governance Standard v1.0",

    baseline_score=0.1,
    tie_break_logic="highest_grade_wins",

    tier_thresholds=(
        (0.9, "consensus"),
        (0.7, "strong"),
        (0.5, "moderate"),
        (0.3, "emerging"),
        (0.0, "speculative"),
    ),

    rule_set=(
        # ── Study Type Weights ──
        PolicyRule(
            rule_id="STUDY_TYPE_WEIGHT",
            description="Score contribution from highest-quality study type in evidence set",
            category="study_type_weight",
            parameters=(
                ("meta-analysis", 0.6),
                ("systematic-review", 0.5),
                ("rct", 0.4),
                ("observational", 0.2),
                ("animal", 0.1),
                ("in-vitro", 0.05),
                ("mechanistic-inference", 0.05),
            ),
        ),
        # ── Sample Size Bonus ──
        PolicyRule(
            rule_id="SAMPLE_SIZE_BONUS",
            description="Bonus based on cumulative sample size across evidence set",
            category="sample_size_bonus",
            parameters=(
                ("threshold_high", 1000),
                ("bonus_high", 0.2),
                ("threshold_mid", 100),
                ("bonus_mid", 0.1),
                ("threshold_low", 10),
                ("bonus_low", 0.05),
            ),
        ),
        # ── Recency Bonus ──
        PolicyRule(
            rule_id="RECENCY_BONUS",
            description="Bonus for recent publications",
            category="recency_bonus",
            parameters=(
                ("year_recent", 2020),
                ("bonus_recent", 0.1),
                ("year_moderate", 2015),
                ("bonus_moderate", 0.05),
            ),
        ),
        # ── Retraction Penalty ──
        PolicyRule(
            rule_id="RETRACTION_PENALTY",
            description="Hard penalty if any evidence has been retracted",
            category="retraction_penalty",
            parameters=(
                ("penalty_score", 0.01),
                ("override_all", True),
            ),
        ),
        # ── Contradiction Penalty ──
        PolicyRule(
            rule_id="CONTRADICTION_PENALTY",
            description="Penalty for contradictory evidence in the set",
            category="contradiction_penalty",
            parameters=(
                ("per_contradiction_penalty", 0.05),
                ("max_penalty", 0.15),
            ),
        ),
    ),
)
