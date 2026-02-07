import logging
from enum import Enum
from typing import Optional, Dict, List, Any
from backend.mechanism_engine import MechanismChain, MechanismStep
from backend.belief_state import BeliefState
from backend.decision_comparator import DecisionDelta
from backend.reversal_explainer import ReversalExplanation

logger = logging.getLogger(__name__)

class ExplanationVerbosity(Enum):
    QUICK = "quick" # Outcome only
    SCIENTIFIC = "scientific" # Condensed mechanism
    FULL = "full" # Complete chain details

class LanguagePolicy:
    """
    Graded language policy based on RecommendationDecision.
    
    Gap 4 Fix: Not binary allow/ban, but graded epistemic language.
    """
    
    # Banned phrases unless decision = ALLOW
    BANNED_UNLESS_ALLOW = [
        "you should",
        "you must",
        "this will",
        "guaranteed",
        "proven to",
        "definitely",
        "always",
        "recommended for everyone",
        "safe for all"
    ]
    
    # Tier-specific allowed phrases
    ALLOW_LANGUAGE = [
        "may help", "can support", "might contribute",
        "could benefit", "has been shown to"
    ]
    
    REQUIRE_MORE_CONTEXT_LANGUAGE = [
        "depends on", "varies by", "individual factors",
        "context-dependent", "may or may not"
    ]
    
    WITHHOLD_LANGUAGE = [
        "cannot recommend", "not advisable without",
        "requires consultation", "caution needed"
    ]
    
    @classmethod
    def for_decision(cls, decision_value: str) -> List[str]:
        """Get allowed language phrases for a given decision."""
        if decision_value == "allow":
            return cls.ALLOW_LANGUAGE
        elif decision_value == "require_more_context":
            return cls.REQUIRE_MORE_CONTEXT_LANGUAGE
        elif decision_value == "withhold":
            return cls.WITHHOLD_LANGUAGE
        else:
            return cls.REQUIRE_MORE_CONTEXT_LANGUAGE
    
    @classmethod
    def check_banned_phrases(cls, text: str, decision_value: str) -> List[str]:
        """Check if text contains banned phrases for this decision level."""
        if decision_value == "allow":
            return []  # No restrictions for ALLOW
        
        text_lower = text.lower()
        violations = [
            phrase for phrase in cls.BANNED_UNLESS_ALLOW
            if phrase in text_lower
        ]
        
        if violations:
            logger.warning(f"[LANGUAGE_GATE_VIOLATION] Found banned phrases: {violations}")
        
        return violations

class ExplanationRouter:
    """
    Renders Mechanism-of-Action (MoA) chains into user-friendly text 
    based on requested verbosity level.
    """

    def render(self, 
               text: str, 
               mechanism: Optional[MechanismChain], 
               verbosity: ExplanationVerbosity = ExplanationVerbosity.QUICK,
               recommendation_decision: str = "allow",
               decision_delta: Optional[DecisionDelta] = None,
               confidence_delta: Optional[float] = None,
               belief_state: Optional[BeliefState] = None,
               reversal_explanation: Optional[ReversalExplanation] = None) -> str:
        
        base_claim = text
        
        # Tier 4: Memory Compression (STABLE path)
        if decision_delta and decision_delta.change_type == "STABLE" and verbosity != ExplanationVerbosity.FULL:
            # Avoid repeating full reasoning if stable
            return f"{base_claim} (As mentioned earlier, our assessment remains stable.)"

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
        
        # Tier 4: Reversal Acknowledgment
        if reversal_explanation:
            reversal_text = self._format_reversal_text(reversal_explanation, decision_delta)
            rendered = f"{reversal_text} {rendered}"

        # Phase 4: No-new-facts validation
        try:
            self._validate_no_new_facts(base_claim, mechanism, rendered)
        except ValueError as e:
            logger.error(f"[EXPLANATION_SAFETY] {e}")
            # Return base claim if validation fails
            return base_claim
        
        # Tier 3: Language policy validation
        violations = LanguagePolicy.check_banned_phrases(rendered, recommendation_decision)
        if violations:
            logger.error(f"[LANGUAGE_GATE_VIOLATION] Rendered text contains banned phrases: {violations}")
            # Sanitize or return base claim
            return base_claim
            
        return rendered

    def _format_reversal_text(self, 
                              reversal: ReversalExplanation, 
                              delta: Optional[DecisionDelta]) -> str:
        """
        Format reversal explanation with Tier 4 temporal language.
        """
        if not delta:
            return ""
            
        if delta.change_type == "UPGRADE":
            prefix = "Now that we know more context,"
        elif delta.change_type == "DOWNGRADE":
            prefix = "Given this new factor,"
        else:
            return ""
            
        # Combine template fields
        text = f"{prefix} {reversal.what_changed.lower()}. {reversal.why_changed}"
        
        # Add turn reference if available
        if reversal.turn_reference:
            text = f"{text} (Learned {reversal.turn_reference})"
            
        return f"{text} Therefore, {reversal.impact_on_decision.lower()}."

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
