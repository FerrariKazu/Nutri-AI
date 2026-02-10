"""
Nutri Sensory Registry
Deterministic mapping of Molecule -> Receptor -> Perception.
Strict 'Never Invent' policy: If not in registry, it's unresolved.
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Molecule -> Receptors (Deterministic, Evidence-Based)
MOLECULE_TO_RECEPTORS = {
    # Bitter (TAS2R family)
    "caffeine": ["TAS2R10", "TAS2R43", "TAS2R46"],
    "quinine": ["TAS2R7", "TAS2R10", "TAS2R14", "TAS2R43", "TAS2R46"],
    "theobromine": ["TAS2R10", "TAS2R14"],
    "naringin": ["TAS2R31"],
    "phenylthiocarbamide": ["TAS2R38"],
    
    # Pungent/Trigeminal
    "capsaicin": ["TRPV1"],
    "piperine": ["TRPV1", "TRPA1"],
    "allyl_isothiocyanate": ["TRPA1"],  # Mustard, wasabi
    "menthol": ["TRPM8"],
    "cinnamaldehyde": ["TRPA1"],
    "eugenol": ["TRPV1", "TRPA1"],  # Cloves
    
    # Sweet (TAS1R2/TAS1R3)
    "sucrose": ["TAS1R2", "TAS1R3"],
    "fructose": ["TAS1R2", "TAS1R3"],
    "glucose": ["TAS1R2", "TAS1R3"],
    "aspartame": ["TAS1R2", "TAS1R3"],
    "saccharin": ["TAS1R2", "TAS1R3"],
    "stevioside": ["TAS1R2", "TAS1R3"],
    
    # Umami (TAS1R1/TAS1R3)
    "glutamic_acid": ["TAS1R1", "TAS1R3"],
    "monosodium_glutamate": ["TAS1R1", "TAS1R3"],
    "inosine_monophosphate": ["TAS1R1", "TAS1R3"],
    "guanosine_monophosphate": ["TAS1R1", "TAS1R3"],
    
    # Salty
    "sodium_chloride": ["ENaC"],
    
    # Sour
    "citric_acid": ["OTOP1"],
    "acetic_acid": ["OTOP1"],
    "lactic_acid": ["OTOP1"],
    "malic_acid": ["OTOP1"],
}

# Receptor -> Perception Modalities
RECEPTOR_TO_PERCEPTION = {
    "TAS2R7": {"modality": "taste", "description": "bitter"},
    "TAS2R10": {"modality": "taste", "description": "bitter"},
    "TAS2R14": {"modality": "taste", "description": "bitter"},
    "TAS2R43": {"modality": "taste", "description": "bitter"},
    "TAS2R46": {"modality": "taste", "description": "bitter"},
    "TAS1R1": {"modality": "taste", "description": "umami"},
    "TAS1R2": {"modality": "taste", "description": "sweet"},
    "TAS1R3": {"modality": "taste", "description": "sweet/umami co-receptor"},
    "TRPV1": {"modality": "trigeminal", "description": "heat / pungency"},
    "TRPM8": {"modality": "trigeminal", "description": "cooling"},
    "ENaC": {"modality": "taste", "description": "salty"},
    "OTOP1": {"modality": "taste", "description": "sour"},
}

class SensoryRegistry:
    """
    Deterministic sensory lookup engine.
    """
    
    @staticmethod
    def map_compound_to_perception(compound_name: str) -> Dict[str, Any]:
        """
        Maps a compound to its sensory chain.
        Returns: {
            "compound": str,
            "receptors": List[str],
            "perception_outputs": List[Dict[str, str]],
            "resolved": bool
        }
        """
        name_lower = compound_name.lower().replace(" ", "_")
        receptors = MOLECULE_TO_RECEPTORS.get(name_lower, [])
        
        if not receptors:
            return {
                "compound": compound_name,
                "receptors": [],
                "perception_outputs": [],
                "resolved": False
            }
        
        perception_outputs = []
        for r in receptors:
            perception = RECEPTOR_TO_PERCEPTION.get(r)
            if perception:
                perception_outputs.append({
                    "receptor": r,
                    **perception
                })
        
        return {
            "compound": compound_name,
            "receptors": receptors,
            "perception_outputs": perception_outputs,
            "resolved": True
        }

    @staticmethod
    def get_receptor_details(receptor_name: str) -> Optional[Dict[str, Any]]:
        return RECEPTOR_TO_PERCEPTION.get(receptor_name)
