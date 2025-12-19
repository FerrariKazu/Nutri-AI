"""
Text normalization and ingredient name processing.

Provides functions for cleaning, normalizing, and standardizing food/ingredient names
for consistent matching and search.
"""

import re
import string
import inflect
import unicodedata
from typing import Dict, Optional, List
import yaml
import json
from pathlib import Path

# Initialize inflect engine for singularization
_inflect_engine = inflect.engine()

# Common cooking descriptors to remove
COOKING_DESCRIPTORS = {
    # Preparation state
    "chopped", "diced", "minced", "sliced", "julienned", "grated", "shredded",
    "crushed", "mashed", "pureed", "ground", "whole", "halved", "quartered",
    "cubed", "crumbled", "flaked", "torn", "broken",
    
    # Cooking state
    "cooked", "raw", "fresh", "frozen", "canned", "dried", "roasted", "toasted",
    "grilled", "fried", "boiled", "steamed", "blanched", "sauteed", "baked",
    "smoked", "pickled", "fermented", "preserved",
    
    # Size/quality
    "large", "medium", "small", "extra-large", "extra-small", "baby", "mini",
    "jumbo", "giant", "tiny", "ripe", "unripe", "firm", "soft", "tender",
    "crisp", "crispy", "crunchy",
    
    # Modifiers
    "optional", "to taste", "as needed", "or more", "about", "approximately",
    "roughly", "finely", "coarsely", "thinly", "thickly",
    
    # Parts/cuts
    "boneless", "skinless", "trimmed", "peeled", "seeded", "cored", "deveined",
    "deboned", "shelled", "pitted", "stemmed",
    
    # Temperature/freshness
    "hot", "cold", "warm", "room temperature", "chilled", "refrigerated",
    
    # Other common
    "organic", "natural", "wild", "farm-raised", "free-range", "grass-fed",
    "homemade", "store-bought", "packaged", "prepared"
}

# Default alias mapping (common ingredient synonyms)
DEFAULT_ALIASES = {
    # Vegetables
    "scallions": "green onion",
    "spring onions": "green onion",
    "bell pepper": "sweet pepper",
    "capsicum": "sweet pepper",
    "cilantro": "coriander",
    "coriander leaves": "coriander",
    "zucchini": "courgette",
    "eggplant": "aubergine",
    "arugula": "rocket",
    
    # Sugars
    "caster sugar": "granulated sugar",
    "superfine sugar": "granulated sugar",
    "confectioners sugar": "powdered sugar",
    "icing sugar": "powdered sugar",
    
    # Dairy
    "heavy cream": "cream",
    "double cream": "cream",
    "single cream": "light cream",
    
    # Greens
    "salad greens": "lettuce",
    "mixed greens": "lettuce",
    
    # Proteins
    "ground beef": "minced beef",
    "ground pork": "minced pork",
    
    # Grains
    "quinoa": "quinoa grain",
    "bulgur": "bulgur wheat",
}

# Unit standardization
UNIT_MAPPING = {
    # Weight
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    
    # Volume
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "tsp": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tbsp": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "cup": "cup",
    "cups": "cup",
    "pint": "pint",
    "pints": "pint",
    "quart": "quart",
    "quarts": "quart",
    "gallon": "gallon",
    "gallons": "gallon",
    "fl oz": "fl_oz",
    "fluid ounce": "fl_oz",
    "fluid ounces": "fl_oz",
}


def normalize_text(s: str) -> str:
    """
    Basic text normalization: lowercase, remove punctuation, normalize Unicode.
    
    Args:
        s: Input string
        
    Returns:
        Normalized string
        
    Example:
        >>> normalize_text("Jalapeño Peppers!")
        'jalapeno peppers'
    """
    # Normalize Unicode (é → e, ñ → n, etc.)
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ASCII', 'ignore').decode('ASCII')
    
    # Convert to lowercase
    s = s.lower()
    
    # Remove punctuation except spaces and hyphens
    s = re.sub(f"[{re.escape(string.punctuation.replace('-', ''))}]", " ", s)
    
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s


def strip_descriptors(s: str) -> str:
    """
    Remove common cooking/food descriptors from text.
    
    Args:
        s: Input string (should be normalized first)
        
    Returns:
        String with descriptors removed
        
    Example:
        >>> strip_descriptors("fresh chopped cilantro")
        'cilantro'
    """
    words = s.split()
    filtered = [w for w in words if w not in COOKING_DESCRIPTORS]
    
    # Return filtered or original if nothing left
    return " ".join(filtered) if filtered else s


def singularize(s: str) -> str:
    """
    Convert plural nouns to singular using inflect.
    
    Args:
        s: Input string (word or phrase)
        
    Returns:
        Singularized string
        
    Example:
        >>> singularize("tomatoes")
        'tomato'
    """
    try:
        # Handle multi-word phrases by singularizing last word
        words = s.split()
        if len(words) > 1:
            last_word = words[-1]
            singular = _inflect_engine.singular_noun(last_word)
            if singular and isinstance(singular, str):
                words[-1] = singular
                return " ".join(words)
        else:
            singular = _inflect_engine.singular_noun(s)
            if singular and isinstance(singular, str):
                return singular
    except Exception:
        pass
    
    return s


def standardize_unit(unit: str) -> str:
    """
    Map unit to canonical form.
    
    Args:
        unit: Unit string
        
    Returns:
        Standardized unit
        
    Example:
        >>> standardize_unit("tablespoons")
        'tbsp'
    """
    unit_lower = unit.lower().strip()
    return UNIT_MAPPING.get(unit_lower, unit_lower)


def normalize_ingredient_name(s: str, apply_aliases: bool = True) -> str:
    """
    Full normalization pipeline for ingredient names.
    
    Pipeline:
    1. Normalize text (lowercase, remove punctuation, Unicode)
    2. Strip descriptors (chopped, fresh, etc.)
    3. Singularize
    4. Apply alias mapping (optional)
    
    Args:
        s: Raw ingredient name
        apply_aliases: Whether to apply alias mapping
        
    Returns:
        Fully normalized name
        
    Example:
        >>> normalize_ingredient_name("Fresh Chopped Scallions")
        'green onion'
    """
    # Step 1: Basic normalization
    s = normalize_text(s)
    
    # Step 2: Remove descriptors
    s = strip_descriptors(s)
    
    # Step 3: Singularize
    s = singularize(s)
    
    # Step 4: Apply aliases
    if apply_aliases and s in DEFAULT_ALIASES:
        s = DEFAULT_ALIASES[s]
    
    return s.strip()


def load_alias_map(path: Optional[str] = None) -> Dict[str, str]:
    """
    Load alias mapping from file or return default.
    
    Supports YAML and JSON formats.
    
    Args:
        path: Path to alias file (YAML or JSON), None for default
        
    Returns:
        Dictionary mapping ingredient names to canonical names
        
    Example:
        >>> aliases = load_alias_map("aliases.yaml")
        >>> aliases.get("cilantro")
        'coriander'
    """
    if path is None:
        return DEFAULT_ALIASES.copy()
    
    path_obj = Path(path)
    if not path_obj.exists():
        return DEFAULT_ALIASES.copy()
    
    try:
        with open(path_obj, 'r', encoding='utf-8') as f:
            if path_obj.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            elif path_obj.suffix == '.json':
                return json.load(f)
            else:
                return DEFAULT_ALIASES.copy()
    except Exception:
        return DEFAULT_ALIASES.copy()


def batch_normalize(names: List[str]) -> List[str]:
    """
    Normalize a batch of ingredient names.
    
    Args:
        names: List of raw ingredient names
        
    Returns:
        List of normalized names
    """
    return [normalize_ingredient_name(name) for name in names]


def extract_quantity_and_unit(s: str) -> tuple[Optional[float], Optional[str], str]:
    """
    Extract quantity, unit, and ingredient name from a string like "2 cups flour".
    
    Args:
        s: Ingredient string with optional quantity and unit
        
    Returns:
        Tuple of (quantity, unit, ingredient_name)
        
    Example:
        >>> extract_quantity_and_unit("2 cups all-purpose flour")
        (2.0, 'cup', 'all-purpose flour')
    """
    # Pattern: optional number, optional unit, then ingredient
    pattern = r'^(?:(\d+(?:\.\d+)?(?:/\d+)?)\s*)?(?:(' + '|'.join(UNIT_MAPPING.keys()) + r')[\s,]+)?(.+)$'
    
    match = re.match(pattern, s.strip(), re.IGNORECASE)
    
    if match:
        quantity_str, unit_str, ingredient = match.groups()
        
        # Parse quantity
        quantity = None
        if quantity_str:
            try:
                # Handle fractions like "1/2"
                if '/' in quantity_str:
                    parts = quantity_str.split('/')
                    quantity = float(parts[0]) / float(parts[1])
                else:
                    quantity = float(quantity_str)
            except ValueError:
                pass
        
        # Standardize unit
        unit = standardize_unit(unit_str) if unit_str else None
        
        return quantity, unit, ingredient.strip()
    
    return None, None, s.strip()
