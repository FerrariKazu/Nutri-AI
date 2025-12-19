"""
Ingredient constraint analysis for Nutri recipe inventor.

This module helps identify when recipes use ingredients beyond what the user
has on hand and a basic pantry, enabling automatic recipe correction.
"""

from __future__ import annotations

from typing import Iterable


# Basic pantry items that most home cooks have
BASIC_PANTRY_ITEMS: set[str] = {
    "salt",
    "black pepper",
    "pepper",
    "water",
    "oil",
    "olive oil",
    "vegetable oil",
    "butter",
    "sugar",
    "flour",
    "baking powder",
    "baking soda",
    "vinegar",
    "garlic powder",
    "onion powder",
    "soy sauce",
    "honey",
    "vanilla extract",
    "cinnamon",
    "paprika",
    "cumin",
    "oregano",
    "basil",
    "thyme",
}


def _normalize_token(text: str) -> str:
    """Lowercase and strip simple punctuation from a short token."""
    return "".join(ch for ch in text.lower().strip() if ch.isalnum() or ch.isspace())


def parse_user_ingredients(raw: str) -> set[str]:
    """
    Split the user-specified ingredients string on commas and return a
    set of normalized ingredient tokens.

    Example:
        "eggs, rice, milk" -> {"eggs", "rice", "milk"}
    """
    parts = [part.strip() for part in raw.split(",")]
    tokens: set[str] = set()
    for part in parts:
        norm = _normalize_token(part)
        if norm:
            tokens.add(norm)
    return tokens


def extract_ingredient_lines(reply: str) -> list[str]:
    """
    Extract bullet lines from the INGREDIENTS section of a Nutri reply.

    Assumes the reply contains a section starting with a line that begins with
    'INGREDIENTS' (case-insensitive), and that the lines immediately following
    that header which start with a '-', '•', or '*' are ingredient lines,
    until a blank line or another ALL-CAPS style header.

    Returns a list of raw ingredient lines, e.g. "- 2 large eggs".
    If the structure cannot be found, returns an empty list.
    """
    lines = reply.splitlines()
    ingredients_start = None

    for idx, line in enumerate(lines):
        if line.strip().upper().startswith("INGREDIENTS"):
            ingredients_start = idx
            break

    if ingredients_start is None:
        return []

    result: list[str] = []
    for line in lines[ingredients_start + 1 :]:
        stripped = line.strip()
        if not stripped:
            # blank line: stop if we've already collected some
            if result:
                break
            continue

        # Stop on next header-like line
        if stripped.isupper() and not stripped.startswith(("-", "•", "*")):
            break

        if stripped.startswith(("-", "•", "*")):
            result.append(stripped)
        elif result:
            # Once we've started collecting bullets, stop when bullets stop.
            break

    return result


def normalize_ingredient_line(line: str) -> str:
    """
    Normalize a single ingredient bullet line to a rough ingredient name token.

    Example:
        "- 2 large eggs" -> "eggs"
        "- 1 tbsp olive oil" -> "olive oil"
    """
    stripped = line.lstrip("-•*").strip()
    norm = _normalize_token(stripped)
    if not norm:
        return ""

    # Heuristic: drop leading quantity/measurement words (numbers, 'tbsp', 'tsp', etc.)
    words = norm.split()
    cleaned_words: list[str] = []
    skip_prefixes = {
        "tbsp",
        "tsp",
        "teaspoon",
        "teaspoons",
        "tablespoon",
        "tablespoons",
        "cup",
        "cups",
        "g",
        "kg",
        "ml",
        "l",
        "oz",
        "lb",
        "lbs",
        "pinch",
        "dash",
        "large",
        "small",
        "medium",
    }

    for w in words:
        if w.isdigit():
            continue
        if w in skip_prefixes:
            continue
        cleaned_words.append(w)

    if not cleaned_words:
        cleaned_words = words

    return " ".join(cleaned_words).strip()


def analyze_ingredients(user_ingredients_raw: str, reply_text: str) -> dict[str, set[str]]:
    """
    Compare the ingredients listed in the model's reply with what the user said they have,
    plus a small basic pantry.

    Returns a dict with three sets:
      - "from_user": ingredients that appear to come from the user's list,
      - "pantry": ingredients that match BASIC_PANTRY_ITEMS,
      - "extras": ingredients that are neither from_user nor pantry.

    All values are normalized simple strings (lowercase).
    """
    user_set = parse_user_ingredients(user_ingredients_raw)
    pantry_set = {_normalize_token(item) for item in BASIC_PANTRY_ITEMS}

    lines = extract_ingredient_lines(reply_text)
    from_user: set[str] = set()
    pantry: set[str] = set()
    extras: set[str] = set()

    for line in lines:
        name = normalize_ingredient_line(line)
        if not name:
            continue

        # Check if this ingredient seems to come from the user's list
        if any(token and token in name for token in user_set):
            from_user.add(name)
            continue

        # Check if this ingredient matches pantry
        if any(p and p in name for p in pantry_set):
            pantry.add(name)
            continue

        extras.add(name)

    return {
        "from_user": from_user,
        "pantry": pantry,
        "extras": extras,
    }
