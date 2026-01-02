"""
Nutri Phase 6: Sensory Types
Defines the structure for sensory profiles and physical properties.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class SensoryProfile:
    """Predicted sensory attributes and their provenance (Phase 6.5)."""
    texture: Dict[str, float] = field(default_factory=lambda: {
        "surface_crust": 0.0,
        "structural_crispness": 0.0,
        "crispness": 0.0,
        "tenderness": 0.0,
        "chewiness": 0.0,
        "moistness": 0.0
    })
    flavor: Dict[str, float] = field(default_factory=lambda: {
        "umami": 0.0,
        "saltiness": 0.0,
        "sweetness": 0.0,
        "bitterness": 0.0
    })
    mouthfeel: Dict[str, float] = field(default_factory=lambda: {
        "richness": 0.0,
        "coating": 0.0,
        "astringency": 0.0
    })
    confidence: Dict[str, str] = field(default_factory=lambda: {
        "nutrition": "medium",
        "sensory_physics": "medium",
        "chemical_flavor": "medium",
        "overall": "medium"
    })
    provenance: Dict[str, bool] = field(default_factory=lambda: {
        "used_recipes_store": False,
        "used_open_nutrition": False
    })
    sensory_timeline: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "initial_bite": {},
        "mid_palate": {},
        "finish": {}
    })
    scientific_explanation: str = ""
    warnings: List[str] = field(default_factory=list)

@dataclass
class PhysicalProperties:
    """Mechanistic contributors to sensory perception (Phase 6.5)."""
    moisture_content: float = 0.0  # 0 to 1
    fat_fraction: float = 0.0      # 0 to 1
    protein_density: float = 0.0   # 0 to 1
    starch_gelatinization_potential: float = 0.0
    maillard_browning_potential: float = 0.0
    polyphenol_content: float = 0.0
    free_amino_acids: float = 0.0
    sodium_content_mg: float = 0.0
    sugar_content_g: float = 0.0   # Added for Phase 6.5 sweetness logic
    is_muscle_tissue: bool = False # Added for Phase 6.5 fiber modeling

@dataclass
class SensoryIssue:
    """A detected sensory extreme and its mechanistic cause."""
    dimension: str
    severity: str  # high, medium, low
    cause: str     # mechanistic cause
    value: float

@dataclass
class AdjustmentProposal:
    """A scientifically grounded adjustment to the recipe."""
    change: str
    mechanism: str
    expected_effect: Dict[str, float]

@dataclass
class OptimizationStep:
    """A single iteration of the sensory optimization loop."""
    iteration: int
    recipe: str
    profile: SensoryProfile
    issues: List[SensoryIssue]
    proposals: List[AdjustmentProposal]

@dataclass
class SensoryOptimizationResult:
    """Final result of the sensory optimization process."""
    final_recipe: str
    final_profile: SensoryProfile
    log: List[OptimizationStep]
    success: bool
    message: str
@dataclass
class SensoryVariant:
    """A recipe variant with a specific sensory trade-off."""
    name: str # e.g. "Crisp-Forward"
    recipe: str
    profile: SensoryProfile
    trade_offs: str # Human-readable explanation of trade-offs

@dataclass
class ParetoFrontierResult:
    """The collection of non-dominated sensory variants."""
    variants: List[SensoryVariant]
    objectives: Dict[str, str] # dimension -> goal (maximize/minimize)
@dataclass
class UserPreferences:
    """Explicit user signals for sensory selection."""
    eating_style: str = "balanced" # comfort, indulgent, light, performance
    time_constraint: str = "flexible" # short, flexible
    texture_preference: str = "balanced" # soft, crisp, balanced

@dataclass
class SelectionResult:
    """The result of projecting preferences onto the Pareto frontier."""
    selected_variant: SensoryVariant
    reasoning: List[str]
    scores: Dict[str, float]

@dataclass
class ExplanationResult:
    """An audience-calibrated explanation of the sensory profile."""
    mode: str # casual, culinary, scientific, technical
    content: str
    preserved_warnings: List[str]
    confidence_statement: str

@dataclass
class CounterfactualReport:
    """Predicted sensory changes under parameter modifications (Phase 11)."""
    parameter: str
    delta: float
    predicted_changes: Dict[str, float] # dimension -> delta
    explanation: str
    confidence: str # high, medium, low

@dataclass
class SensitivityRanking:
    """Ranking of parameters by their impact on a specific sensory dimension (Phase 11)."""
    dimension: str
    rankings: List[Dict[str, Any]] # list of {parameter: str, strength: float}

@dataclass
class MultiCounterfactualReport:
    """Predicted sensory changes under multiple parameter modifications (Phase 12)."""
    deltas: Dict[str, float] # parameter -> delta
    predicted_changes: Dict[str, float] # dimension -> total delta
    feasibility_warnings: List[str]
    explanation: str
    confidence: str
@dataclass
class IterationState:
    """A single step in the interactive design loop (Phase 13)."""
    iteration_number: int
    proposed_deltas: Dict[str, float]
    predicted_changes: Dict[str, float]
    feasibility_warnings: List[str]
    recommendation: str
    explanation: ExplanationResult

@dataclass
class DesignSessionResult:
    """The full history of an interactive design session."""
    base_recipe: str
    target_goals: Dict[str, str] # e.g. {"crispness": "high"}
    history: List[IterationState]
    current_profile: SensoryProfile
