import json
import logging
import re
from pathlib import Path
from typing import List, Set, Dict, Any, Optional

logger = logging.getLogger(__name__)

class QueryDecomposer:
    """
    Service for decomposing and expanding technical nutrition queries 
    into semantic variations using a scientific ontology.
    """
    
    # 🧬 Scientific & Nutritional Ontology Registry
    ONTOLOGY = {
        "sodium": [
            "sodium ion transport", "Na+ transport", "sodium potassium ATPase", 
            "renal sodium reabsorption", "intestinal sodium absorption"
        ],
        "calcium": [
            "calcium signaling", "Ca2+ flux", "calbindin", 
            "intracellular calcium", "calcium-sensing receptor"
        ],
        "glucose": [
            "Maillard reaction", "Strecker degradation", "blood glucose regulation", 
            "glycemic index"
        ],
        "antioxidant": [
            "lipid peroxidation", "hexanal formation", "free radical scavenging", 
            "oxidative stress"
        ],
        "oxidation": [
            "lipid peroxidation", "hexanal formation", "free radical scavenging", 
            "oxidative stress"
        ],
        "vitamins": [
            "fat-soluble vitamins", "water-soluble vitamins", "micronutrient absorption", 
            "bioavailability", "hypervitaminosis"
        ],
        "minerals": [
            "trace elements", "electrolytes", "bone mineral density", 
            "enzyme cofactors"
        ],
        "protein": [
            "amino acid profile", "nitrogen balance", "proteolysis", 
            "muscle protein synthesis", "denaturation"
        ],
        "fats": [
            "fatty acid composition", "omega-3 to omega-6 ratio", "lipid metabolism", 
            "cholesterol regulation", "triglyceride hydrolyzation"
        ],
        "carbs": [
            "glycemic load", "dietary fiber", "resistant starch", 
            "insulin sensitivity", "gluconeogenesis"
        ],
        "metabolism": [
            "metabolic rate", "catabolism", "anabolism", 
            "thermogenesis", "mitochondrial function"
        ],
        "magnesium": [
            "elemental magnesium", "magnesium citrate", "magnesium glycinate", 
            "serum magnesium", "renal magnesium excretion"
        ],
        "curcumin": [
            "curcuminoids", "turmeric extract", "bioavailability enhancement", 
            "piperine co-administration"
        ],
        "egcg": [
            "epigallocatechin gallate", "green tea extract", "catechin bioavailability", 
            "polyphenol absorption"
        ]
    }

    # 🍽️ Taste Ontology Registry — hardcoded fallback
    _TASTE_ONTOLOGY_FALLBACK = {
        "bitter": ["alkaloid", "tannin", "polyphenol"],
        "sweet": ["sucrose", "glucose", "fructose"],
        "sour": ["citric acid", "malic acid", "lactic acid"],
        "umami": ["glutamate", "inosinate", "umami receptor"]
    }

    # M7 — Dynamic loading from JSON with validation
    TASTE_ONTOLOGY: Dict[str, List[str]] = {}

    @classmethod
    def _load_taste_ontology(cls) -> Dict[str, List[str]]:
        """Load taste ontology from JSON file with fallback to hardcoded dict."""
        if cls.TASTE_ONTOLOGY:
            return cls.TASTE_ONTOLOGY

        # Correct path for Phase 3
        ontology_path = Path(__file__).resolve().parent.parent.parent / "ontologies" / "taste.json"
        try:
            with open(ontology_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cls.TASTE_ONTOLOGY = data
            logger.info(f"[ONTOLOGY] Loaded taste ontology from {ontology_path}")
        except Exception as e:
            logger.warning(f"[ONTOLOGY] Failed to load {ontology_path}: {e} — using internal fallback")
            cls.TASTE_ONTOLOGY = cls._TASTE_ONTOLOGY_FALLBACK

        return cls.TASTE_ONTOLOGY

    @staticmethod
    def _normalize_for_dedup(text: str) -> str:
        """Normalize text for deduplication: lowercase, strip punctuation, collapse whitespace."""
        # R1: Proper query normalization
        normalized = text.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[?.!,;:]+$", "", normalized)
        return normalized

    @classmethod
    def decompose(cls, query: str, tier: Optional[str] = None) -> List[str]:
        """
        Expand a query into its semantic components.
        Returns a list of unique subqueries, limited to 5 total.
        """
        query_lower = query.lower()
        expansions = [query]

        # Subquery splitting
        subqueries = re.split(r'\s+(and|or|with|,)\s+', query_lower)
        for sq in subqueries:
            sq = sq.strip()
            if sq not in ["and", "or", "with", ","] and len(sq) > 2:
                expansions.append(sq)

        # 1. Apply Scientific Ontology Expansion
        for key, terms in cls.ONTOLOGY.items():
            if re.search(r'\b' + re.escape(key) + r'\b', query_lower):
                expansions.extend([terms[i] for i in range(min(3, len(terms)))])

        # 2. Taste Expansion Activation Rule (Feature 2)
        taste_ontology = cls._load_taste_ontology()
        taste_keywords = set(taste_ontology.keys()) | {"taste", "flavor", "flavour", "profile", "sensory", "palate"}
        
        activate_taste = any(re.search(r'\b' + re.escape(kw) + r'\b', query_lower) for kw in taste_keywords)
        
        taste_expansion_applied = False
        if activate_taste:
            tier_has_chemistry = tier in ["TIER_1", "TIER_2", "TIER_3", "TIER_4", "TIER_5"]
            for key, terms in taste_ontology.items():
                if re.search(r'\b' + re.escape(key) + r'\b', query_lower):
                    # Limit to max 3 terms per category (Feature 3)
                    expansions.extend([terms[i] for i in range(min(3, len(terms)))])
                    taste_expansion_applied = True
                    logger.info(f"[QUERY_DECOMP] Expanded taste key '{key}' (chemistry={tier_has_chemistry})")

        # ── M1: Case + punctuation normalized deduplication ───────────────
        unique_expansions = []
        seen: Set[str] = set()
        for item in expansions:
            if not item:
                continue
            norm = cls._normalize_for_dedup(item)
            if norm not in seen:
                unique_expansions.append(item)
                seen.add(norm)
            if len(unique_expansions) >= 5:
                break

        # ── M3: Structured expansion logging ──────────────────────────────
        logger.info(
            "[QUERY_DECOMP] decomposition_complete",
            extra={
                "original_query": query,
                "expanded_count": len(unique_expansions),
                "taste_expansion": taste_expansion_applied,
                "tier": tier,
                "queries": unique_expansions
            }
        )

        return unique_expansions