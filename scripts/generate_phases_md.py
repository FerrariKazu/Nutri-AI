"""
Nutri Documentation Generator: Phases 1–13
Generates a comprehensive summary of the Nutri-AI food synthesis system.
"""

import os
from datetime import datetime

PHASES_DATA = [
    {
        "number": 1,
        "name": "Food Synthesis Engine",
        "objective": "Invent recipes from first principles using chemistry and science.",
        "components": ["food_synthesis.py", "retriever.py"],
        "highlights": "Uses RAG with dedicated chemical and nutritional vector stores.",
        "ascii": "Query -> Retriever -> LLM -> Recipe"
    },
    {
        "number": 2,
        "name": "Intent Extraction & Constraints",
        "objective": "Precisely extract user culinary intent and dietary constraints.",
        "components": ["intent.py"],
        "highlights": "Pydantic-based structured intent extraction.",
        "ascii": "User Raw Text -> Extraction Logic -> Structured Intent"
    },
    {
        "number": 3,
        "name": "Multi-Factor Claim Verification",
        "objective": "Verify culinary and nutritional claims made in generated recipes.",
        "components": ["claim_verifier.py"],
        "highlights": "Atomic claim decomposition and scientific validation.",
        "ascii": "Recipe -> Claim Splitter -> Verifier -> Report"
    },
    {
        "number": 4,
        "name": "Automated Recipe Refinement",
        "objective": "Iteratively improve recipes based on verification feedback.",
        "components": ["refinement.py"],
        "highlights": "Closed-loop refinement cycle.",
        "ascii": "Failed Claims -> Refinement Prompt -> Adjusted Recipe"
    },
    {
        "number": 5,
        "name": "Nutritional Optimization",
        "objective": "Solve for exact nutritional targets using linear programming.",
        "components": ["nutrition/solver.py"],
        "highlights": "Guarantees dietary constraint satisfaction (e.g. <500mg Sodium).",
        "ascii": "Ingredients -> Constraint Solver -> Optimized Weights"
    },
    {
        "number": 6,
        "name": "Sensory Prediction engine",
        "objective": "Predict texture, flavor, and mouthfeel via physical properties.",
        "components": ["sensory/predictor.py", "sensory/property_mapper.py"],
        "highlights": "Mechanistic mapping from starch/moisture to crispness/tenderness.",
        "ascii": "Ingredients -> Physical Properties -> Sensory Profile"
    },
    {
        "number": 7,
        "name": "Sensory Optimization Loop",
        "objective": "Refine recipes specifically for sensory balance using a Critic-Planner loop.",
        "components": ["sensory/optimizer.py"],
        "highlights": "Critic identifies imbalances; Planner proposes physical adjustments.",
        "ascii": "Profile -> Critic -> Planner -> Recipe Adjustment"
    },
    {
        "number": 8,
        "name": "Sensory Pareto Frontier",
        "objective": "Generate multiple non-dominated recipe variants (trade-offs).",
        "components": ["sensory/frontier.py"],
        "highlights": "Moves beyond 'one-best' to a landscape of valid trade-offs.",
        "ascii": "Objectives -> Variant Gen -> Dominance Filtering -> Frontier"
    },
    {
        "number": 9,
        "name": "Preference Projection Layer",
        "objective": "Select optimal variant based on explicit user signals (No ML).",
        "components": ["sensory/selector.py"],
        "highlights": "Deterministic dot-product selection from the Pareto frontier.",
        "ascii": "User Signals -> Weight Vector -> Selection Result"
    },
    {
        "number": 10,
        "name": "Epistemic Explanation Control",
        "objective": "Calibrate scientific explanations for different audiences.",
        "components": ["sensory/explainer.py"],
        "highlights": "Preserves facts and uncertainties while adapting tone.",
        "ascii": "Scientific Data -> Mode (Casual/Tech) -> Calibrated Text"
    },
    {
        "number": 11,
        "name": "Counterfactual Utility",
        "objective": "Answer 'What if' questions using sensitivity reasoning.",
        "components": ["sensory/counterfactual_engine.py"],
        "highlights": "Linear sensitivity projections from a static registry.",
        "ascii": "Profile + Parameter Change -> Delta Prediction"
    },
    {
        "number": 12,
        "name": "Multi-Parameter Joint Reasoning",
        "objective": "Reason about joint parameter shifts and interaction effects.",
        "components": ["sensory/counterfactual_multi_engine.py"],
        "highlights": "Handles interaction dry-out effects and physical feasibility.",
        "ascii": "Multi-Deltas -> Interaction Layer -> Aggregate Impact"
    },
    {
        "number": 13,
        "name": "Interactive Design Loop",
        "objective": "Let users iteratively refine recipes toward target sensory goals.",
        "components": ["sensory/interactive_design_loop.py"],
        "highlights": "State-less iteration tracking and minimal adjustment suggestions.",
        "ascii": "User Refinement -> Multi-Simulation -> Suggestion -> Next Profile"
    }
]

def generate_markdown(output_path: str):
    now = datetime.now().strftime("%Y-%m-%d")
    md = [
        "# Nutri AI Food Synthesis System – Phases 1–13",
        f"*Generated on: {now}*",
        "",
        "## Table of Contents"
    ]
    
    for p in PHASES_DATA:
        anchor = f"phase-{p['number']}-{p['name'].lower().replace(' ', '-').replace('&', '').replace('–', '-')}"
        md.append(f"{p['number']}. [Phase {p['number']}: {p['name']}](#{anchor})")
    
    md.append("\n---\n")
    
    for p in PHASES_DATA:
        anchor = f"phase-{p['number']}-{p['name'].lower().replace(' ', '-').replace('&', '').replace('–', '-')}"
        md.append(f"## Phase {p['number']}: {p['name']} <a name=\"{anchor}\"></a>")
        md.append(f"**Objective:** {p['objective']}")
        md.append("**Key Components:**")
        for comp in p['components']:
            md.append(f"- `{comp}`")
        md.append(f"**Highlights:** {p['highlights']}")
        if "ascii" in p:
            md.append("```text")
            md.append(p["ascii"])
            md.append("```")
        md.append("\n---\n")
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(md))
    
    print(f"Successfully generated {output_path}")

if __name__ == "__main__":
    import sys
    path = "docs/Nutri_Phases.md"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    generate_markdown(path)
