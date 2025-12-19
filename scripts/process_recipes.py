#!/usr/bin/env python3
"""
Recipe Nutrition Processor CLI

End-to-end pipeline to:
1. Load recipes from CSV
2. Normalize ingredients and map to nutrition database
3. Compute recipe nutrition totals
4. Classify dietary tags
5. Save processed recipes to JSON

Usage:
    python scripts/process_recipes.py
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to import nutri module
sys.path.insert(0, str(Path(__file__).parent.parent))

from nutri.normalizer import load_food_database
from nutri.nutrition import compute_recipe_nutrition


def load_recipes(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load recipes from CSV file.
    
    Args:
        csv_path: Path to recipes CSV
        
    Returns:
        List of recipe dictionaries
    """
    print(f"📚 Loading recipes from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Convert to list of dicts
    recipes = df.to_dict('records')
    print(f"✅ Loaded {len(recipes)} recipes")
    
    return recipes


def process_all_recipes(recipes: List[Dict[str, Any]], food_db) -> List[Dict[str, Any]]:
    """
    Process all recipes to compute nutrition.
    
    Args:
        recipes: List of recipe dicts
        food_db: FoodDatabase instance
        
    Returns:
        List of processed recipes with nutrition
    """
    processed = []
    matched_count = 0
    total_ingredients = 0
    
    print(f"\n🔬 Processing {len(recipes)} recipes...")
    
    for idx, recipe in enumerate(recipes):
        if (idx + 1) % 100 == 0:
            print(f"  Progress: {idx + 1}/{len(recipes)} recipes ({(idx + 1) / len(recipes) * 100:.1f}%)")
        
        processed_recipe = compute_recipe_nutrition(recipe, food_db)
        processed.append(processed_recipe)
        
        # Track statistics
        for ing in processed_recipe['ingredients']:
            total_ingredients += 1
            if ing['matched_food']:
                matched_count += 1
    
    # Print summary statistics
    match_rate = (matched_count / total_ingredients * 100) if total_ingredients > 0 else 0
    print(f"\n📊 Processing Summary:")
    print(f"  Total recipes: {len(processed)}")
    print(f"  Total ingredients: {total_ingredients}")
    print(f"  Matched ingredients: {matched_count} ({match_rate:.1f}%)")
    print(f"  Unmatched ingredients: {total_ingredients - matched_count} ({100 - match_rate:.1f}%)")
    
    # Calculate average nutrition
    if processed:
        avg_calories = sum(r['nutrition']['calories'] for r in processed) / len(processed)
        avg_protein = sum(r['nutrition']['protein_g'] for r in processed) / len(processed)
        avg_fat = sum(r['nutrition']['fat_g'] for r in processed) / len(processed)
        avg_carbs = sum(r['nutrition']['carbs_g'] for r in processed) / len(processed)
        
        print(f"\n🍽️  Average Nutrition per Recipe:")
        print(f"  Calories: {avg_calories:.1f} kcal")
        print(f"  Protein: {avg_protein:.1f}g")
        print(f"  Fat: {avg_fat:.1f}g")
        print(f"  Carbs: {avg_carbs:.1f}g")
    
    # Dietary tag distribution
    tag_counts = {}
    for recipe in processed:
        for tag in recipe.get('diet_tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    if tag_counts:
        print(f"\n🏷️  Dietary Tag Distribution:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(processed) * 100
            print(f"  {tag}: {count} recipes ({percentage:.1f}%)")
    
    return processed


def save_processed_recipes(recipes: List[Dict[str, Any]], output_path: str):
    """
    Save processed recipes to JSON file.
    
    Args:
        recipes: List of processed recipe dicts
        output_path: Output JSON path
    """
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving processed recipes to {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)
    
    file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
    print(f"✅ Saved {len(recipes)} recipes ({file_size:.2f} MB)")


def main():
    """Main CLI entry point."""
    # Define paths
    base_dir = Path(__file__).parent.parent
    nutrition_db_path = base_dir / "data" / "nutrition" / "opennutrition_foods.tsv"
    recipes_csv_path = base_dir / "data" / "recipes" / "13k-recipes.csv"
    output_path = base_dir / "processed" / "recipes_with_nutrition.json"
    
    print("=" * 70)
    print("🍳 RECIPE NUTRITION PROCESSOR")
    print("=" * 70)
    
    # Check if files exist
    if not nutrition_db_path.exists():
        print(f"❌ Error: Nutrition database not found at {nutrition_db_path}")
        sys.exit(1)
    
    if not recipes_csv_path.exists():
        print(f"❌ Error: Recipes CSV not found at {recipes_csv_path}")
        sys.exit(1)
    
    try:
        # Load nutrition database
        print(f"\n🗄️  Loading nutrition database from {nutrition_db_path}...")
        food_db = load_food_database(str(nutrition_db_path))
        print(f"✅ Loaded nutrition database with {len(food_db.df)} foods")
        
        # Load recipes
        recipes = load_recipes(str(recipes_csv_path))
        
        # Process recipes
        processed_recipes = process_all_recipes(recipes, food_db)
        
        # Save results
        save_processed_recipes(processed_recipes, str(output_path))
        
        print(f"\n{'=' * 70}")
        print("✨ Processing complete!")
        print(f"{'=' * 70}\n")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
