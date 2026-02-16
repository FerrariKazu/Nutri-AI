"""
Nutri Sensory Registry v1.2
Deterministic mapping of Molecule -> Receptor -> Perception.
Supports multiple mechanism families: Chemical, Receptor, Process, Physical, Structural.
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

ONTOLOGY_VERSION = "1.3"

# Centralized Ontology Source of Truth
ONTOLOGY = {
    "compounds": {
        "caffeine": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "UniProt", "type": "database", "id": "Q9NYW0", "url": "https://www.uniprot.org/uniprotkb/Q9NYW0"},
                {"name": "PubChem", "type": "database", "id": "2519", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2519"}
            ],
            "tastes": [{"label": "bitter", "confidence": 0.95, "strength": 0.9, "direction": "increase"}],
            "receptors": [
                {
                    "name": "TAS2R10", 
                    "perception": "bitter", 
                    "confidence": 0.9, 
                    "strength": 0.8,
                    "canonical_pathway": [
                        {"node": "gustducin", "type": "g_protein", "label": "Gustducin Activation"},
                        {"node": "plc_beta_2", "type": "effector", "label": "PLCβ2 Activation"},
                        {"node": "trpm5", "type": "channel", "label": "TRPM5 Opening"},
                        {"node": "depolarization", "type": "signal", "label": "Cell Depolarization"}
                    ]
                },
                {"name": "TAS2R43", "perception": "bitter", "confidence": 0.85, "strength": 0.7},
                {"name": "TAS2R46", "perception": "bitter", "confidence": 0.85, "strength": 0.7}
            ],
            "evidence_type": "human study"
        },
        "quinine": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "PubChem", "type": "database", "id": "3034034", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/3034034"}
            ],
            "tastes": [{"label": "bitter", "confidence": 0.98, "strength": 1.0, "direction": "increase"}],
            "receptors": [
                {"name": "TAS2R7", "perception": "bitter", "confidence": 0.9},
                {"name": "TAS2R10", "perception": "bitter", "confidence": 0.9},
                {"name": "TAS2R14", "perception": "bitter", "confidence": 0.9},
                {"name": "TAS2R43", "perception": "bitter", "confidence": 0.9},
                {"name": "TAS2R46", "perception": "bitter", "confidence": 0.9}
            ],
            "evidence_type": "human study"
        },
        "capsaicin": {
            "families": ["receptor"],
            "authorities": [
                {"name": "UniProt", "type": "database", "id": "Q8NER1", "url": "https://www.uniprot.org/uniprotkb/Q8NER1"}
            ],
            "receptors": [{"name": "TRPV1", "perception": "heat / pungency", "confidence": 0.95, "strength": 1.0}],
            "evidence_type": "human study"
        },
        "menthol": {
            "families": ["receptor"],
            "authorities": [
                {"name": "UniProt", "type": "database", "id": "Q8TAC3", "url": "https://www.uniprot.org/uniprotkb/Q8TAC3"}
            ],
            "receptors": [{"name": "TRPM8", "perception": "cooling", "confidence": 0.95, "strength": 0.9}],
            "evidence_type": "human study"
        },
        "sucrose": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "PubChem", "type": "database", "id": "5988", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/5988"}
            ],
            "tastes": [{"label": "sweet", "confidence": 0.99, "strength": 1.0, "direction": "increase"}],
            "receptors": [
                {
                    "name": "TAS1R2", 
                    "perception": "sweet", 
                    "confidence": 0.95,
                    "canonical_pathway": [
                        {"node": "gustducin", "type": "g_protein", "label": "Gustducin (GNAT3)"},
                        {"node": "plc_beta_2", "type": "effector", "label": "PLCβ2 Activation"},
                        {"node": "ip3_ca", "type": "messenger", "label": "IP3/Ca2+ Release"},
                        {"node": "trpm5", "type": "channel", "label": "TRPM5 Opening"},
                        {"node": "depolarization", "type": "signal", "label": "Cell Depolarization"}
                    ]
                },
                {
                    "name": "TAS1R3", 
                    "perception": "sweet", 
                    "confidence": 0.95,
                    "canonical_pathway": [
                        {"node": "gustducin", "type": "g_protein", "label": "Gustducin (GNAT3)"},
                        {"node": "plc_beta_2", "type": "effector", "label": "PLCβ2 Activation"},
                        {"node": "ip3_ca", "type": "messenger", "label": "IP3/Ca2+ Release"},
                        {"node": "trpm5", "type": "channel", "label": "TRPM5 Opening"},
                        {"node": "depolarization", "type": "signal", "label": "Cell Depolarization"}
                    ]
                }
            ],
            "evidence_type": "human study"
        },
        "monosodium_glutamate": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "PubChem", "type": "database", "id": "23672308", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/23672308"}
            ],
            "tastes": [{"label": "umami", "confidence": 0.95, "strength": 0.9, "direction": "increase"}],
            "receptors": [
                {"name": "TAS1R1", "perception": "umami", "confidence": 0.9},
                {"name": "TAS1R3", "perception": "umami", "confidence": 0.9}
            ],
            "evidence_type": "human study"
        },
        "sodium_chloride": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "PubChem", "type": "database", "id": "5234", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/5234"}
            ],
            "tastes": [{"label": "salty", "confidence": 0.99, "strength": 1.0, "direction": "increase"}],
            "receptors": [{"name": "ENaC", "perception": "salty", "confidence": 0.9}],
            "evidence_type": "human study"
        },
        "citric_acid": {
            "families": ["chemical", "receptor"],
            "authorities": [
                {"name": "PubChem", "type": "database", "id": "311", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/311"}
            ],
            "tastes": [{"label": "sour", "confidence": 0.95, "strength": 0.8, "direction": "increase"}],
            "receptors": [{"name": "OTOP1", "perception": "sour", "confidence": 0.9}],
            "evidence_type": "human study"
        }
    },
    "processes": {
        "roasting": {
            "family": "chemical",
            "perceptions": [{"label": "bitter", "type": "taste", "direction": "increase", "strength": 0.6, "confidence": 0.7}],
            "evidence_type": "theoretical"
        },
        "fermentation": {
            "family": "chemical",
            "perceptions": [{"label": "sour", "type": "taste", "direction": "increase", "strength": 0.7, "confidence": 0.8}],
            "evidence_type": "human study"
        },
        "maillard": {
            "family": "chemical",
            "perceptions": [
                {"label": "savory", "type": "flavor", "direction": "increase", "strength": 0.8, "confidence": 0.85},
                {"label": "browned", "type": "color", "direction": "increase", "strength": 0.9, "confidence": 0.9}
            ],
            "evidence_type": "theoretical"
        }
    },
    "physical_states": {
        "fat": {
            "family": "physical",
            "effects": [{"label": "flavor release", "type": "aroma", "direction": "delay", "strength": 0.8, "confidence": 0.75}],
            "evidence_type": "theoretical"
        },
        "emulsion": {
            "family": "structural",
            "effects": [{"label": "mouthfeel", "type": "texture", "direction": "increase", "strength": 0.7, "confidence": 0.65}],
            "evidence_type": "theoretical"
        },
        "volatility": {
            "family": "structural",
            "effects": [{"label": "aroma release", "type": "aroma", "direction": "increase", "strength": 0.9, "confidence": 0.8}],
            "evidence_type": "theoretical"
        }
    }
}

class SensoryRegistry:
    """
    Deterministic sensory lookup engine based on Ontology v1.2.
    """
    
    @staticmethod
    def resolve_compound(compound_name: str) -> Dict[str, Any]:
        """
        Resolves a compound to its ontological entry.
        """
        name_clean = compound_name.lower().replace(" ", "_").replace("-", "_")
        return ONTOLOGY["compounds"].get(name_clean, {})

    @staticmethod
    def resolve_process(process_name: str) -> Dict[str, Any]:
        """
        Resolves a process (roasting, maillard, etc.)
        """
        return ONTOLOGY["processes"].get(process_name.lower(), {})

    @staticmethod
    def resolve_state(state_name: str) -> Dict[str, Any]:
        """
        Resolves a physical or structural state.
        """
        return ONTOLOGY["physical_states"].get(state_name.lower(), {})

    @staticmethod
    def map_compound_to_perception(compound_name: str) -> Dict[str, Any]:
        """
        LEGACY WRAPPER for backward compatibility.
        Maps a compound to its sensory chain.
        """
        entry = SensoryRegistry.resolve_compound(compound_name)
        if not entry:
            return {
                "compound": compound_name,
                "receptors": [],
                "perception_outputs": [],
                "resolved": False
            }
        
        receptors = [r["name"] for r in entry.get("receptors", [])]
        perception_outputs = []
        
        # Add receptor perceptions
        for r_entry in entry.get("receptors", []):
            perception_outputs.append({
                "receptor": r_entry["name"],
                "modality": "receptor_activation",
                "description": r_entry["perception"],
                "confidence": r_entry.get("confidence", 0.5),
                "direction": r_entry.get("direction", "increase")
            })
            
        # Add taste perceptions (if any)
        for t_entry in entry.get("tastes", []):
            perception_outputs.append({
                "modality": "taste",
                "description": t_entry["label"],
                "confidence": t_entry.get("confidence", 0.5),
                "direction": t_entry.get("direction", "increase")
            })
            
        return {
            "compound": compound_name,
            "receptors": receptors,
            "perception_outputs": perception_outputs,
            "resolved": True,
            "evidence_type": entry.get("evidence_type", "theoretical")
        }

    @staticmethod
    def get_receptor_details(receptor_name: str) -> Optional[Dict[str, Any]]:
        """
        Search ontology for a specific receptor's perception.
        """
        for compound in ONTOLOGY["compounds"].values():
            for r in compound.get("receptors", []):
                if r["name"] == receptor_name:
                    return {"modality": "receptor", "description": r["perception"]}
        return None

    @staticmethod
    def get_registry_snapshot() -> Dict[str, str]:
        """
        Computes a deterministic snapshot of the current registry state.
        Requirement for "computational time travel" (Vulnerability #2).
        """
        import hashlib
        import json
        
        canonical = json.dumps(ONTOLOGY, sort_keys=True, default=str)
        reg_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        
        return {
            "version": "1.2", # Registry version
            "hash": reg_hash,
            "ontology_version": ONTOLOGY_VERSION
        }
