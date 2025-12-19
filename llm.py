"""
Simple wrapper for calling a local Qwen model via Ollama.

This module provides a clean interface to interact with Qwen models
served by Ollama running locally. It handles chat-style interactions,
prompt building, validation, and self-correction.

Example usage:
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me a simple pasta recipe."},
    ]
    reply = generate(messages)
    print(reply)
"""

import os
import requests
import re
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

# Import backend tools
try:
    from backend.tools import (
        search_recipes,
        get_ingredient_nutrition,
        convert_units,
        get_food_chemistry,
        pantry_tools,
        memory,
    )
    TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Tools not available: {e}")
    TOOLS_AVAILABLE = False

# Tool registry
TOOL_REGISTRY = {}
if TOOLS_AVAILABLE:
    TOOL_REGISTRY = {
        "search_recipes": search_recipes,
        "get_ingredient_nutrition": get_ingredient_nutrition,
        "convert_units": convert_units,
        "get_food_chemistry": get_food_chemistry,
        "pantry_tools": pantry_tools,
        "memory_save": lambda session_id, key, value: memory.save(session_id, key, value),
        "memory_get": lambda session_id, key: memory.get(session_id, key),
    }

# Configuration constants
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"



def get_engine():
    """Satisfies api.py startup check. Returns the Ollama base URL."""
    return OLLAMA_URL


class LLMError(Exception):
    """Custom exception raised when LLM operations fail."""
    pass


def generate(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,  # Increased from 512 to 2048 for detailed chemistry explanations
    model_name: Optional[str] = None,
) -> str:
    """
    Generate a response from the Qwen model via Ollama.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.
                 Role should be one of: 'system', 'user', or 'assistant'.
                 Example: [{"role": "user", "content": "Hello!"}]
        temperature: Sampling temperature (0.0 to 1.0). Higher values make
                    output more random. Default is 0.7.
        max_tokens: Maximum number of tokens to generate. Default is 2048.
        model_name: Override the model name. If None, uses OLLAMA_MODEL_NAME
                   environment variable or DEFAULT_MODEL_NAME.

    Returns:
        The assistant's response text as a string.

    Raises:
        LLMError: If the request fails or the response is malformed.
    """
    # Determine which model to use
    if model_name is None:
        model_name = os.getenv("OLLAMA_MODEL_NAME", DEFAULT_MODEL_NAME)

    # Build the request payload
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }

    try:
        # Make the request to Ollama (increased timeout for longer responses)
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        
        # Check for HTTP errors
        if not response.ok:
            raise LLMError(
                f"Ollama API returned status {response.status_code}: {response.text}"
            )
        
        # Parse the response
        data = response.json()
        
        # Extract the assistant's message
        if "message" not in data or "content" not in data["message"]:
            raise LLMError(
                f"Unexpected response structure from Ollama: {data}"
            )
        
        assistant_reply = data["message"]["content"].strip()
        return assistant_reply
        
    except requests.exceptions.RequestException as e:
        raise LLMError(
            f"Failed to contact Ollama at {OLLAMA_URL}: {e}"
        ) from e


def build_prompt(
    system_prompt: str,
    rag_block: str = "",
    memory_block: str = "",
    user_context: str = "",
    task_instruction: str = ""
) -> str:
    """
    Build a complete user prompt with all context blocks.
    
    Args:
        system_prompt: System-level instructions
        rag_block: RAG reference recipes (if any)
        memory_block: Conversation history (if any)
        user_context: User request context (ingredients, constraints, etc.)
        task_instruction: Specific task instructions
        
    Returns:
        Complete formatted prompt string
    """
    blocks = []
    
    if rag_block:
        blocks.append(rag_block)
    
    if memory_block:
        blocks.append(f"=== RECENT CONVERSATION ===\n{memory_block}\n=== END MEMORY ===")
    
    if user_context:
        blocks.append(f"=== USER REQUEST CONTEXT ===\n{user_context}")
    
    # Add highly detailed instruction
    detailed_instruction = """
IMPORTANT: Generate a HIGHLY DETAILED recipe with:
- Detailed ingredient explanations (why each ingredient, what it does)
- Step-by-step clarity with specific techniques
- Temperature and time reasoning when applicable
- Optional variations or substitutions
- Texture, flavor, and aroma descriptions
- Kitchen chemistry explanations where relevant

Be thorough and educational while maintaining mobile-friendly formatting."""
    
    if task_instruction:
        blocks.append(f"\n{task_instruction}\n{detailed_instruction}")
    else:
        blocks.append(detailed_instruction)
    
    return "\n\n".join(blocks)


def validate_recipe(
    recipe_text: str,
    forbidden_ingredients: List[str],
    required_constraints: Dict[str, str]
) -> Tuple[bool, List[str]]:
    """
    Validate a recipe against constraints.
    
    Args:
        recipe_text: Generated recipe text
        forbidden_ingredients: List of ingredients to avoid (dislikes)
        required_constraints: Dict of constraint types and values
        
    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    violations = []
    recipe_lower = recipe_text.lower()
    
    # Check for forbidden ingredients
    for ingredient in forbidden_ingredients:
        if ingredient.lower() in recipe_lower:
            violations.append(f"Contains forbidden ingredient: {ingredient}")
    
    # Check dietary constraints
    dietary = required_constraints.get("dietary_constraints", "").lower()
    if dietary and dietary != "none":
        if "vegan" in dietary:
            non_vegan = ["meat", "chicken", "beef", "pork", "fish", "egg", "dairy", "milk", "cheese", "butter"]
            for item in non_vegan:
                if item in recipe_lower:
                    violations.append(f"Vegan constraint violated: contains {item}")
                    break
        
        if "vegetarian" in dietary:
            non_veg = ["meat", "chicken", "beef", "pork", "fish", "seafood"]
            for item in non_veg:
                if item in recipe_lower:
                    violations.append(f"Vegetarian constraint violated: contains {item}")
                    break
    
    is_valid = len(violations) == 0
    return is_valid, violations


def generate_with_reflection(
    messages: List[Dict],
    forbidden_ingredients: List[str] = None,
    constraints: Dict[str, str] = None,
    max_retries: int = 2
) -> str:
    """
    Generate with self-correction via validation and retry.
    
    Args:
        messages: Message list for LLM
        forbidden_ingredients: Ingredients to avoid
        constraints: Dietary and other constraints
        max_retries: Maximum number of regeneration attempts
        
    Returns:
        Validated recipe text
    """
    forbidden_ingredients = forbidden_ingredients or []
    constraints = constraints or {}
    
    for attempt in range(max_retries + 1):
        # Generate recipe with increased token limit for detail
        recipe = generate(messages, temperature=0.7, max_tokens=1500)
        
        # Validate
        is_valid, violations = validate_recipe(recipe, forbidden_ingredients, constraints)
        
        if is_valid:
            logger.info(f"Recipe validated successfully on attempt {attempt + 1}")
            return recipe
        
        # Log violations and retry
        logger.warning(f"Attempt {attempt + 1} failed validation: {violations}")
        
        if attempt < max_retries:
            # Add correction instruction
            correction_msg = f"\n\nYour previous recipe violated these constraints: {', '.join(violations)}. Please regenerate without these violations."
            messages.append({"role": "assistant", "content": recipe})
            messages.append({"role": "user", "content": correction_msg})
    
    # Return last attempt even if invalid (with warning)
    logger.error(f"Recipe failed validation after {max_retries + 1} attempts")
    return recipe
