import logging

logger = logging.getLogger(__name__)

# --- Categorized Entities ---

IONS = {
    "sodium", "potassium", "calcium", "magnesium", "chloride",
    "iron", "zinc", "copper", "selenium", "iodine"
}

HORMONES = {
    "insulin", "leptin", "ghrelin", "aldosterone", "cortisol",
    "glucagon", "thyroid", "estrogen", "testosterone"
}

TRANSPORTERS = {
    "atpase", "na+/k+ atpase", "enac", "sglt", "glut",
    "aquaporin", "transporter", "carrier"
}

BIO_STRUCTURES = {
    "membrane", "receptor", "tubule", "epithelium", "mitochondria",
    "intestine", "kidney", "cell", "plasma", "intracellular",
    "synaptic", "neuron", "epithelial", "organelle"
}

MECHANISTIC_VERBS = {
    "bind", "activate", "inhibit", "regulate", "transport",
    "absorb", "phosphorylate", "reabsorb", "secrete",
    "catalyze", "modulate", "trigger", "express"
}

# --- Derived Registries (Govern Escalation Scoring) ---

# 🚨 IMPORTANT: MECHANISTIC_VERBS are excluded from SCIENTIFIC_KEYWORDS
# This prevents verbs like "regulate" from inflating escalation scores.
SCIENTIFIC_KEYWORDS = IONS | HORMONES | TRANSPORTERS | {
    "biochemical", "metabolism", "signaling", "substrate", "enzyme",
    "ligand", "pathway", "interaction", "molecular", "synthesis",
    "glucose", "mtorc1"
}

# Biological contexts used for query broadening
BIO_CONTEXT = BIO_STRUCTURES | {
    "protein", "molecule", "atp", "biological", "affinity", "binding"
}

# Nutrition-specific terms (used for filtering or lower-tier RAG)
NUTRITION_KEYWORDS = {
    "calories", "macros", "protein", "nutrition", "vitamins", 
    "minerals", "fiber", "carbs", "fats", "kcal", "nutrient",
    "serving", "dietary", "intake"
}

# --- Ontology-Driven Expansion Templates ---

ENTITY_TEMPLATES = {
    "ion": [
        "{entity} transport mechanism",
        "{entity} absorption intestine",
        "{entity} reabsorption kidney",
        "{entity} cellular exchange"
    ],
    "hormone": [
        "{entity} receptor binding pathway",
        "{entity} metabolic regulation",
        "{entity} signaling cascade"
    ],
    "transporter": [
        "{entity} channel activation",
        "{entity} gradient transport",
        "{entity} membrane permeability"
    ]
}

def get_entity_type(word: str) -> str:
    """Helper to classify an entity for template routing."""
    w = word.lower()
    if w in IONS: return "ion"
    if w in HORMONES: return "hormone"
    if w in TRANSPORTERS: return "transporter"
    return "unknown"

# --- Startup Diagnostics ---
logger.info(f"[REGISTRY_INIT] sci={len(SCIENTIFIC_KEYWORDS)} bio={len(BIO_CONTEXT)}")
