"""
Deterministic Mechanism Parser for Scientific Intelligence.
Extracts structured claims from text using regex and keyword matching.
"""
import re
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

class MechanismParser:
    """
    Parses scientific text to extract structured mechanism claims.
    Reliable > Smart.
    """
    
    # --- KNOWLEDGE BASE (hardcoded for reliability) ---
    
    # --- KNOWLEDGE BASE ---
    # We import from registry to ensure 1:1 parity with the rest of the system
    from backend.sensory.sensory_registry import MOLECULE_TO_RECEPTORS, RECEPTOR_TO_PERCEPTION

    COMPOUNDS = set(MOLECULE_TO_RECEPTORS.keys()) | {
        "caffeine", "theobromine", "glutamate", "sodium", "sucrose", 
        "ethanol", "menthol", "piperine", "gingerol", "shogaol", "acetic acid",
        "lactic acid", "citric acid", "malic acid", "tannin", "polyphenol",
        "gluten", "gliadin", "glutenin", "starch", "amylose", "amylopectin",
        "carbon_dioxide", "nitrogen", "water", "lipid", "fatty_acid", "amino_acid",
        "capsaicin", "salt", "sugar", "yeast" 
    }

    RECEPTORS = set(RECEPTOR_TO_PERCEPTION.keys()) | {
        "trpv1", "trpa1", "trpm8", "tas2r", "tas1r2", "tas1r3", "enact", "g-protein",
        "gpcr", "ion channel", "neuron", "nociceptor", "olfactory_receptor"
    }

    PROCESSES = {
        "binds", "activates", "inhibits", "blocks", "triggers", "stimulates",
        "released", "denaturation", "fermentation", "maillard", 
        "caramelization", "oxidation", "hydrolysis", "emulsification", "gelatinization",
        "expansion", "rise", "brown"
    }

    PERCEPTIONS = {
        "burning", "hot", "spicy", "bitter", "sweet", "sour", "salty", "umami",
        "astringent", "cooling", "cold", "pungent", "tingling", "numbing", 
        "aroma", "flavor", "taste", "texture", "mouthfeel", "fluffy", "airy", "crispy"
    }

    def __init__(self):
        # Normalize keys for matching (replace underscores with spaces for regex)
        self.compound_patterns = self._compile_patterns([c.replace("_", " ") for c in self.COMPOUNDS])
        self.receptor_patterns = self._compile_patterns(self.RECEPTORS)
        self.process_patterns = self._compile_patterns(self.PROCESSES)
        self.perception_patterns = self._compile_patterns(self.PERCEPTIONS)

    def _compile_patterns(self, terms: Set[str]) -> List[Any]:
        """Compile regex patterns for terms."""
        return [re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) for term in terms]

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract mechanisms from text.
        Returns a list of structured claim objects.
        """
        if not text:
            return []

        text_lower = text.lower()
        claims = []
        
        # 1. Detect Entities
        found_compounds = self._find_matches(text_lower, self.compound_patterns, self.COMPOUNDS)
        found_receptors = self._find_matches(text_lower, self.receptor_patterns, self.RECEPTORS)
        found_processes = self._find_matches(text_lower, self.process_patterns, self.PROCESSES)
        found_perceptions = self._find_matches(text_lower, self.perception_patterns, self.PERCEPTIONS)

        # 2. Heuristic Construction
        # If we found relevant entities, construct a claim.
        # Ideally, we'd link specific compounds to specific receptors, but for now, 
        # we aggregate found entities into a single "narrative claim" if they co-occur.
        
        if found_compounds or found_receptors or found_processes:
            # Create a claim for each Compound -> Process -> Perception/Receptor grouping?
            # Or just one big claim for the paragraph?
            # User requirement: "Compound: capsaicin, Target: TRPV1, Effect: heat"
            
            # Simple aggregation strategy:
            # For each compound found, create a claim linking it to found receptors/perceptions.
            
            if found_compounds:
                for compound in found_compounds:
                    claim = {
                        "claim_id": f"parsed_{compound}_{len(claims)}",
                        "text": text[:200] + "...", # Snippet
                        "compound": compound,
                        "receptor": found_receptors[0] if found_receptors else "unknown",
                        "mechanism": {
                            "label": found_processes[0] if found_processes else "associated with",
                            "steps": [{"type": "compound", "description": compound}] 
                                     + ([{"type": "receptor", "description": r} for r in found_receptors])
                                     + ([{"type": "process", "description": p} for p in found_processes])
                        },
                        "perception_outputs": found_perceptions,
                        "evidence_level": "unverified",
                        "source": "mechanism_parser"
                    }
                    claims.append(claim)
            
            elif found_receptors or found_processes:
                 # No compound, but mechanism discussion
                 claim = {
                        "claim_id": f"parsed_general_{len(claims)}",
                        "text": text[:200] + "...",
                        "compound": "general",
                        "receptor": found_receptors[0] if found_receptors else "unknown",
                        "mechanism": {
                            "label": "general mechanism",
                            "steps": ([{"type": "receptor", "description": r} for r in found_receptors])
                                     + ([{"type": "process", "description": p} for p in found_processes])
                        },
                        "perception_outputs": found_perceptions,
                        "evidence_level": "unverified",
                         "source": "mechanism_parser"
                 }
                 claims.append(claim)

        logger.info(f"[PARSER] Extracted {len(claims)} claims from text.")
        return claims

    def _find_matches(self, text: str, patterns: List[Any], original_terms: Set[str]) -> List[str]:
        """Find unique terms in text."""
        matches = set()
        # Optimization: verify if term is substring first? No, regex is fast enough for small sets.
        # Actually mapping back to original term might be cleaner.
        
        # Using simple iteration over set keywords checking `in` might be faster/simpler than regex for unigram keywords
        # But regex handles boundaries (\b).
        
        for term in original_terms:
            # Quick check
            if term in text:
                 # Strict boundary check
                 if re.search(r'\b' + re.escape(term) + r'\b', text):
                     matches.add(term)
        
        return list(matches)
