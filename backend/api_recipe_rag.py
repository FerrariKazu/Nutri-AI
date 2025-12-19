"""
RAG-enhanced recipe generation endpoint.

Combines food and compound retrieval for scientifically-grounded recipe invention.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging

from backend.vector_store_food import search as food_search
from backend.vector_store_compound import search as compound_search
from backend.nutrition_loader import normalizer
from backend.utils.api_response import create_success_response, create_error_response
from llm import generate  # Existing Qwen wrapper
from prompts import SYSTEM_PROMPT
from ingredient_constraints import analyze_ingredients, BASIC_PANTRY_ITEMS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["recipe_rag"])


class RAGRecipeRequest(BaseModel):
    """Request for RAG-enhanced recipe generation."""
    ingredients: str = Field(..., description="Comma-separated ingredients")
    dislikes: str = Field("none", description="Dislikes/allergies")
    dietary_constraints: str = Field("none", description="Dietary constraints")
    goal: str = Field("", description="Goal (e.g., 'dinner', 'dessert')")
    innovation_level: int = Field(2, ge=1, le=3, description="1=safe, 3=wild")
    explain_compounds: bool = Field(True, description="Include chemical explanations")


@router.post("/recipe/rag", response_model=dict)
async def generate_rag_recipe(req: RAGRecipeRequest) -> dict:
    """
    Generate recipe with RAG (Retrieval-Augmented Generation).
    
    Process:
    1. Normalize ingredients
    2. Search food index for relevant recipes
    3. Search compound index for chemical context
    4. Build enhanced LLM prompt
    5. Generate recipe
    6. Run pantry checker
    7. Return with RAG metadata
    
    Example:
        POST /api/recipe/rag
        {
            "ingredients": "eggs, spinach, cheese",
            "goal": "breakfast",
            "innovation_level": 2,
            "explain_compounds": true
        }
    """
    try:
        # Normalize ingredients
        ingredient_list = [i.strip() for i in req.ingredients.split(',')]
        normalized_ingredients = [
            normalizer.normalize_ingredient_name(ing)
            for ing in ingredient_list
        ]
        
        logger.info(f"RAG recipe request: {ingredient_list}")
        
        # ===========================================================
        # STEP 1: Search Food Index
        # ===========================================================
        retrieved_foods = []
        
        try:
            if not food_search.is_ready():
                food_search.load()
            
            # Search with goal + ingredients
            search_query = f"{req.goal} {req.ingredients}".strip()
            food_results = food_search.semantic_search(search_query, k=5)
            retrieved_foods = food_results
            
            logger.info(f"Retrieved {len(retrieved_foods)} relevant foods")
        except Exception as e:
            logger.warning(f"Food search failed: {e}")
        
        # ===========================================================
        # STEP 2: Search Compound Index
        # ===========================================================
        compound_blocks = []
        
        if req.explain_compounds:
            try:
                if not compound_search.is_ready():
                    compound_search.load()
                
                # Search compounds for each ingredient
                for ing in normalized_ingredients[:5]:  # Limit to 5
                    compound_results = compound_search.semantic_search(ing, k=2)
                    
                    for comp in compound_results:
                        compound_blocks.append({
                            'ingredient': ing,
                            'compound_name': comp.get('name', ''),
                            'formula': comp.get('molecular_formula', ''),
                            'score': comp.get('score', 0),
                            'snippet': comp.get('snippet', ''),
                            'toxicity': comp.get('toxicity', {})
                        })
                
                logger.info(f"Retrieved {len(compound_blocks)} compound blocks")
            except Exception as e:
                logger.warning(f"Compound search failed: {e}")
        
        # ===========================================================
        # STEP 3: Build RAG-Enhanced Prompt
        # ===========================================================
        
        # Food context block
        food_context = ""
        if retrieved_foods:
            food_context = "\n\n=== RELEVANT RECIPES FOR INSPIRATION ===\n\n"
            for i, food in enumerate(retrieved_foods[:3], 1):
                food_context += f"[Recipe #{i}]\n"
                food_context += f"Title: {food.get('name', 'Unknown')}\n"
                food_context += f"Source: {food.get('source', 'N/A')}\n"
                
                nutrients = food.get('nutrients', {})
                if nutrients:
                    nutr_str = ", ".join([
                        f"{k}: {v:.1f}"
                        for k, v in list(nutrients.items())[:5]
                    ])
                    food_context += f"Nutrition: {nutr_str}\n"
                
                if food.get('snippet'):
                    food_context += f"Description: {food['snippet'][:200]}\n"
                
                food_context += "\n"
            
            food_context += "=== END OF REFERENCE RECIPES ===\n"
        
        # Compound context block
        compound_context = ""
        if compound_blocks:
            compound_context = "\n\n=== CHEMICAL CONTEXT FOR INGREDIENTS ===\n\n"
            for block in compound_blocks[:5]:
                compound_context += f"Ingredient: {block['ingredient']}\n"
                compound_context += f"  Compound: {block['compound_name']}\n"
                if block['formula']:
                    compound_context += f"  Formula: {block['formula']}\n"
                if block['snippet']:
                    compound_context += f"  Notes: {block['snippet'][:150]}\n"
                compound_context += "\n"
            
            compound_context += "=== END OF CHEMICAL CONTEXT ===\n"
        
        # Combined user prompt
        user_prompt = f"""{food_context}{compound_context}

ingredients_on_hand: {req.ingredients}
dislikes: {req.dislikes}
dietary_constraints: {req.dietary_constraints}
goal: {req.goal}
innovation_level: {req.innovation_level}

Task: Create a new recipe using the listed ingredients. Use the reference recipes and chemical context above to inspire your creation and explain ingredient interactions scientifically.
"""
        
        # ===========================================================
        # STEP 4: Generate Recipe
        # ===========================================================
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        initial_recipe = generate(messages, temperature=0.8, max_tokens=1024)
        
        # ===========================================================
        # STEP 5: Pantry Checker
        # ===========================================================
        analysis = analyze_ingredients(req.ingredients, initial_recipe)
        extras = sorted(analysis.get("extras", set()))
        
        final_recipe = initial_recipe
        corrected = False
        
        if extras:
            corrected = True
            logger.info(f"Correcting recipe - removing extras: {extras}")
            
            extras_list = ", ".join(extras)
            pantry_list = ", ".join(sorted(BASIC_PANTRY_ITEMS))
            
            followup = f"""In your previous draft, you used these ingredients which the user did NOT list and which are not in the basic pantry: {extras_list}.

Please rewrite the recipe to use only:
- the user's listed ingredients: {req.ingredients}
- and these basic pantry items: {pantry_list}

Do NOT use any of those extra ingredients again. Keep the same structure and chemical explanations."""
            
            messages.append({"role": "assistant", "content": initial_recipe})
            messages.append({"role": "user", "content": followup})
            
            final_recipe = generate(messages, temperature=0.8, max_tokens=1024)
        
        # ===========================================================
        # STEP 6: Return Response
        # ===========================================================
        
        data = {
            "success": True,
            "recipe": final_recipe,
            "retrieved_foods": retrieved_foods[:3],  # Return top 3
            "compound_blocks": compound_blocks[:5],  # Return top 5
            "rag_used": len(retrieved_foods) > 0 or len(compound_blocks) > 0,
            "corrected": corrected,
            "extras_removed": extras if extras else None
        }
        return create_success_response(data)
    
    except Exception as e:
        logger.error(f"RAG recipe generation failed: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))
