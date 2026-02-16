"""
Policy Engine v1.0 — Deterministic Confidence Executor

This is the SOLE AUTHORITY for computing confidence in Nutri.
No other component may compute, infer, or default confidence values.

Invariants:
- Pure function: no side effects
- Reproducible: identical inputs → identical outputs
- Traceable: every rule firing is logged structurally
- Fails hard: missing policy → crash
"""

import logging
from typing import List, Dict, Any

from backend.contracts.evidence_schema import EvidenceRecord, EffectDirection
from backend.contracts.evidence_policy import (
    EvidencePolicy, PolicyRule, RuleFiring, ConfidenceBreakdown
)

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Deterministic executor.
    Receives (claim, evidence_records, policy) → ConfidenceBreakdown.
    
    - Side-effect free
    - Reproducible
    - Identical input → identical output
    - Emits trace log of which rules fired
    """

    @staticmethod
    def execute(
        claim: Dict[str, Any],
        evidence: List[EvidenceRecord],
        policy: EvidencePolicy
    ) -> ConfidenceBreakdown:
        """
        Execute the declared policy against evidence.
        Returns a fully structural ConfidenceBreakdown.
        
        HARD FAIL if policy is None or invalid.
        """
        # ── FAILURE DOCTRINE ──
        if policy is None:
            raise RuntimeError("[POLICY_ENGINE] FATAL: Policy artifact is None. Cannot compute confidence.")
        
        # Identity and Integrity Validation (Phase 1)
        policy.validate()
        
        if not isinstance(policy, EvidencePolicy):
            raise TypeError(f"[POLICY_ENGINE] FATAL: Expected EvidencePolicy, got {type(policy).__name__}")
        if not policy.rule_set:
            raise RuntimeError(f"[POLICY_ENGINE] FATAL: Policy {policy.policy_id} has empty rule_set. Corrupted artifact.")

        policy_hash = policy.compute_hash()
        score = policy.baseline_score
        firings: List[RuleFiring] = []

        logger.info(
            f"[POLICY_ENGINE] Executing policy={policy.policy_id} v={policy.version} "
            f"hash={policy_hash} evidence_count={len(evidence)} baseline={policy.baseline_score}"
        )

        # ── Execute each rule in declared order ──
        for rule in policy.get_rules():
            contribution = 0.0
            fired = False
            input_value = None

            if rule.category == "study_type_weight":
                contribution, fired, input_value = PolicyEngine._apply_study_type_weight(evidence, rule)

            elif rule.category == "sample_size_bonus":
                contribution, fired, input_value = PolicyEngine._apply_sample_size_bonus(evidence, rule)

            elif rule.category == "recency_bonus":
                contribution, fired, input_value = PolicyEngine._apply_recency_bonus(evidence, rule)

            elif rule.category == "retraction_penalty":
                result = PolicyEngine._apply_retraction_penalty(evidence, rule, score)
                contribution, fired, input_value = result
                if fired:
                    # Retraction overrides: set score to penalty value directly
                    score = rule.get_params()["penalty_score"]
                    firings.append(RuleFiring(
                        rule_id=rule.rule_id,
                        category=rule.category,
                        input_value=input_value,
                        contribution=contribution,
                        fired=True
                    ))
                    # Skip remaining rules — retraction is terminal
                    logger.warning(f"[POLICY_ENGINE] Retraction detected. Score overridden to {score}.")
                    break

            elif rule.category == "contradiction_penalty":
                contribution, fired, input_value = PolicyEngine._apply_contradiction_penalty(evidence, rule)

            else:
                raise RuntimeError(
                    f"[POLICY_ENGINE] FATAL: Unknown rule category '{rule.category}' in policy {policy.policy_id}. "
                    f"Rule: {rule.rule_id}. Aborting."
                )

            if fired:
                score += contribution

            firings.append(RuleFiring(
                rule_id=rule.rule_id,
                category=rule.category,
                input_value=input_value,
                contribution=contribution if fired else 0.0,
                fired=fired
            ))

            logger.info(
                f"[POLICY_ENGINE] Rule={rule.rule_id} fired={fired} "
                f"contribution={contribution:.3f} running_score={score:.3f}"
            )

        # ── Cap and assign tier ──
        final_score = min(round(score, 2), 1.0)
        final_score = max(final_score, 0.0)

        # Tier assignment from policy thresholds
        tier_map = policy.get_tier_thresholds()
        final_tier = "speculative"
        for threshold in sorted(tier_map.keys(), reverse=True):
            if final_score >= threshold:
                final_tier = tier_map[threshold]
                break

        breakdown = ConfidenceBreakdown(
            policy_id=policy.policy_id,
            policy_version=policy.version,
            policy_hash=policy_hash,
            final_score=final_score,
            tier=final_tier,
            baseline_used=policy.baseline_score,
            rule_firings=firings
        )

        logger.info(
            f"[POLICY_ENGINE] RESULT: score={final_score} tier={final_tier} "
            f"rules_fired={sum(1 for f in firings if f.fired)}/{len(firings)}"
        )

        return breakdown

    # ══════════════════════════════════════════════════════
    # Pure rule applicators — no side effects
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _apply_study_type_weight(evidence: List[EvidenceRecord], rule: PolicyRule):
        """Find max study type weight from evidence set."""
        if not evidence:
            return 0.0, False, "no_evidence"

        params = rule.get_params()
        max_weight = 0.0
        max_type = "none"

        for ev in evidence:
            weight = params.get(ev.study_type.value, 0.0)
            if weight > max_weight:
                max_weight = weight
                max_type = ev.study_type.value

        return max_weight, max_weight > 0.0, max_type

    @staticmethod
    def _apply_sample_size_bonus(evidence: List[EvidenceRecord], rule: PolicyRule):
        """Compute bonus from cumulative sample size."""
        total_n = sum(ev.n for ev in evidence if ev.n)
        if total_n == 0:
            return 0.0, False, 0

        params = rule.get_params()

        if total_n > params["threshold_high"]:
            return params["bonus_high"], True, total_n
        elif total_n > params["threshold_mid"]:
            return params["bonus_mid"], True, total_n
        elif total_n > params["threshold_low"]:
            return params["bonus_low"], True, total_n

        return 0.0, False, total_n

    @staticmethod
    def _apply_recency_bonus(evidence: List[EvidenceRecord], rule: PolicyRule):
        """Bonus for publication recency."""
        years = [ev.publication_year for ev in evidence if ev.publication_year]
        if not years:
            return 0.0, False, None

        max_year = max(years)
        params = rule.get_params()

        if max_year >= params["year_recent"]:
            return params["bonus_recent"], True, max_year
        elif max_year >= params["year_moderate"]:
            return params["bonus_moderate"], True, max_year

        return 0.0, False, max_year

    @staticmethod
    def _apply_retraction_penalty(evidence: List[EvidenceRecord], rule: PolicyRule, current_score: float):
        """Hard penalty if any evidence is retracted."""
        retracted = [ev for ev in evidence if ev.retraction_status]
        if retracted:
            params = rule.get_params()
            penalty = params["penalty_score"] - current_score  # Delta to reach penalty score
            return penalty, True, [ev.id for ev in retracted]
        return 0.0, False, None

    @staticmethod
    def _apply_contradiction_penalty(evidence: List[EvidenceRecord], rule: PolicyRule):
        """Penalty for contradictory evidence."""
        contradictions = [ev for ev in evidence if ev.effect_direction == EffectDirection.CONTRADICTORY]
        if not contradictions:
            return 0.0, False, 0

        params = rule.get_params()
        penalty = min(
            len(contradictions) * params["per_contradiction_penalty"],
            params["max_penalty"]
        )
        return -penalty, True, len(contradictions)
