"""
Deterministic Trace Domain Classifier.
Two-pass architecture: preliminary (cheap) → final (post-enrichment).
Replaces _is_scientific_intent() with a structured, auditable classification.

Pass 1 (Preliminary): Uses ONLY user_message + response_mode.
    Called at EP-2 (after classify_response_mode, before pipeline).
    May produce provisional "contextual" that Pass 2 can upgrade.

Pass 2 (Final): Uses enriched claims, belief_state, prior_claims.
    Called at EP-3 (after enrich_claims, after purity gate).
    MONOTONIC UPGRADE RULE: SCIENTIFIC is sticky, CONTEXTUAL can only upgrade.
"""

import logging
from backend.response_modes import ResponseMode
from backend.mode_classifier import is_biological_context, is_causal_intent

logger = logging.getLogger(__name__)

SCIENTIFIC_MODES = {ResponseMode.DIAGNOSTIC, ResponseMode.NUTRITION_ANALYSIS}
CONTEXTUAL_MODES = {ResponseMode.CONVERSATION}
PROCEDURAL_MODES = {ResponseMode.PROCEDURAL}


# ── PASS 1: Preliminary Classification (EP-2, pre-pipeline) ──

def classify_trace_domain_preliminary(
    user_message: str,
    response_mode: ResponseMode
) -> tuple:
    """
    Fast classification using ONLY user_message + response_mode.
    No memory/belief_state required (may not be available yet).

    Returns: (domain_type, visibility_level, domain_confidence, reason)

    Returns provisional domain. May be upgraded by Pass 2.
    NEVER downgrades: SCIENTIFIC is sticky once set.
    """
    has_bio = is_biological_context(user_message)
    # has_causal is too broad (e.g. "how do") for Pass 1.
    # We rely on Pass 2 (enrichment) to catch non-bio mechanistic queries.
    
    # Rule 1: Mode-based classification (Strongest signal)
    if response_mode in SCIENTIFIC_MODES:
        result = ("scientific", "expanded", 0.85,
                  f"response_mode={response_mode.value}")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 1: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Rule 2: Provisional procedural (pending enrichment)
    if response_mode in PROCEDURAL_MODES:
        result = ("contextual", "hidden", 0.60,
                  "provisional_procedural (pending enrichment)")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 1: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Rule 3: Explicit biological signal
    if has_bio:
        result = ("scientific", "expanded", 0.95,
                  f"bio_keywords={has_bio}")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 1: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Default: Provisional contextual
    result = ("contextual", "hidden", 0.60,
              f"provisional_contextual (mode={response_mode.value})")
    logger.info(f"[DOMAIN_CLASSIFIER] Pass 1: {result[0]} (confidence={result[2]}, reason={result[3]})")
    return result


# ── PASS 2: Final Classification (EP-3, post-enrichment) ──

def classify_trace_domain_final(
    preliminary_domain: str,
    preliminary_confidence: float,
    has_enriched_claims: bool,
    enriched_claim_count: int,
    belief_state_active: bool,
    has_prior_claims: bool
) -> tuple:
    """
    Confirms or upgrades the preliminary classification.

    MONOTONIC UPGRADE RULE:
      - SCIENTIFIC is sticky. Can NEVER be downgraded.
      - CONTEXTUAL can upgrade to HYBRID or SCIENTIFIC.
      - HYBRID cannot downgrade to CONTEXTUAL.

    Returns: (domain_type, visibility_level, domain_confidence, reason)
    """
    # Rule 0: Handle confirmed scientific (monotonic)
    if preliminary_domain == "scientific":
        refined_confidence = preliminary_confidence
        if has_enriched_claims and enriched_claim_count > 0:
            refined_confidence = min(1.0, preliminary_confidence + 0.05)
        result = ("scientific", "expanded", refined_confidence,
                  f"confirmed_scientific (claims={enriched_claim_count})")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Rule 1: Upgrade CONTEXTUAL → HYBRID if scientific content emerged
    if preliminary_domain == "contextual" and has_enriched_claims:
        if belief_state_active or has_prior_claims:
            result = ("hybrid", "collapsible", 0.75,
                      f"upgraded_to_hybrid (claims={enriched_claim_count}, belief_active={belief_state_active})")
            logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
            return result
        # Claims exist but no memory context → upgrade to SCIENTIFIC
        result = ("scientific", "expanded", 0.80,
                  f"upgraded_to_scientific (unexpected_claims={enriched_claim_count})")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Rule 2: Upgrade CONTEXTUAL → HYBRID if prior scientific context
    if preliminary_domain == "contextual" and has_prior_claims:
        result = ("hybrid", "collapsible", 0.70,
                  "upgraded_to_hybrid (prior_claims_from_session)")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Rule 3: HYBRID stays HYBRID (monotonic)
    if preliminary_domain == "hybrid":
        refined_confidence = preliminary_confidence
        if has_enriched_claims:
            refined_confidence = min(1.0, preliminary_confidence + 0.05)
        result = ("hybrid", "collapsible", refined_confidence,
                  f"confirmed_hybrid (claims={enriched_claim_count})")
        logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
        return result

    # Default: Keep preliminary
    result = (preliminary_domain, "hidden", preliminary_confidence,
              "confirmed_contextual (no scientific content found)")
    logger.info(f"[DOMAIN_CLASSIFIER] Pass 2: {result[0]} (confidence={result[2]}, reason={result[3]})")
    return result
