"""
Nutri Phase 7: Sensory Optimization Engine
Implements the closed-loop optimization of recipes based on sensory profiles.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import (
    SensoryProfile, 
    SensoryIssue, 
    AdjustmentProposal, 
    OptimizationStep, 
    SensoryOptimizationResult
)
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """Analyze the following sensory profile and detect undesirable sensory imbalances or extremes.
Focus on:
- High Chewiness (>0.7 for muscle tissue)
- Low Tenderness (<0.5 for proteins)
- Excessive Crust (>0.8 if not requested)
- Flavor imbalances (e.g. extremely low saltiness <0.2 or extreme bitterness >0.5)

For each issue, identify the MECHANCISTIC CAUSE based on physics and chemistry.

Sensory Profile:
{profile_json}

Rules:
1. No subjective language (e.g. "too salty", "unpleasant").
2. Use mechanistic terms (e.g. "excessive sodium concentration", "fiber shortening", "lipid-induced coating").
3. Return issue severity (high/medium/low).

Return ONLY JSON:
{{
  "issues": [
    {{ "dimension": "name", "severity": "high|medium|low", "cause": "mechanistic explanation", "value": float }}
  ]
}}"""

PLANNER_PROMPT = """Given the sensory issues and the current recipe, propose minimal, scientifically grounded adjustments to the techniques or heat sequencing.
DO NOT change core ingredients unless absolutely necessary for chemistry (e.g. adding acid to balance bitterness).

Recipe:
{recipe}

Sensory Issues:
{issues_json}

Rules:
1. Propose changes to heat intensity, duration, or sequencing (e.g. "rest for 10 min", "reduce sear temp").
2. Each proposal must include the scientific mechanism and expected numeric effect on the sensory dimensions.

Return ONLY JSON:
{{
  "proposals": [
    {{
      "change": "instruction level change",
      "mechanism": "scientific explanation",
      "expected_effect": {{ "attribute_name": delta_float }}
    }}
  ]
}}"""

class SensoryCritic:
    """Detects sensory extremes and identifies mechanistic causes."""
    def __init__(self, llm: LLMQwen3):
        self.llm = llm

    def critique(self, profile: SensoryProfile) -> List[SensoryIssue]:
        profile_data = {
            "texture": profile.texture,
            "flavor": profile.flavor,
            "mouthfeel": profile.mouthfeel
        }
        # Skip critique if profile is empty/invalid
        if all(v == 0 for v in profile.texture.values()):
            return []

        messages = [
            {"role": "system", "content": "You are a mechanistic sensory critic. Analyze profiles for extremes (>0.8 or <0.2). Output a JSON object with an 'issues' key containing a list."},
            {"role": "user", "content": CRITIC_PROMPT.format(profile_json=json.dumps(profile_data))}
        ]
        try:
            response = self.llm.generate_text(messages, temperature=0.0, json_mode=True)
            data = self._parse_json(response)
            issues_list = data.get("issues", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            
            issues = []
            for issue in issues_list:
                if isinstance(issue, dict):
                    issues.append(SensoryIssue(
                        dimension=issue.get("dimension", "unknown"),
                        severity=issue.get("severity", "medium"),
                        cause=issue.get("cause", "unknown mechanism"),
                        value=float(issue.get("value", 0.0))
                    ))
            return issues
        except Exception as e:
            logger.error(f"Critic failed: {e}")
            return []

    def _parse_json(self, response: str) -> Any:
        try:
            # Clean up potential markdown blocks if LLM failed json_mode
            clean_res = response.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[-1].split("```")[0].strip()
            return json.loads(clean_res)
        except:
            # Fallback to extraction
            try:
                import re
                match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except:
                pass
        return {}

class AdjustmentPlanner:
    """Proposes scientifically grounded adjustments to resolve sensory issues."""
    def __init__(self, llm: LLMQwen3):
        self.llm = llm

    def plan(self, recipe: str, issues: List[SensoryIssue]) -> List[AdjustmentProposal]:
        issues_data = [
            {"dim": i.dimension, "sev": i.severity, "cause": i.cause, "val": i.value} 
            for i in issues
        ]
        messages = [
            {"role": "system", "content": "You are a food science adjustment planner. Output a JSON object with a 'proposals' key containing a list."},
            {"role": "user", "content": PLANNER_PROMPT.format(
                recipe=recipe, 
                issues_json=json.dumps(issues_data)
            )}
        ]
        try:
            response = self.llm.generate_text(messages, temperature=0.0, json_mode=True)
            data = self._parse_json(response)
            proposals_list = data.get("proposals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            
            proposals = []
            for prop in proposals_list:
                if isinstance(prop, dict):
                    proposals.append(AdjustmentProposal(
                        change=prop.get("change", "instruction change"),
                        mechanism=prop.get("mechanism", "mechanistic justification"),
                        expected_effect=prop.get("expected_effect", {})
                    ))
            return proposals
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            return []

    def _parse_json(self, response: str) -> Any:
        # Reuse same robust parser
        try:
            clean_res = response.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[-1].split("```")[0].strip()
            return json.loads(clean_res)
        except:
            try:
                import re
                match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except:
                pass
        return {}

class SensoryOptimizer:
    """Orchestrates the closed-loop sensory optimization process."""
    def __init__(self, engine: Any, predictor: Any):
        self.engine = engine # FoodSynthesisEngine
        self.predictor = predictor # SensoryPredictor
        self.critic = SensoryCritic(engine.llm)
        self.planner = AdjustmentPlanner(engine.llm)

    def optimize(self, initial_recipe: str, properties_list: Any, provenance: Any, max_iter: int = 3) -> SensoryOptimizationResult:
        current_recipe = initial_recipe
        log = []
        
        for i in range(max_iter):
            logger.info(f"Sensory Optimization Iteration {i+1}")
            
            # 1. Predict
            profile = self.predictor.predict(current_recipe, properties_list, provenance)
            
            # 2. Critique
            issues = self.critic.critique(profile)
            if not issues:
                logger.info("No sensory issues detected by critic.")
                return SensoryOptimizationResult(
                    final_recipe=current_recipe,
                    final_profile=profile,
                    log=log,
                    success=True,
                    message="No sensory issues detected."
                )
            
            logger.info(f"Critic detected {len(issues)} issues.")
                
            # 3. Plan
            proposals = self.planner.plan(current_recipe, issues)
            if not proposals:
                logger.info("Issues detected but no adjustment proposals generated.")
                return SensoryOptimizationResult(
                    final_recipe=current_recipe,
                    final_profile=profile,
                    log=log,
                    success=False,
                    message="Issues detected but no valid adjustments found."
                )
            
            logger.info(f"Planner generated {len(proposals)} proposals.")
                
            # Store step
            step = OptimizationStep(
                iteration=i+1,
                recipe=current_recipe,
                profile=profile,
                issues=issues,
                proposals=proposals
            )
            log.append(step)
            
            # 4. Adjust (Regenerate with feedback)
            feedback = "\n".join([f"- {p.change} (Mechanism: {p.mechanism})" for p in proposals])
            refinement_prompt = f"Adjust the following recipe to resolve these sensory issues:\n{feedback}\n\nOriginal Recipe:\n{current_recipe}"
            
            # Use engine to refine the recipe instructions
            try:
                # We use a direct LLM call here to apply the precise adjustments
                messages = [
                    {"role": "system", "content": "You are a food science refiner. Apply the requested technical adjustments precisely without changing core ingredients unless instructed."},
                    {"role": "user", "content": refinement_prompt}
                ]
                current_recipe = self.engine.llm.generate_text(messages, temperature=0.1)
            except Exception as e:
                logger.error(f"Adjustment application failed: {e}")
                break

        # Final evaluation
        final_profile = self.predictor.predict(current_recipe, properties_list, provenance)
        return SensoryOptimizationResult(
            final_recipe=current_recipe,
            final_profile=final_profile,
            log=log,
            success=True,
            message=f"Optimization completed after {len(log)} iterations."
        )
