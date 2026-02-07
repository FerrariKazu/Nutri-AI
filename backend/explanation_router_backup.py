import logging
from enum import Enum
from typing import Optional, Dict, List, Any
from backend.mechanism_engine import MechanismChain, MechanismStep

logger = logging.getLogger(__name__)

class ExplanationVerbosity(Enum):
    QUICK = "quick" # Outcome only
    SCIENTIFIC = "scientific" # Condensed mechanism
    FULL = "full" # Complete chain details

class ExplanationRouter:
    """
    Renders Mechanism-of-Action (MoA) chains into user-friendly text 
    based on requested verbosity level.
    """

    def render(self, 
               text: str, 
               mechanism: Optional[MechanismChain], 
               verbosity: ExplanationVerbosity = ExplanationVerbosity.QUICK) -> str:
        
        base_claim = text
        if not mechanism or not mechanism.is_valid:
            return base_claim # Fallback to original text

        if verbosity == ExplanationVerbosity.QUICK:
            rendered = self._render_quick(base_claim, mechanism)
        
        elif verbosity == ExplanationVerbosity.SCIENTIFIC:
            rendered = self._render_scientific(base_claim, mechanism)
            
        elif verbosity == ExplanationVerbosity.FULL:
            rendered = self._render_full(base_claim, mechanism)
        else:
            rendered = base_claim
        
        # Phase 4: No-new-facts validation
        try:
            self._validate_no_new_facts(base_claim, mechanism, rendered)
        except ValueError as e:
            logger.error(f"[EXPLANATION_SAFETY] {e}")
            # Return base claim if validation fails
            return base_claim
            
        return rendered

    def _extract_entities(self, mechanism: MechanismChain) -> set:
        """Extract all nouns/entities mentioned in the mechanism chain."""
        entities = set()
        for step in mechanism.steps:
            # Simple word extraction (could be improved with NLP)
            words = step.description.lower().split()
            entities.update(words)
        return entities

    def _validate_no_new_facts(self, base_claim: str, mechanism: MechanismChain, rendered: str):
        """
        Assert that rendered explanation only references entities from the mechanism chain.
        Raises ValueError if new facts are introduced.
        """
        allowed_entities = self._extract_entities(mechanism)
        # Also allow words from base claim
        base_words = set(base_claim.lower().split())
        allowed_entities.update(base_words)
        
        rendered_words = set(rendered.lower().split())
        
        # Filter out common words and punctuation
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'this', 'that', 'which', 'who', 'what', 'their', 'its', 'it', 'they',
            'driven', 'contains', 'contributes', 'mechanism:', 'confidence:','[compound]', '[interaction]', '[physiology]', '[outcome]'
        }
        
        # Check for substantive new words (nouns, compounds, outcomes)
        # This is a simplified check - could be enhanced with NLP
        suspicious_new_words = rendered_words - allowed_entities - stop_words
        
        # Only flag if new words look substantive (length > 4, capitalized, or scientific terms)
        new_facts = {
            w for w in suspicious_new_words 
            if len(w) > 4 and (w[0].isupper() or w.endswith('ose') or w.endswith('ase'))
        }
        
        if new_facts:
            raise ValueError(
                f"Explanation introduced new facts not in mechanism chain: {new_facts}"
            )

    def _render_quick(self, base_claim: str, mechanism: MechanismChain) -> str:
        # Just the claim, maybe slightly enhanced if confident explanation exists
        # Actually, "Quick: Outcome only" -> "Lentils help moderate blood sugar."
        # This matches the base_claim mostly.
        return base_claim

    def _render_scientific(self, base_claim: str, mechanism: MechanismChain) -> str:
        # "Their fiber slows glucose absorption, reducing insulin spikes."
        # Compound -> Physiology -> Outcome
        
        # Extract key steps
        compounds = [s.description for s in mechanism.steps if s.type == "compound"]
        physiologies = [s.description for s in mechanism.steps if s.type == "physiology"]
        outcomes = [s.description for s in mechanism.steps if s.type == "outcome"]
        
        citation = ""
        if compounds and physiologies:
            citation = f"Driven by {compounds[0]}, which {physiologies[0].lower()}."
        elif compounds and outcomes:
             citation = f"Contains {compounds[0]} which contributes to {outcomes[0].lower()}."
             
        return f"{base_claim} ({citation})"

    def _render_full(self, base_claim: str, mechanism: MechanismChain) -> str:
        # Full Step-by-Step
        chain_str = " -> ".join([f"[{s.type.upper()}] {s.description}" for s in mechanism.steps])
        confidence_str = f" (Confidence: {mechanism.weakest_link_confidence:.2f})"
        
        return f"{base_claim}\nMechanism: {chain_str}{confidence_str}"
