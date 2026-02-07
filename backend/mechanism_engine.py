import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

StepType = Literal["compound", "interaction", "physiology", "outcome"]
EvidenceSource = Literal["pubchem", "usda", "rag", "heuristic", "inferred"]

@dataclass
class MechanismStep:
    type: StepType
    description: str
    evidence_source: EvidenceSource
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "evidence_source": self.evidence_source,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

@dataclass
class MechanismChain:
    steps: List[MechanismStep]
    weakest_link_confidence: float = 0.0
    break_reason: Optional[str] = None
    is_valid: bool = False

    def __post_init__(self):
        # Calculate weakest link on init if steps exist
        if self.steps:
            self.weakest_link_confidence = min(s.confidence for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "weakest_link_confidence": self.weakest_link_confidence,
            "break_reason": self.break_reason,
            "is_valid": self.is_valid
        }

class MechanismEngine:
    """
    Engine for assembling, validating, and managing causal mechanism chains.
    Enforces "Tier 2" reasoning standards: No jumps, explicit causality.
    """

    # Permitted transitions for a valid causal chain.
    # From -> [To list]
    VALID_TRANSITIONS = {
        "compound": ["interaction", "physiology"], # Can skip interaction if physiology is direct, but interaction is preferred
        "interaction": ["physiology", "outcome"],
        "physiology": ["outcome", "physiology"],   # Physiology can chain (e.g. gastric emptying -> glucose absorption)
        "outcome": [] # End of chain
    }

    # Source-to-Step Contracts (Evidence Discipline)
    # Enforces which evidence sources are allowed for each step type
    SOURCE_STEP_ALLOWANCE = {
        "compound": ["pubchem", "usda"],  # Only hard chemical/nutrient data
        "interaction": ["rag"],            # Biological interactions from research
        "physiology": ["rag"],             # Physiological effects from research
        "outcome": ["rag", "heuristic"]    # Health outcomes from research or inference
    }

    def validate_chain(self, steps: List[MechanismStep]) -> MechanismChain:
        """
        Validates a raw list of mechanism steps against causal rules.
        Returns a populated MechanismChain.
        """
        if not steps:
            return MechanismChain(steps=[], break_reason="Empty chain", is_valid=False)

        # 1. Start Check: Must start with a verified entity (Compound or Nutrient)
        if steps[0].type != "compound":
            # We might allow 'physiology' start if context is implied, but strict MoA starts with substance.
            return MechanismChain(
                steps=steps, 
                break_reason="Chain must start with a 'compound' or 'nutrient'", 
                is_valid=False
            )

        # 2. Source Contract Validation (NEW - Phase 2)
        for step in steps:
            allowed_sources = self.SOURCE_STEP_ALLOWANCE.get(step.type, [])
            if step.evidence_source not in allowed_sources:
                logger.warning(
                    f"[EVIDENCE_TYPE_VIOLATION] Step type '{step.type}' cannot use source '{step.evidence_source}'. "
                    f"Allowed: {allowed_sources}"
                )
                return MechanismChain(
                    steps=steps,
                    break_reason=f"Evidence type violation: {step.type} step cannot use {step.evidence_source} source",
                    is_valid=False
                )

        # 3. Transition Check
        for i in range(len(steps) - 1):
            current_step = steps[i]
            next_step = steps[i+1]
            
            allowed_next = self.VALID_TRANSITIONS.get(current_step.type, [])
            
            if next_step.type not in allowed_next:
                # Specific Error for Compound -> Outcome jump
                if current_step.type == "compound" and next_step.type == "outcome":
                    return MechanismChain(
                        steps=steps,
                        break_reason="Invalid Jump: Cannot go directly from Compound to Health Outcome. Missing biological interaction or physiology.",
                        is_valid=False
                    )
                
                return MechanismChain(
                    steps=steps,
                    break_reason=f"Invalid Transition: {current_step.type} -> {next_step.type}",
                    is_valid=False
                )

        # 3. End Check: Must end in Outcome (or Physiology if intermediate)
        # Actually, a valuable insight implies an Outcome. 
        # But we might allow concluding on Physiology if the user asked "What happens inside?"
        # For Tier 2 "Health Claims", must end in Outcome.
        if steps[-1].type not in ["outcome", "physiology"]:
             return MechanismChain(
                steps=steps,
                break_reason="Chain must conclude with a physiological effect or health outcome",
                is_valid=False
            )

        # 4. Source Discipline Check (Optional per step, but enforced globally via confidence)
        # "No health outcomes without a biological interaction" - handled by transitions logic roughly.
        
        # Valid!
        return MechanismChain(
            steps=steps,
            is_valid=True,
            break_reason=None
        )

    def assemble_chain(self, 
                       compound_data: Dict[str, Any], 
                       rag_mechanisms: List[str], 
                       outcome_claim: str) -> MechanismChain:
        """
        Attempt to build a chain from disparate components.
        Placeholder for Phase 2 integration logic.
        """
        # This will be implemented when integrating with RAG and Enforcer.
        # For now, it returns an empty invalid chain.
        return MechanismChain(steps=[], break_reason="Not implemented", is_valid=False)
