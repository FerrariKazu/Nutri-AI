# Nutri AI Food Synthesis System – Phases 1–13
*Generated on: 2026-01-02*

## Table of Contents
1. [Phase 1: Food Synthesis Engine](#phase-1-food-synthesis-engine)
2. [Phase 2: Intent Extraction & Constraints](#phase-2-intent-extraction--constraints)
3. [Phase 3: Multi-Factor Claim Verification](#phase-3-multi-factor-claim-verification)
4. [Phase 4: Automated Recipe Refinement](#phase-4-automated-recipe-refinement)
5. [Phase 5: Nutritional Optimization](#phase-5-nutritional-optimization)
6. [Phase 6: Sensory Prediction engine](#phase-6-sensory-prediction-engine)
7. [Phase 7: Sensory Optimization Loop](#phase-7-sensory-optimization-loop)
8. [Phase 8: Sensory Pareto Frontier](#phase-8-sensory-pareto-frontier)
9. [Phase 9: Preference Projection Layer](#phase-9-preference-projection-layer)
10. [Phase 10: Epistemic Explanation Control](#phase-10-epistemic-explanation-control)
11. [Phase 11: Counterfactual Utility](#phase-11-counterfactual-utility)
12. [Phase 12: Multi-Parameter Joint Reasoning](#phase-12-multi-parameter-joint-reasoning)
13. [Phase 13: Interactive Design Loop](#phase-13-interactive-design-loop)

---

## Phase 1: Food Synthesis Engine <a name="phase-1-food-synthesis-engine"></a>
**Objective:** Invent recipes from first principles using chemistry and science.
**Key Components:**
- `food_synthesis.py`
- `retriever.py`
**Highlights:** Uses RAG with dedicated chemical and nutritional vector stores.
```text
Query -> Retriever -> LLM -> Recipe
```

---

## Phase 2: Intent Extraction & Constraints <a name="phase-2-intent-extraction--constraints"></a>
**Objective:** Precisely extract user culinary intent and dietary constraints.
**Key Components:**
- `intent.py`
**Highlights:** Pydantic-based structured intent extraction.
```text
User Raw Text -> Extraction Logic -> Structured Intent
```

---

## Phase 3: Multi-Factor Claim Verification <a name="phase-3-multi-factor-claim-verification"></a>
**Objective:** Verify culinary and nutritional claims made in generated recipes.
**Key Components:**
- `claim_verifier.py`
**Highlights:** Atomic claim decomposition and scientific validation.
```text
Recipe -> Claim Splitter -> Verifier -> Report
```

---

## Phase 4: Automated Recipe Refinement <a name="phase-4-automated-recipe-refinement"></a>
**Objective:** Iteratively improve recipes based on verification feedback.
**Key Components:**
- `refinement.py`
**Highlights:** Closed-loop refinement cycle.
```text
Failed Claims -> Refinement Prompt -> Adjusted Recipe
```

---

## Phase 5: Nutritional Optimization <a name="phase-5-nutritional-optimization"></a>
**Objective:** Solve for exact nutritional targets using linear programming.
**Key Components:**
- `nutrition/solver.py`
**Highlights:** Guarantees dietary constraint satisfaction (e.g. <500mg Sodium).
```text
Ingredients -> Constraint Solver -> Optimized Weights
```

---

## Phase 6: Sensory Prediction engine <a name="phase-6-sensory-prediction-engine"></a>
**Objective:** Predict texture, flavor, and mouthfeel via physical properties.
**Key Components:**
- `sensory/predictor.py`
- `sensory/property_mapper.py`
**Highlights:** Mechanistic mapping from starch/moisture to crispness/tenderness.
```text
Ingredients -> Physical Properties -> Sensory Profile
```

---

## Phase 7: Sensory Optimization Loop <a name="phase-7-sensory-optimization-loop"></a>
**Objective:** Refine recipes specifically for sensory balance using a Critic-Planner loop.
**Key Components:**
- `sensory/optimizer.py`
**Highlights:** Critic identifies imbalances; Planner proposes physical adjustments.
```text
Profile -> Critic -> Planner -> Recipe Adjustment
```

---

## Phase 8: Sensory Pareto Frontier <a name="phase-8-sensory-pareto-frontier"></a>
**Objective:** Generate multiple non-dominated recipe variants (trade-offs).
**Key Components:**
- `sensory/frontier.py`
**Highlights:** Moves beyond 'one-best' to a landscape of valid trade-offs.
```text
Objectives -> Variant Gen -> Dominance Filtering -> Frontier
```

---

## Phase 9: Preference Projection Layer <a name="phase-9-preference-projection-layer"></a>
**Objective:** Select optimal variant based on explicit user signals (No ML).
**Key Components:**
- `sensory/selector.py`
**Highlights:** Deterministic dot-product selection from the Pareto frontier.
```text
User Signals -> Weight Vector -> Selection Result
```

---

## Phase 10: Epistemic Explanation Control <a name="phase-10-epistemic-explanation-control"></a>
**Objective:** Calibrate scientific explanations for different audiences.
**Key Components:**
- `sensory/explainer.py`
**Highlights:** Preserves facts and uncertainties while adapting tone.
```text
Scientific Data -> Mode (Casual/Tech) -> Calibrated Text
```

---

## Phase 11: Counterfactual Utility <a name="phase-11-counterfactual-utility"></a>
**Objective:** Answer 'What if' questions using sensitivity reasoning.
**Key Components:**
- `sensory/counterfactual_engine.py`
**Highlights:** Linear sensitivity projections from a static registry.
```text
Profile + Parameter Change -> Delta Prediction
```

---

## Phase 12: Multi-Parameter Joint Reasoning <a name="phase-12-multi-parameter-joint-reasoning"></a>
**Objective:** Reason about joint parameter shifts and interaction effects.
**Key Components:**
- `sensory/counterfactual_multi_engine.py`
**Highlights:** Handles interaction dry-out effects and physical feasibility.
```text
Multi-Deltas -> Interaction Layer -> Aggregate Impact
```

---

## Phase 13: Interactive Design Loop <a name="phase-13-interactive-design-loop"></a>
**Objective:** Let users iteratively refine recipes toward target sensory goals.
**Key Components:**
- `sensory/interactive_design_loop.py`
**Highlights:** State-less iteration tracking and minimal adjustment suggestions.
```text
User Refinement -> Multi-Simulation -> Suggestion -> Next Profile
```

---
