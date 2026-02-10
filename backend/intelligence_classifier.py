import re

class IntelligenceClassifier:
    """
    Determines if a user query requires scientific trace telemetry.
    Adheres to the Mandate: Text is not the product, structured intelligence is.
    """
    
    SCIENTIFIC_DOMAINS = {
        "chemistry": [
            "molecule", "compound", "capsaicin", "glucose", "reactive", "ph ", "acid", 
            "catalyst", "transformation", "bonding", "solvent", "caffeine", "sugar",
            "carbohydrate", "protein", "lipid", "fat", "amino acid", "enzyme"
        ],
        "biology": [
            "receptor", "trpv1", "tas1r", "tas2r", "neuron", "absorption", "digestion",
            "metabolism", "effect", "interaction", "cell", "tissue", "gut", "brain",
            "sensory", "perception", "bitter", "sweet", "umami"
        ],
        "physics": [
            "heat", "temperature", "pressure", "viscosity", "emulsion", "foaming",
            "surface tension", "vapor", "sublimation", "phase change", "conduction",
            "convection", "radiation"
        ],
        "food_science": [
            "fermentation", "maillard", "caramelization", "denaturation", "hydration",
            "gelatinization", "crystallization", "oxidation", "preserving"
        ]
    }

    QUESTION_WORDS = ["how", "why", "what happens", "mechanism", "explain the relationship"]

    @classmethod
    def requires_trace(cls, user_input: str) -> bool:
        """
        Returns True if the input likely requires scientific reasoning.
        """
        text = user_input.lower()
        
        # 1. Check for specific scientific keywords
        for domain, keywords in cls.SCIENTIFIC_DOMAINS.items():
            for kw in keywords:
                if kw in text:
                    return True
        
        # 2. Check for "How/Why" questions combined with food context
        is_question = any(q in text for q in cls.QUESTION_WORDS)
        food_context = ["cooking", "food", "ingredient", "recipe", "dish", "taste"]
        has_food_context = any(f in text for f in food_context)
        
        if is_question and has_food_context:
            return True
            
        return False
