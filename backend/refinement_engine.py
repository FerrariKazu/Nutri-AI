"""
Nutri Phase 3: Iterative Refinement Engine

Enables multi-turn refinement of invented recipes through:
- Feedback parsing into structured deltas
- Constraint merging with previous context
- Re-synthesis with chemical justification
- Change tracking and explanation enforcement

This module does NOT replace any Phase 1/2 components.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add project root to path for direct execution
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class AdjustmentDirection(str, Enum):
    """Direction of adjustment for macros/properties."""
    INCREASE = "increase"
    DECREASE = "decrease"
    UNCHANGED = "unchanged"


@dataclass
class MacroAdjustments:
    """Macro nutrient adjustment deltas."""
    protein: AdjustmentDirection = AdjustmentDirection.UNCHANGED
    fat: AdjustmentDirection = AdjustmentDirection.UNCHANGED
    carbs: AdjustmentDirection = AdjustmentDirection.UNCHANGED

    def to_dict(self) -> Dict[str, str]:
        return {
            "protein": self.protein.value,
            "fat": self.fat.value,
            "carbs": self.carbs.value
        }


@dataclass
class FeedbackDelta:
    """
    Structured feedback delta extracted from user input.
    
    This is the required Feedback Schema from Phase 3 spec.
    """
    adjustments: Dict[str, Any] = field(default_factory=lambda: {
        "macros": {
            "protein": "unchanged",
            "fat": "unchanged",
            "carbs": "unchanged"
        },
        "texture": [],
        "flavor_profile": [],
        "caloric_density": "unchanged"
    })
    explanation_depth: str = "scientific"  # casual | scientific
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_empty(self) -> bool:
        """Check if this is a no-op feedback (no changes requested)."""
        macros = self.adjustments.get("macros", {})
        return (
            macros.get("protein") == "unchanged" and
            macros.get("fat") == "unchanged" and
            macros.get("carbs") == "unchanged" and
            self.adjustments.get("caloric_density") == "unchanged" and
            len(self.adjustments.get("texture", [])) == 0 and
            len(self.adjustments.get("flavor_profile", [])) == 0 and
            len(self.notes) == 0
        )


@dataclass
class RefinementResult:
    """
    Result from refinement operation.
    
    Required output structure from Phase 3 spec.
    """
    recipe: str
    changes: List[str]
    chemical_justification: str
    nutrition_estimate: Dict[str, Any]
    confidence: Literal["high", "medium", "low"]
    warnings: List[str] = field(default_factory=list)
    
    # Additional tracking
    previous_recipe: Optional[str] = None
    merged_constraints: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# FEEDBACK PARSER
# =============================================================================

FEEDBACK_PARSER_PROMPT = """You are a feedback parser for a food synthesis system.

Your task is to extract structured adjustment deltas from user feedback about a recipe.

You must identify:
- Macro adjustments (protein, fat, carbs): "increase" | "decrease" | "unchanged"
- Texture changes requested (list of strings like "crispy", "softer", "chewy")
- Flavor profile changes (list of strings like "more savory", "less sweet")
- Caloric density adjustment: "increase" | "decrease" | "unchanged"
- Explanation depth preference: "casual" | "scientific"
- Any other notes

You must NOT:
- Suggest recipes
- Interpret chemistry
- Add ingredients not mentioned

Return valid JSON only, matching this schema:
{
  "adjustments": {
    "macros": {
      "protein": "increase | decrease | unchanged",
      "fat": "increase | decrease | unchanged",
      "carbs": "increase | decrease | unchanged"
    },
    "texture": [],
    "flavor_profile": [],
    "caloric_density": "increase | decrease | unchanged"
  },
  "explanation_depth": "casual | scientific",
  "notes": []
}"""


class FeedbackParser:
    """
    Parses user feedback into structured FeedbackDelta.
    
    Uses LLM to understand natural language feedback and convert to
    structured constraint deltas.
    """
    
    def __init__(self, model_name: str = "qwen3:8b"):
        """Initialize feedback parser."""
        self.llm = LLMQwen3(model_name=model_name)
        logger.info("FeedbackParser initialized")
    
    def parse(self, feedback: str) -> FeedbackDelta:
        """
        Parse user feedback into structured delta.
        
        Args:
            feedback: Natural language feedback from user
            
        Returns:
            FeedbackDelta with extracted adjustments
        """
        if not feedback or not feedback.strip():
            logger.info("Empty feedback - returning empty delta")
            return FeedbackDelta()
        
        logger.info(f"Parsing feedback: {feedback[:100]}...")
        
        messages = [
            {"role": "system", "content": FEEDBACK_PARSER_PROMPT},
            {"role": "user", "content": f"Parse this feedback: {feedback}"}
        ]
        
        try:
            response = self.llm.generate_text(
                messages=messages,
                max_new_tokens=512,
                temperature=0.1  # Low temperature for structured extraction
            )
            
            logger.debug(f"Parser raw output: {response}")
            
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Feedback parsing failed: {e}")
            # Return fallback delta with notes
            return FeedbackDelta(notes=[f"Unparsed feedback: {feedback}"])
    
    def _parse_json_response(self, response: str) -> FeedbackDelta:
        """Parse JSON from LLM response into FeedbackDelta."""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                
                return FeedbackDelta(
                    adjustments=data.get('adjustments', {
                        "macros": {"protein": "unchanged", "fat": "unchanged", "carbs": "unchanged"},
                        "texture": [],
                        "flavor_profile": [],
                        "caloric_density": "unchanged"
                    }),
                    explanation_depth=data.get('explanation_depth', 'scientific'),
                    notes=data.get('notes', [])
                )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
        
        return FeedbackDelta()


# =============================================================================
# CONSTRAINT MERGER
# =============================================================================

class ConstraintMerger:
    """
    Merges original intent, feedback deltas, and previous context.
    
    Rules:
    - New constraints override old ones
    - Conflicting constraints are preserved and surfaced
    - Nothing is silently dropped
    """
    
    def merge(
        self,
        original_intent: Dict[str, Any],
        feedback_delta: FeedbackDelta,
        previous_recipe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge constraints from all sources.
        
        Args:
            original_intent: Intent from Phase 2 IntentAgent
            feedback_delta: Parsed feedback from user
            previous_recipe: Previously generated recipe text
            
        Returns:
            Merged constraints with conflict tracking
        """
        logger.info("Merging constraints...")
        
        merged = {
            # Preserve original intent
            "goal": original_intent.get("goal", "invent_meal"),
            "ingredients": original_intent.get("ingredients", []),
            "equipment": original_intent.get("equipment", []),
            "dietary_constraints": original_intent.get("dietary_constraints", {}),
            "nutritional_goals": original_intent.get("nutritional_goals", {}),
            "time_limit_minutes": original_intent.get("time_limit_minutes"),
            "explanation_depth": original_intent.get("explanation_depth", "scientific"),
            
            # Add refinement-specific fields
            "adjustments": feedback_delta.adjustments,
            "refinement_notes": feedback_delta.notes,
            "previous_recipe": previous_recipe,
            "conflicts": []
        }
        
        # Override explanation depth if feedback specifies
        if feedback_delta.explanation_depth:
            merged["explanation_depth"] = feedback_delta.explanation_depth
        
        # Detect conflicts
        conflicts = self._detect_conflicts(original_intent, feedback_delta)
        merged["conflicts"] = conflicts
        
        if conflicts:
            logger.warning(f"Detected {len(conflicts)} constraint conflicts")
        
        logger.info(f"Merged constraints: {json.dumps(merged, default=str)[:200]}...")
        return merged
    
    def _detect_conflicts(
        self,
        original: Dict[str, Any],
        delta: FeedbackDelta
    ) -> List[str]:
        """Detect conflicts between original constraints and feedback."""
        conflicts = []
        
        macros = delta.adjustments.get("macros", {})
        nutritional = original.get("nutritional_goals") or {}
        
        # Check for conflicts with existing nutritional goals
        if macros.get("fat") == "increase" and nutritional.get("low_fat"):
            conflicts.append("Conflict: User requested more fat but original goal is low-fat")
        
        if macros.get("carbs") == "increase" and nutritional.get("low_carb"):
            conflicts.append("Conflict: User requested more carbs but original goal is low-carb")
        
        if macros.get("protein") == "decrease" and nutritional.get("high_protein"):
            conflicts.append("Conflict: User requested less protein but original goal is high-protein")
        
        # Check dietary constraint conflicts with texture requests
        textures = delta.adjustments.get("texture", [])
        dietary = original.get("dietary_constraints") or {}
        
        if "crispy" in textures and dietary.get("oil_free"):
            conflicts.append("Conflict: Crispy texture requested but oil-free constraint exists")
        
        return conflicts


# =============================================================================
# REFINEMENT ENGINE
# =============================================================================

REFINEMENT_SYSTEM_PROMPT = """You are Nutri, a food formulation and cooking science system.

You have already invented a recipe. The user has provided feedback for refinement.

Your task is to REFINE the existing recipe based on the feedback, while:
- Maintaining chemical and physical feasibility
- Explaining WHAT changed and WHY
- Providing CHEMICAL JUSTIFICATION for every change
- Preserving the core concept of the original dish

You MUST structure your response with these sections:

## Refined Recipe
[The improved recipe with clear steps]

## Changes Made
[Bullet list of specific changes]

## Chemical Justification
[Scientific explanation of why each change works chemically]

## Nutrition Estimate
[Updated nutritional estimates - MUST be labeled as "Estimated" with confidence level]

If a requested refinement is IMPOSSIBLE (violates physics or chemistry), you MUST:
1. Refuse the impossible part
2. Explain why it's impossible
3. Suggest the closest feasible alternative

NEVER apply changes without justification.
NEVER hallucinate chemical reactions.
NEVER silently ignore constraints.

─────────────────────────────────────────────────────────────
SCIENTIFIC ACCURACY RULES (MANDATORY)
─────────────────────────────────────────────────────────────

STARCH AND UMAMI:
- Starch hydrolysis produces SUGARS (glucose, maltose), NOT glutamate
- Umami (glutamate) arises ONLY from protein degradation
- ✅ CORRECT: "Starch modifies viscosity and flavor release timing"
- ❌ WRONG: "Starch contributes glutamate via hydrolysis"

ENZYME CLAIMS AT COOKING TEMPERATURES:
- Most enzymes denature and become inactive at cooking temperatures (>60°C)
- Do NOT cite enzyme inhibition during cooking as a mechanism
- ✅ CORRECT: "Rosemary acts as an antioxidant, reducing lipid oxidation"
- ❌ WRONG: "Rosemary inhibits lipase activity" (lipase is inactive when cooking)

NUTRITION ESTIMATES:
- Label all values as "Estimated" or "Approximate"
- Include confidence level: high | medium | low
- Use language: "Based on standard USDA averages"

─────────────────────────────────────────────────────────────
GLOBAL SAFETY RULE (CRITICAL)
─────────────────────────────────────────────────────────────

If a biochemical or molecular claim does NOT materially affect:
- Cooking outcomes
- Texture
- Flavor
- Nutrition

Then it MUST be framed as secondary or uncertain, OR omitted entirely.

Examples to OMIT:
- In-vitro enzyme inhibition
- Heat-inactivated pathways
- Sensory-irrelevant molecular trivia"""


class RefinementEngine:
    """
    Phase 3 Refinement Engine.
    
    Orchestrates re-synthesis with:
    - Merged constraints
    - Previous recipe context
    - Chemical justification enforcement
    - Change tracking
    """
    
    def __init__(self, model_name: str = "qwen3:8b"):
        """Initialize refinement engine."""
        self.llm = LLMQwen3(model_name=model_name)
        self.feedback_parser = FeedbackParser(model_name=model_name)
        self.constraint_merger = ConstraintMerger()
        logger.info("RefinementEngine initialized")
    
    def refine(
        self,
        previous_recipe: str,
        original_intent: Dict[str, Any],
        feedback: str,
        retrieved_docs: Optional[List[Dict[str, Any]]] = None
    ) -> RefinementResult:
        """
        Refine a recipe based on user feedback.
        
        Args:
            previous_recipe: The previously generated recipe
            original_intent: Original intent from Phase 2
            feedback: User's refinement feedback
            retrieved_docs: Optional additional retrieved knowledge
            
        Returns:
            RefinementResult with refined recipe and justification
        """
        logger.info(f"Refining recipe with feedback: {feedback[:100]}...")
        
        # Step 1: Parse feedback into structured delta
        delta = self.feedback_parser.parse(feedback)
        logger.info(f"Parsed feedback delta: {delta.to_dict()}")
        
        # Step 2: Handle no-op case
        if delta.is_empty():
            logger.info("Empty feedback - returning previous recipe unchanged")
            return RefinementResult(
                recipe=previous_recipe,
                changes=["No changes requested"],
                chemical_justification="No refinement needed - recipe unchanged.",
                nutrition_estimate={},
                confidence="high",
                warnings=["No specific feedback provided"],
                previous_recipe=previous_recipe,
                merged_constraints=original_intent
            )
        
        # Step 3: Merge constraints
        merged = self.constraint_merger.merge(
            original_intent=original_intent,
            feedback_delta=delta,
            previous_recipe=previous_recipe
        )
        
        # Step 4: Build refinement prompt
        prompt = self._build_refinement_prompt(
            previous_recipe=previous_recipe,
            merged_constraints=merged,
            delta=delta,
            retrieved_docs=retrieved_docs
        )
        
        # Step 5: Execute refinement
        messages = [
            {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm.generate_text(
                messages=messages,
                max_new_tokens=4096,
                temperature=0.4
            )
            
            logger.info(f"Refinement output length: {len(response)} chars")
            
            # Step 6: Parse and validate response
            result = self._parse_refinement_response(
                response=response,
                previous_recipe=previous_recipe,
                merged_constraints=merged,
                conflicts=merged.get("conflicts", [])
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return RefinementResult(
                recipe=previous_recipe,
                changes=["Refinement failed"],
                chemical_justification=f"Error: {str(e)}",
                nutrition_estimate={},
                confidence="low",
                warnings=[f"Refinement error: {str(e)}"],
                previous_recipe=previous_recipe
            )
    
    def _build_refinement_prompt(
        self,
        previous_recipe: str,
        merged_constraints: Dict[str, Any],
        delta: FeedbackDelta,
        retrieved_docs: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build the refinement prompt for the LLM."""
        
        # Build context from retrieved docs
        context = ""
        if retrieved_docs:
            context_parts = []
            for doc in retrieved_docs[:5]:
                context_parts.append(doc.get("text", "")[:300])
            context = "\n".join(context_parts)
        
        # Build adjustment description
        adjustments_desc = []
        macros = delta.adjustments.get("macros", {})
        
        if macros.get("protein") == "increase":
            adjustments_desc.append("Increase protein content")
        elif macros.get("protein") == "decrease":
            adjustments_desc.append("Decrease protein content")
        
        if macros.get("fat") == "increase":
            adjustments_desc.append("Increase fat content")
        elif macros.get("fat") == "decrease":
            adjustments_desc.append("Decrease fat content")
        
        if macros.get("carbs") == "increase":
            adjustments_desc.append("Increase carbohydrate content")
        elif macros.get("carbs") == "decrease":
            adjustments_desc.append("Decrease carbohydrate content")
        
        textures = delta.adjustments.get("texture", [])
        if textures:
            adjustments_desc.append(f"Modify texture: {', '.join(textures)}")
        
        flavors = delta.adjustments.get("flavor_profile", [])
        if flavors:
            adjustments_desc.append(f"Adjust flavor: {', '.join(flavors)}")
        
        if delta.adjustments.get("caloric_density") == "increase":
            adjustments_desc.append("Increase caloric density")
        elif delta.adjustments.get("caloric_density") == "decrease":
            adjustments_desc.append("Decrease caloric density")
        
        # Build conflicts warning
        conflicts_section = ""
        conflicts = merged_constraints.get("conflicts", [])
        if conflicts:
            conflicts_section = f"""
## ⚠️ DETECTED CONFLICTS
{chr(10).join('- ' + c for c in conflicts)}

You MUST acknowledge these conflicts and explain how you will handle them.
"""
        
        prompt = f"""## Previous Recipe
{previous_recipe}

## Requested Adjustments
{chr(10).join('- ' + a for a in adjustments_desc) if adjustments_desc else '- No specific adjustments'}

## Additional Notes
{chr(10).join('- ' + n for n in delta.notes) if delta.notes else '- None'}

## Explanation Depth
{merged_constraints.get('explanation_depth', 'scientific')}
{conflicts_section}
## Available Ingredients
{', '.join(merged_constraints.get('ingredients', [])) or 'Use ingredients from original recipe'}

{f'## Scientific Context{chr(10)}{context}' if context else ''}

Refine the recipe according to the adjustments. You MUST:
1. Make the specific changes requested
2. Explain each change
3. Provide chemical justification
4. Update nutrition estimates
5. If any change is impossible, explain why and suggest alternatives"""
        
        return prompt
    
    def _parse_refinement_response(
        self,
        response: str,
        previous_recipe: str,
        merged_constraints: Dict[str, Any],
        conflicts: List[str]
    ) -> RefinementResult:
        """Parse LLM response into RefinementResult."""
        
        # Extract sections from response
        recipe = response
        changes = []
        justification = ""
        nutrition = {}
        warnings = list(conflicts)  # Start with known conflicts
        
        # Try to extract structured sections
        if "## Changes Made" in response or "## Changes" in response:
            parts = response.split("## ")
            for part in parts:
                if part.lower().startswith("refined recipe"):
                    recipe = part.split("\n", 1)[1] if "\n" in part else part
                elif part.lower().startswith("changes"):
                    changes_text = part.split("\n", 1)[1] if "\n" in part else part
                    changes = [line.strip("- ").strip() for line in changes_text.split("\n") if line.strip().startswith("-")]
                elif part.lower().startswith("chemical justification"):
                    justification = part.split("\n", 1)[1] if "\n" in part else part
                elif part.lower().startswith("nutrition"):
                    # Extract nutrition estimates
                    nutrition_text = part.split("\n", 1)[1] if "\n" in part else ""
                    nutrition = {"raw_estimate": nutrition_text.strip()}
        
        # Validate justification exists
        if not justification:
            # Try to find inline justification
            if "because" in response.lower() or "chemically" in response.lower():
                justification = "See inline chemical explanations in recipe."
            else:
                warnings.append("Warning: No explicit chemical justification provided")
                justification = "Implicit justification in recipe steps."
        
        # Determine confidence
        confidence = "high"
        if conflicts:
            confidence = "medium"
        if warnings and len(warnings) > 1:
            confidence = "low"
        if "impossible" in response.lower() or "cannot" in response.lower():
            confidence = "medium"
        
        # Check for refusal indicators
        if "not possible" in response.lower() or "impossible" in response.lower():
            warnings.append("Some requested changes may have been refused due to feasibility")
        
        return RefinementResult(
            recipe=recipe,
            changes=changes if changes else ["Recipe refined (see details)"],
            chemical_justification=justification,
            nutrition_estimate=nutrition,
            confidence=confidence,
            warnings=warnings,
            previous_recipe=previous_recipe,
            merged_constraints=merged_constraints
        )


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("NUTRI PHASE 3: REFINEMENT ENGINE TEST")
    print("=" * 60)
    
    # Test feedback parser
    parser = FeedbackParser()
    
    test_feedbacks = [
        "More protein please",
        "Make it crispier and less fatty",
        "Explain the chemistry in more depth",
        "Increase protein but keep it low fat"
    ]
    
    for fb in test_feedbacks:
        print(f"\nFeedback: {fb}")
        delta = parser.parse(fb)
        print(f"Parsed: {json.dumps(delta.to_dict(), indent=2)}")
    
    print("=" * 60)
