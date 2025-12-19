"""
Simple heuristic topic filter to check if user messages are food-related.

This module provides keyword-based filtering to pre-screen user messages
before sending them to a kitchen-only assistant.
"""

# Comprehensive set of food/cooking/nutrition-related keywords
FOOD_KEYWORDS = {
    # Cooking methods
    "bake", "baking", "boil", "boiling", "fry", "frying", "grill", "grilling",
    "roast", "roasting", "steam", "steaming", "sauté", "sauteing", "saute", "simmer",
    "simmering", "broil", "broiling", "poach", "poaching", "braise", "braising",
    "blanch", "blanching", "marinate", "marinating", "season", "seasoning",
    "chop", "chopping", "dice", "dicing", "mince", "mincing", "slice", "slicing",
    "stir-fry", "stir fry", "stirfry",
    
    # Food categories
    "vegetable", "vegetables", "veggie", "veggies", "fruit", "fruits", "meat", "meats", 
    "fish", "seafood", "poultry", "chicken", "beef", "pork", "lamb", "turkey",
    "pasta", "rice", "bread", "cheese", "dairy", "egg", "eggs",
    "grain", "grains", "legume", "legumes", "nut", "nuts", "seed", "seeds",
    "herb", "herbs", "spice", "spices", "sauce", "sauces", "soup", "soups",
    "salad", "salads", "dessert", "desserts", "cake", "cakes", "cookie", "cookies",
    
    # Common ingredients
    "garlic", "onion", "onions", "tomato", "tomatoes", "potato", "potatoes",
    "carrot", "carrots", "pepper", "peppers", "salt", "sugar", "flour",
    "butter", "oil", "olive", "vinegar", "lemon", "lime", "ginger",
    "basil", "oregano", "thyme", "rosemary", "parsley", "cilantro",
    "mushroom", "mushrooms", "broccoli", "spinach", "lettuce", "cucumber",
    "milk", "cream", "yogurt", "yoghurt",
    
    # Recipe-related terms
    "recipe", "recipes", "ingredient", "ingredients", "cook", "cooking",
    "prepare", "preparation", "dish", "dishes", "meal", "meals",
    "breakfast", "lunch", "dinner", "snack", "snacks", "brunch",
    "appetizer", "appetizers", "entree", "side", "main course", "cuisine", 
    "food", "foods",
    
    # Kitchen equipment
    "pan", "pot", "oven", "stove", "knife", "cutting board", "bowl",
    "whisk", "spatula", "spoon", "fork", "plate", "skillet", "wok",
    "blender", "mixer", "microwave", "refrigerator", "freezer",
    
    # Flavor and texture
    "sweet", "salty", "sour", "bitter", "umami", "savory", "spicy",
    "mild", "hot", "crispy", "crunchy", "creamy", "smooth", "tender",
    "juicy", "moist", "dry", "flavor", "flavors", "flavour", "flavours",
    "taste", "tastes", "aroma", "aromatic", "smell", "texture", "fresh", "ripe",
    
    # Nutrition terms
    "nutrition", "nutritional", "nutrient", "nutrients", "protein", "proteins",
    "carbohydrate", "carbohydrates", "carbs", "carb", "fat", "fats", 
    "vitamin", "vitamins", "mineral", "minerals", "calorie", "calories", 
    "fiber", "fibre", "diet", "diets", "healthy", "health", 
    "vegan", "vegetarian", "gluten", "organic", "keto", "paleo", 
    "low-carb", "low-fat", "allergy", "allergies", "intolerance", "intolerances",
    
    # Kitchen chemistry / food science
    "emulsion", "emulsify", "caramelize", "caramelization", "maillard",
    "browning", "ferment", "fermentation", "yeast", "baking soda",
    "baking powder", "starch", "acid", "alkaline",
    
    # Meal-specific and comfort foods
    "pizza", "burger", "sandwich", "burrito", "taco", "sushi", "curry",
    "stew", "casserole", "pie", "pancake", "pancakes", "waffle", "waffles",
    "omelette", "smoothie", "juice", "tea", "coffee", "broth", "stock",
    
    # Action words
    "eat", "eating", "ate", "eaten", "drink", "drinking", "drank",
    "serve", "serving", "garnish", "plate", "refrigerate", "freeze",
    
    # Misc food-related
    "kitchen", "culinary", "chef", "restaurant", "menu", "appetizing",
    "delicious", "tasty", "yummy", "edible", "homemade", "leftover", "leftovers",
}


def is_food_related(text: str) -> bool:
    """
    Check if the input text appears to be food-related using keyword matching.
    
    This is a simple heuristic that checks if any food-related keyword
    appears in the text. It's not perfect, but provides a basic pre-filter.
    
    Args:
        text: The user message to check.
    
    Returns:
        True if the text contains at least one food-related keyword,
        False otherwise.
    
    Example:
        >>> is_food_related("How do I make pasta carbonara?")
        True
        >>> is_food_related("Hello, I have eggs and rice, what can I do?")
        True
        >>> is_food_related("What is the capital of France?")
        False
        >>> is_food_related("What is machine learning?")
        False
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Check if any keyword appears in the text
    return any(kw in text_lower for kw in FOOD_KEYWORDS)
