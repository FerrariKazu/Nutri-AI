curl -s -X POST http://localhost:11434/api/chat -d '{
  "model": "qwen3:8b",
  "messages": [
    {"role": "system", "content": "You are a precise ingredient extractor."},
    {"role": "user", "content": "Extract the quantitative ingredients from this recipe into a JSON list.\n\nRecipe:\n\n    **Recipe: Chicken and Rice**\n    - 150g Chicken breast\n    - 200g White rice\n    - 2 tbsp Soy sauce (30g)\n    \n\nREQUIRED JSON Format:\n[\n  { \"name\": \"Ingredient Name\", \"amount_g\": float, \"original_text\": \"Original text\" }\n]\n\nRules:\n- 1 tbsp = 15g, 1 cup = 240g, 1 tsp = 5g.\n- If no unit, estimate 100g for mains, 5g for spices.\n- Return ONLY the JSON list.\n\nIMPORTANT: Return ONLY valid JSON. No conversational filler or explanations."}
  ],
  "options": {"temperature": 0.1},
  "stream": false
}'
