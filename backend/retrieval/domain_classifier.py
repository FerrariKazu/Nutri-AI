"""
Domain Classifier — Pre-retrieval semantic disambiguation.

Detects whether a query is about biology/physiology vs chemistry vs nutrition,
ensuring correct index routing BEFORE retrieval happens.
"""

import re
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# Biological / Physiological context signals
BIOLOGY_SIGNALS: Set[str] = {
    "body", "cells", "cell", "cellular", "blood", "bloodstream",
    "tissue", "organ", "muscle", "nerve", "brain", "heart", "liver", "kidney",
    "transport", "transporter", "absorption", "absorb", "digest", "digestion",
    "metabolism", "metabolize", "metabolic", "physiological", "physiology",
    "membrane", "channel", "ion channel", "receptor", "signal", "signaling",
    "pathway", "biological", "homeostasis", "electrolyte",
    "gradient", "potential", "electrochemical", "pump",
    "sodium potassium pump", "na+", "k+", "ca2+",
    "enzyme activity", "cofactor", "bioavailability",
    "in the body", "in your body", "in our body",
    "how the body", "what the body", "inside the body",
    "human body", "in cells", "across membrane",
}

# Chemical / Industrial context signals
CHEMISTRY_SIGNALS: Set[str] = {
    "ionic", "covalent", "bond", "bonding", "nacl", "formula",
    "oxidation", "reduction", "reagent", "titration", "molarity",
    "stoichiometry", "valence", "electron", "orbital",
    "crystallize", "precipitate", "chromatography", "eluant",
    "industrial", "manufacture", "synthesis reaction",
}

# Nutrition-specific signals
NUTRITION_SIGNALS: Set[str] = {
    "macros", "calories", "calorie", "kcal", "protein content",
    "carbs", "carbohydrates", "fat content", "fiber",
    "serving", "per 100g", "daily value", "rdi", "rda",
    "nutrition facts", "nutritional value", "how much protein",
    "how many calories",
}

# Contamination blocklist — terms that indicate irrelevant retrieval results
CONTAMINATION_BLOCKLIST: Set[str] = {
    "chromatography", "eluant", "eluent", "electrophoresis",
    "hplc", "mass spectrometry", "spectroscopy",
    "industrial solvent", "cas number", "cas no",
    "laboratory grade", "reagent grade",
    "patent", "manufacturing process",
}


class DomainClassifier:
    """
    Pre-retrieval classifier that determines the semantic domain of a query.
    
    Prevents routing errors like:
    - "sodium binds in the body" → chemistry (WRONG) → should be biology
    - "maillard reaction temperature" → biology (WRONG) → should be chemistry
    """

    def classify(self, query: str) -> Dict[str, any]:
        """
        Classify query into semantic domain.
        
        Returns:
            {
                "domain": "biology" | "chemistry" | "nutrition" | "general",
                "signals": ["matched signal terms"],
                "confidence": 0.0-1.0,
                "suppress_indices": ["index names to deprioritize"]
            }
        """
        q = query.lower().strip()

        bio_matches = self._match_signals(q, BIOLOGY_SIGNALS)
        chem_matches = self._match_signals(q, CHEMISTRY_SIGNALS)
        nutr_matches = self._match_signals(q, NUTRITION_SIGNALS)

        bio_score = len(bio_matches)
        chem_score = len(chem_matches)
        nutr_score = len(nutr_matches)

        total = bio_score + chem_score + nutr_score
        if total == 0:
            return {
                "domain": "general",
                "signals": [],
                "confidence": 0.3,
                "suppress_indices": []
            }

        # Priority: biology > nutrition > chemistry (for ambiguous queries)
        if bio_score > 0 and bio_score >= chem_score:
            domain = "biology"
            confidence = min(1.0, bio_score / max(total, 1))
            suppress = ["chemistry"] if chem_score == 0 else []
            signals = bio_matches
        elif nutr_score > 0 and nutr_score >= bio_score and nutr_score >= chem_score:
            domain = "nutrition"
            confidence = min(1.0, nutr_score / max(total, 1))
            suppress = ["chemistry"]
            signals = nutr_matches
        elif chem_score > 0:
            domain = "chemistry"
            confidence = min(1.0, chem_score / max(total, 1))
            suppress = []
            signals = chem_matches
        else:
            domain = "general"
            confidence = 0.3
            suppress = []
            signals = []

        logger.info(
            f"[DOMAIN_CLASSIFIER] query='{q[:60]}' → domain={domain} "
            f"confidence={confidence:.2f} signals={signals[:3]} "
            f"suppress={suppress}"
        )

        return {
            "domain": domain,
            "signals": signals,
            "confidence": confidence,
            "suppress_indices": suppress
        }

    def is_contaminated(self, text: str) -> bool:
        """Check if retrieved text is contamination (chromatography, industrial, etc.)."""
        t = text.lower()
        return any(term in t for term in CONTAMINATION_BLOCKLIST)

    def _match_signals(self, query: str, signals: Set[str]) -> List[str]:
        """Find all signal terms present in query."""
        matched = []
        for signal in signals:
            if signal in query:
                matched.append(signal)
        return matched
