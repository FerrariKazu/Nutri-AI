"""
Domain Classifier — v2.0 Scientific Routing Refactor

Deterministic prompt classifier that runs BEFORE ResponseMode assignment.
Returns DomainClassification with confidence arbitration.

Pipeline order:
    User Input → Domain Classifier → Intent Type → ResponseMode → Pipeline Routing
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DomainClassification:
    """Result of domain-level prompt classification."""
    domain_type: str        # mechanistic_explanation | design_specification | compound_lookup | clinical_nutrition | general_discourse
    scientific_trigger: bool
    confidence: float       # 0.0–1.0


# ── PATTERN BANKS ──

MECHANISTIC_PATTERNS = [
    r"\bwhat\s+makes\b",
    r"\bhow\s+does\b",
    r"\bhow\s+do\b",
    r"\bwhy\s+does\b",
    r"\bwhy\s+do\b",
    r"\bwhy\s+is\b",
    r"\bmechanism\b",
    r"\bprocess\s+of\b",
    r"\breaction\b",
    r"\bfermentation\b",
    r"\benzyme\b",
    r"\bmolecular\b",
    r"\bstructure\s+of\b",
    r"\bgas\s+formation\b",
    r"\bchemical\s+(?:process|reaction|change)\b",
    r"\bphysical\s+(?:process|change|property)\b",
    r"\bscience\s+(?:behind|of)\b",
    r"\bchemistry\s+of\b",
    r"\bphysics\s+of\b",
    r"\bbiology\s+of\b",
    r"\bcausal\s+chain\b",
    r"\bbiochemical\b",
    r"\bmetaboli[sz]",
    r"\bcatalys",
    r"\bdenatur",
    r"\bgelatiniz",
    r"\bcrosslinking\b",
    r"\bMaillard\b",
    r"\bcarameliz",
    r"\bemulsif",
    r"\bhydrolysis\b",
    r"\boxidation\b",
    r"\bprotein\s+(?:folding|structure|denaturation)\b",
]

DESIGN_PATTERNS = [
    r"\brecipe\s+for\b",
    r"\bmake\s+me\b",
    r"\bcook\s+(?:a|me)\b",
    r"\bdesign\s+(?:a|me)\b",
    r"\bcreate\s+(?:a|me)\b",
    r"\bstep\s+by\s+step\b",
    r"\binstructions\s+for\b",
    r"\bingredients\b",
    r"\bmeal\s+plan\b",
    r"\bshopping\s+list\b",
    r"\bhow\s+do\s+i\s+(?:make|cook|prepare|bake)\b",
    r"\bgive\s+me\s+(?:a\s+)?(?:recipe|steps)\b",
    r"\bwalk\s+me\s+through\b",
    r"\b\d+\s*kcal\b",
    r"\bhigh[\s-]protein\s+(?:meal|breakfast|lunch|dinner|snack)\b",
]

COMPOUND_PATTERNS = [
    r"\bCID[\s:]?\d+\b",
    r"\bPubChem\b",
    r"\b(?:caffeine|capsaicin|curcumin|theanine|resveratrol|quercetin)\b",
    r"\bmolecular\s+(?:weight|formula)\b",
    r"\bcompound\s+(?:lookup|search|info)\b",
]

CLINICAL_PATTERNS = [
    r"\bmTOR\b",
    r"\binsulin\s+(?:resistance|sensitivity|response)\b",
    r"\bglycemic\s+(?:index|load|response)\b",
    r"\binflammation\b",
    r"\banti[\s-]?oxidant\b",
    r"\bleucine\b",
    r"\bomega[\s-]?3\b",
    r"\bcholesterol\b",
    r"\bcortisol\b",
    r"\bgut\s+(?:microbiome|flora|health)\b",
    r"\bimmune\s+(?:system|response|function)\b",
    r"\bblood\s+(?:sugar|pressure|glucose)\b",
]

GREETING_PATTERNS = [
    r"^\s*(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|what's\s+up|howdy)\s*[!.]?\s*$",
    r"^\s*(?:thanks?|thank\s+you|bye|goodbye|see\s+you)\s*[!.]?\s*$",
]


def classify_domain(prompt: str) -> DomainClassification:
    """
    Classifies a user prompt into a domain type with confidence.

    Runs BEFORE ResponseMode assignment.
    Confidence < 0.6 → falls back to general_discourse.
    """
    prompt_lower = prompt.lower().strip()

    # ── Fast Exit: Greetings / Meta ──
    for pat in GREETING_PATTERNS:
        if re.match(pat, prompt_lower, re.IGNORECASE):
            result = DomainClassification("general_discourse", False, 0.95)
            _log_classification(result, "greeting_match")
            return result

    # ── Score each domain ──
    mech_score = _score_patterns(prompt_lower, MECHANISTIC_PATTERNS)
    design_score = _score_patterns(prompt_lower, DESIGN_PATTERNS)
    compound_score = _score_patterns(prompt_lower, COMPOUND_PATTERNS)
    clinical_score = _score_patterns(prompt_lower, CLINICAL_PATTERNS)

    scores = {
        "mechanistic_explanation": mech_score,
        "design_specification": design_score,
        "compound_lookup": compound_score,
        "clinical_nutrition": clinical_score,
    }

    # ── Winner-takes-all with tie-breaking ──
    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    # Scientific trigger: any causal/scientific signal at all
    scientific_trigger = (mech_score > 0 or clinical_score > 0 or compound_score > 0)

    # ── Confidence Mapping ──
    # Each pattern match contributes to confidence
    # Mechanistic gets a boost for strong causal triggers (what makes, why does, how does)
    strong_causal = any(re.search(p, prompt_lower) for p in [
        r"\bwhat\s+makes\b", r"\bhow\s+does\b", r"\bwhy\s+does\b",
        r"\bwhy\s+do\b", r"\bhow\s+do\b", r"\bwhy\s+is\b",
        r"\bwhat\s+causes\b", r"\beffect\s+of\b",
        r"\bscience\s+(?:behind|of)\b", r"\bchemistry\s+of\b",
    ])
    
    base_confidence = min(1.0, best_score * 0.35)
    
    # Strong causal trigger boost for mechanistic
    if best_domain == "mechanistic_explanation" and strong_causal:
        base_confidence = max(base_confidence, 0.75)
    
    # Clinical domain boost for specific biomarkers
    if best_domain == "clinical_nutrition" and clinical_score >= 1:
        base_confidence = max(base_confidence, 0.75)
    
    confidence = base_confidence

    # ── Design vs Mechanistic Disambiguation ──
    # "Design a fluffy bread" → design (has recipe structure)
    # "What makes bread fluffy?" → mechanistic (causal question, no recipe)
    if best_domain == "mechanistic_explanation" and design_score > 0:
        # Design signal present → check if mechanistic is dominant
        if mech_score <= design_score:
            best_domain = "design_specification"
            confidence = min(1.0, design_score * 0.25)
            scientific_trigger = False

    # ── Clinical + Mechanistic uplift ──
    # "How does leucine activate mTOR?" → clinical_nutrition (more specific)
    if clinical_score > 0 and mech_score > 0:
        if clinical_score >= mech_score:
            best_domain = "clinical_nutrition"
            # Preserve boosted confidence if already set
            confidence = max(confidence, min(1.0, clinical_score * 0.35))

    # ── Confidence Arbitration ──
    if confidence < 0.6:
        if best_score > 0:
            # Some signal but too weak to commit
            _log_classification(
                DomainClassification("general_discourse", scientific_trigger, confidence),
                f"confidence_arbitration_fallback (best={best_domain}, conf={confidence:.2f})"
            )
            return DomainClassification("general_discourse", scientific_trigger, confidence)
        else:
            result = DomainClassification("general_discourse", False, 0.50)
            _log_classification(result, "no_signal")
            return result

    result = DomainClassification(best_domain, scientific_trigger, confidence)
    _log_classification(result, f"scores={{mech={mech_score}, design={design_score}, compound={compound_score}, clinical={clinical_score}}}")
    return result


def _score_patterns(text: str, patterns: list) -> int:
    """Count how many patterns match in the text."""
    count = 0
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            count += 1
    return count


def _log_classification(result: DomainClassification, reason: str):
    logger.info(
        f"[DOMAIN_CLASSIFIER] domain={result.domain_type} "
        f"scientific_trigger={result.scientific_trigger} "
        f"confidence={result.confidence:.2f} "
        f"reason={reason}"
    )
