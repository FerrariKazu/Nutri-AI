"""
Nutri Phase 5: Nutrition Constraint Solver.

Uses scipy.optimize to solve for optimal ingredient proportions
that satisfy nutritional constraints while maintaining culinary feasibility.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field
import scipy.optimize

from backend.nutrition.vectorizer import NutritionVector

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of nutrition optimization."""
    optimized_ratios: Dict[str, float]  # Ingredient name -> new amount (g)
    achieved_targets: Dict[str, float]
    unmet_constraints: List[str]
    confidence: Literal["high", "medium", "low"]
    recipe_explanation: Optional[str] = None
    original_totals: Dict[str, float] = field(default_factory=dict)
    new_totals: Dict[str, float] = field(default_factory=dict)


class NutritionConstraintSolver:
    """Solves for optimal ingredient amounts."""

    def __init__(self):
        logger.info("NutritionConstraintSolver initialized")

    def solve(
        self,
        ingredients: List[Dict[str, Any]],
        goals: Dict[str, Any]
    ) -> OptimizationResult:
        """
        Solve optimization problem.
        
        Args:
            ingredients: List[dict(name, amount_g, vector)]
            goals: dict with 'constraints' and optional 'maximize'/'minimize'
                   e.g. {
                       "constraints": {"calories": {"max": 600}},
                       "maximize": "protein"
                   }
                   
        Returns:
            OptimizationResult
        """
        if not ingredients:
            return OptimizationResult({}, {}, ["No ingredients"], "low")

        names = [i['name'] for i in ingredients]
        x0 = np.array([i['amount_g'] for i in ingredients])
        vectors = [i['vector'] for i in ingredients]  # NutritionVector objects
        
        # 1. Define bounds (Safety: +/- 50% of original)
        bounds = [(val * 0.5, val * 1.5) for val in x0]
        
        # 2. Define constraints
        constraints = []
        user_constraints = goals.get("constraints", {})
        
        metrics = ["calories", "protein", "fat", "carbs", "fiber", "sugar", "sodium"]
        
        for metric in metrics:
            if metric in user_constraints:
                limit = user_constraints[metric]
                # Extract vector component for this metric
                coeffs = np.array([getattr(v, metric) / 100.0 for v in vectors]) # per gram
                
                if "max" in limit:
                    # sum(x * coeffs) <= max  =>  max - sum >= 0
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda x, c=coeffs, m=limit['max']: m - np.dot(x, c)
                    })
                if "min" in limit:
                    # sum(x * coeffs) >= min  =>  sum - min >= 0
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda x, c=coeffs, m=limit['min']: np.dot(x, c) - m
                    })
        
        # 3. Define Objective
        maximize_target = goals.get("maximize")
        minimize_target = goals.get("minimize")
        
        def objective(x):
            # Penalize deviation from original recipe (Culinary Feasibility)
            # sum((x - x0)^2 / x0^2) -> normalized deviation
            deviation_cost = np.sum(((x - x0) / (x0 + 1e-6))**2)
            
            if maximize_target and maximize_target in metrics:
                coeffs = np.array([getattr(v, maximize_target) / 100.0 for v in vectors])
                total = np.dot(x, coeffs)
                # Minimize negative total, plus deviation penalty/regularization
                return -total + (0.1 * deviation_cost)
            
            elif minimize_target and minimize_target in metrics:
                coeffs = np.array([getattr(v, minimize_target) / 100.0 for v in vectors])
                total = np.dot(x, coeffs)
                return total + (0.1 * deviation_cost)
            
            else:
                return deviation_cost

        # 4. Total Mass Constraint (Optional, keeping total mass roughly similar +/- 20%)
        # total_mass_orig = np.sum(x0)
        # constraints.append({'type': 'ineq', 'fun': lambda x: total_mass_orig * 1.2 - np.sum(x)})
        # constraints.append({'type': 'ineq', 'fun': lambda x: np.sum(x) - total_mass_orig * 0.8})

        # 5. Solve
        try:
            res = scipy.optimize.minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 100}
            )
            
            success = res.success
            x_opt = res.x
            
            # 6. Analyze Result
            optimized_ratios = {names[i]: float(x_opt[i]) for i in range(len(names))}
            
            # Calculate achieved totals
            new_totals = {m: 0.0 for m in metrics}
            orig_totals = {m: 0.0 for m in metrics}
            
            for i, vec in enumerate(vectors):
                for m in metrics:
                    val_per_g = getattr(vec, m) / 100.0
                    new_totals[m] += val_per_g * x_opt[i]
                    orig_totals[m] += val_per_g * x0[i]
            
            # Check unmet constraints
            unmet = []
            for metric, limit in user_constraints.items():
                val = new_totals.get(metric, 0)
                if "max" in limit and val > limit['max'] * 1.05: # 5% tolerance
                    unmet.append(f"{metric} > {limit['max']}")
                if "min" in limit and val < limit['min'] * 0.95:
                    unmet.append(f"{metric} < {limit['min']}")
            
            confidence = "high"
            if not success:
                confidence = "low"
                unmet.append("Optimization did not converge")
            elif unmet:
                confidence = "medium"
                
            return OptimizationResult(
                optimized_ratios=optimized_ratios,
                achieved_targets=new_totals,
                unmet_constraints=unmet,
                confidence=confidence,
                original_totals=orig_totals,
                new_totals=new_totals
            )
            
        except Exception as e:
            logger.error(f"Solver failed: {e}")
            return OptimizationResult({}, {}, [f"Solver error: {str(e)}"], "low")
