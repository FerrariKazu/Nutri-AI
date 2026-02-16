"""
Deterministic Mechanism Parser for Scientific Intelligence.
Extracts structured claims from text using regex and keyword matching.
v1.2: Integrated with unified Ontology.
"""
import re
import logging
from typing import List, Dict, Any, Set

from backend.sensory.sensory_registry import ONTOLOGY

logger = logging.getLogger(__name__)

class MechanismParser:
    """
    Parses scientific text to identify compounds, receptors, processes, and states.
    """
    
    # --- DYNAMIC KNOWLEDGE BASE ---
    
    COMPOUNDS = set(ONTOLOGY["compounds"].keys()) | {
        "caffeine", "theobromine", "glutamate", "sodium", "sucrose", 
        "ethanol", "menthol", "piperine", "gingerol", "shogaol", "acetic acid",
        "lactic acid", "citric acid", "malic acid", "tannin", "polyphenol",
        "fat", "lipid", "msg", "salt", "sugar"
    }

    # Extract all receptor names from ontology
    RECEPTORS = set()
    for comp in ONTOLOGY["compounds"].values():
        for r in comp.get("receptors", []):
            RECEPTORS.add(r["name"])
    
    # Standard receptor families
    RECEPTORS |= {"trpa1", "trpv1", "trpm8", "tas2r", "tas1r2", "tas1r3", "enac", "otop1"}

    PROCESSES = {
        "binds", "activates", "inhibits", "blocks", "triggers", "stimulates",
        "released", "denaturation", "fermentation", "maillard", 
        "caramelization", "oxidation", "hydrolysis", "emulsification", "gelatinization",
        "expansion", "rise", "brown", "roasting", "extraction", "partitioning", "volatilization"
    }

    PHYSICAL_STATES = {
        "lipid", "fat", "phase", "diffusion", "transport", "release", "solubility", "viscosity", "kinetics"
    }

    STRUCTURES = {
        "emulsion", "matrix", "network", "foam", "suspension", "micelle", "bubble", "structural"
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
        self.physical_patterns = self._compile_patterns(self.PHYSICAL_STATES)
        self.structure_patterns = self._compile_patterns(self.STRUCTURES)

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
        found_physical = self._find_matches(text_lower, self.physical_patterns, self.PHYSICAL_STATES)
        found_structures = self._find_matches(text_lower, self.structure_patterns, self.STRUCTURES)

        # 2. Heuristic Construction
        if found_compounds or found_receptors or found_processes or found_physical or found_structures:
            if found_compounds:
                for compound in found_compounds:
                    claim = {
                        "claim_id": f"parsed_{compound}_{len(claims)}",
                        "text": text[:300] + "...",
                        "compound": compound,
                        "receptor": found_receptors[0] if found_receptors else "unknown",
                        "mechanism": {
                            "label": found_processes[0] if found_processes else "associated with",
                            "steps": [{"type": "compound", "description": compound}] 
                                     + ([{"type": "receptor", "description": r} for r in found_receptors])
                                     + ([{"type": "process", "description": p} for p in found_processes])
                                     + ([{"type": "physical", "description": ph} for ph in found_physical])
                                     + ([{"type": "structure", "description": s} for s in found_structures])
                        },
                        "perception_outputs": found_perceptions,
                        "physical_states": found_physical,
                        "structures": found_structures,
                        "evidence_level": "heuristic",
                        "source": "mechanism_parser"
                    }
                    claims.append(claim)
            
            elif found_receptors or found_processes or found_physical or found_structures:
                 claim = {
                        "claim_id": f"parsed_general_{len(claims)}",
                        "text": text[:300] + "...",
                        "compound": "general",
                        "receptor": found_receptors[0] if found_receptors else "unknown",
                        "mechanism": {
                            "label": "general mechanism",
                            "steps": ([{"type": "receptor", "description": r} for r in found_receptors])
                                     + ([{"type": "process", "description": p} for p in found_processes])
                                     + ([{"type": "physical", "description": ph} for ph in found_physical])
                                     + ([{"type": "structure", "description": s} for s in found_structures])
                        },
                        "perception_outputs": found_perceptions,
                        "physical_states": found_physical,
                        "structures": found_structures,
                        "evidence_level": "heuristic",
                         "source": "mechanism_parser"
                 }
                 claims.append(claim)

        return claims

    def _find_matches(self, text: str, patterns: List[Any], original_terms: Set[str]) -> List[str]:
        """Find unique terms in text."""
        matches = set()
        for term in original_terms:
            t_lower = term.lower().replace("_", " ")
            if t_lower in text:
                 if re.search(r'\b' + re.escape(t_lower) + r'\b', text):
                     matches.add(term)
        return list(matches)
