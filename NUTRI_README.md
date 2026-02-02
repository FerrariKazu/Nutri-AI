# Nutri Food Synthesis System

A reasoning pipeline that invents chemically feasible, nutritionally constrained meals using retrieved scientific knowledge.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 2 (Optional)                       │
│  User Input → Agent 1 (Intent Extractor) → Constraints JSON │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                        PHASE 1                               │
│  Constraints → Retriever → Chemistry/Nutrition/Technique    │
│                     ↓                                        │
│           Food Synthesis LLM                                 │
│                     ↓                                        │
│       Invented Recipe + Chemical Explanation                 │
└─────────────────────────────────────────────────────────────┘
```

## Core Principles

1. **Recipes are OUTPUTS, not INPUTS** - No recipe lookup or recall
2. **Chemistry-first reasoning** - All decisions grounded in food science
3. **No hallucinated chemistry** - Must refuse impossible requests
4. **Agents are control flow** - Structured LLM calls, not personalities

## Quick Start

```python
from backend.food_synthesis import NutriPipeline

# Create pipeline (Phase 2 with intent extraction)
pipeline = NutriPipeline(use_phase2=True)

# Generate a novel recipe
result = pipeline.synthesize("I have eggs, flour, butter. Make something creative.")

print(result.recipe)
print(result.intent)  # Extracted constraints
```

## Components

### FoodSynthesisRetriever
Searches chemistry, nutrition, and technique knowledge. **Never searches recipes.**

Indexes used:
- `chemistry` - Ingredient chemistry, reactions, compounds
- `science` - Cooking physics, texture formation
- `usda_foundation` - Nutrition data (raw ingredients)
- `usda_branded` - Nutrition data (processed foods)

### IntentAgent (Agent 1)
Extracts structured constraints from user input. Does NO food reasoning.

Output schema:
```json
{
  "goal": "invent_meal | explain | optimize",
  "ingredients": [],
  "equipment": [],
  "dietary_constraints": {},
  "nutritional_goals": {},
  "time_limit_minutes": null,
  "explanation_depth": "casual | scientific"
}
```

### FoodSynthesisEngine
Single LLM call that invents recipes from first principles using:
1. Functional role assignment (protein, fat, acid, structure)
2. Chemical reaction analysis
3. Texture and structure design
4. Flavor layering
5. Nutrition estimation
6. Chemical explanation

## Running Tests

```bash
cd /home/ferrarikazu/nutri-ai
source venv/bin/activate
python -m pytest tests/test_food_synthesis.py -v
```

## Known Failure Cases

| Case | Expected Behavior |
|------|-------------------|
| Impossible physics (frozen+boiling) | System refuses, explains why |
| Conflicting constraints (vegan+eggs) | Extracts both, synthesis explains conflict |
| Missing critical ingredients | System states what's missing |
| Unknown compounds | System says "uncertain" with LOW confidence |

## Next Steps (Phase 3+)

- **Phase 3**: Multi-turn refinement with user feedback
- **Phase 4**: Cross-validation of chemistry claims
- **Phase 5**: Nutrition optimization loops
- **Phase 6**: Sensory prediction (texture, flavor)

## File Structure

```
backend/
├── food_synthesis.py      # Main pipeline (this system)
├── retriever/
│   ├── faiss_retriever.py # FAISS search
│   └── router.py          # Multi-index routing
├── llm_qwen3.py           # Ollama wrapper
└── embedder_bge.py        # BGE-M3 embeddings

vector_store/
├── chemistry/             # Ingredient chemistry
├── science/               # Cooking physics
├── usda_foundation/       # Raw food nutrition
├── usda_branded/          # Processed food nutrition
└── open_nutrition/        # Additional nutrition data

tests/
└── test_food_synthesis.py # Comprehensive test suite
```

## Environment

Requires:
- Ollama with `qwen3:8b` model
- Python 3.10+
- FAISS, sentence-transformers, FlagEmbedding

All dependencies already in `requirements.txt`.

## Phase 3: Iterative Refinement

Refine a previously generated recipe:

```python
from backend.food_synthesis import NutriPipeline

pipeline = NutriPipeline(use_phase2=True)

# Initial synthesis
result = pipeline.synthesize("I have eggs, flour, butter. Make something creative.")

# Refine based on feedback
refined = pipeline.refine(
    previous=result,
    feedback="Increase protein and explain chemistry in depth"
)

print(refined.recipe)               # Refined recipe
print(refined.changes)              # List of changes made
print(refined.chemical_justification)  # Why changes work chemically
print(refined.confidence)           # high/medium/low
```

### Supported Feedback Types
- **Macros**: "More protein", "Less fat", "Reduce carbs"
- **Texture**: "Make it crispier", "Softer please"
- **Flavor**: "More savory", "Less sweet"
- **Depth**: "Explain chemistry in more depth"
- **Caloric**: "Increase/decrease caloric density"

## Phase 4: Chemistry Claim Verification

Verify scientific claims in a synthesis result:

```python
# Assuming result is from synthesize() or refine()
verification = pipeline.verify(result)

print(f"Overall Confidence: {verification.overall_confidence}")

for claim in verification.verified_claims:
    print(f"✅ {claim.claim}")
    print(f"   Justification: {claim.justification}")

for claim in verification.flagged_claims:
    print(f"🚩 {claim.claim}")
    print(f"   Status: {claim.status}")
    print(f"   Reason: {claim.justification}")
    print(f"   Action: {claim.recommended_action}")
```

### Scientific Filters Enforced
- **Thermal Relevance**: Enzymes inactive >60°C are irrelevant
- **Causality**: Claims must materially affect outcome
- **In-Vitro**: Theoretical/lab-only mechanisms grounded as uncertain
- **In-Vitro**: Theoretical/lab-only mechanisms grounded as uncertain
- **Scope**: Nutrition must be estimated, not precise without source

## Phase 5: Nutrition Optimization Solver

Optimize ingredient ratios for nutritional goals:

```python
# Optimize recipe for max protein, under 600 calories
optimized = pipeline.optimize(
    result=result,
    goals={
        "maximize": "protein",
        "constraints": {
            "calories": {"max": 600}
        }
    }
)

print(f"Confidence: {optimized.confidence}")
print(f"Optimized Ratios: {optimized.optimized_ratios}")
print(f"Achieved Targets: {optimized.achieved_targets}")
print(f"Re-explained Recipe:\n{optimized.recipe_explanation}")
```

### Components
- **NutritionVectorizer**: Converts ingredients to numeric vectors using USDA data
- **NutritionConstraintSolver**: Uses `scipy.optimize` for deterministic solving
- **IngredientExtractor**: Parses recipe text into quantitative ingredients

## Demonstration

To verify the Phase 5 Nutrition Optimization system, run the following script:

```bash
python3 scripts/fast_demo_phase5.py
```

This script demonstrates the end-to-end pipeline (extraction, vectorization, solver, and re-explanation) using a mocked retriever to bypass heavy index loading.

For a full end-to-end run with real retrieval (requires ~10GB RAM and several minutes to load indices), use:
```bash
python3 scripts/demonstrate_phase5.py
```
