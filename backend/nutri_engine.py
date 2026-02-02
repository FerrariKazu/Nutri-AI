"""
NutriEngine - Unified Response Generator

Same persona, different modes. This replaces:
- FoodConversationAgent
- FinalPresentationAgent.converse
- FinalPresentationAgent.present_recipe

All paths share the same NUTRI_CORE_PERSONA and conversation memory.
"""

import logging
import re
from typing import Dict, Any, Optional, Callable, List

from backend.response_modes import ResponseMode
from backend.persona import NUTRI_CORE_PERSONA
from backend.mode_constraints import (
    CONVERSATION_CONSTRAINTS,
    DIAGNOSTIC_CONSTRAINTS,
    PROCEDURAL_CONSTRAINTS,
    NUTRITION_ANALYSIS_CONSTRAINTS,
    NUTRITION_CONFIDENCE_POLICY
)
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)


class NutriEngine:
    """
    Unified response generator with strict nutrition governance.
    """

    def __init__(self, llm: LLMQwen3, memory_store):
        self.llm = llm
        self.memory = memory_store

    def generate(
        self,
        session_id: str,
        user_message: str,
        mode: ResponseMode,
        synthesis_data: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        logger.info(f"🎯 NutriEngine generating in {mode.value} mode")
        
        # 1. Build system prompt
        system_prompt = self._build_prompt(mode, synthesis_data)

        # 2. Get conversation history
        history = self.memory.get_messages(session_id)

        # 3. Construct messages
        micro_planning_guidance = (
            "\n\nCONVERSATIONAL MICRO-PLANNING (Hidden):\n"
            "Analyze the user's latest message:\n"
            "- Emotion: Is the user confused, frustrated, curious, or ready to act?\n"
            "- Intent: What is the emotional or practical goal (reassurance, explanation, confirmation)?\n"
            "- Target Length: Should the response be concise (fast confirmation) or detailed (deeper explanation)?\n"
            "Adjust your tone, verbosity, and pacing accordingly. DO NOT mention this analysis in your response."
        )

        messages = [
            {"role": "system", "content": system_prompt + micro_planning_guidance},
            *history,
            {"role": "user", "content": user_message}
        ]

        # 4. Generate with governance pass
        try:
            # For streaming, we apply governance to the final block or chunks if possible.
            # However, post-generation validation works best on the full text.
            response = self.llm.generate_text(messages, stream_callback=stream_callback)
            
            # 5. Governance Safety Net (Hard Strip)
            # 5. Governance Safety Net (Hard Strip)
            if mode != ResponseMode.NUTRITION_ANALYSIS:
                governed_response = self._apply_nutrition_governance(response, mode)
                if governed_response != response:
                    logger.warning("🛡️ Nutrition Governance triggered: Stripped numeric leakage.")
                    response = governed_response
                    # If we already streamed, we can't easily undo, but we store the governed version.

        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise e

        # 6. Store in shared memory
        self.memory.add_message(session_id, "user", user_message)
        self.memory.add_message(session_id, "assistant", response)

        # 7. Update session mode
        self.memory.set_response_mode(session_id, mode)

        return response

    def _apply_nutrition_governance(self, text: str, mode: ResponseMode) -> str:
        """
        Regex-based safety net to strip numeric nutrition leakage.
        Mode-aware: Allows culinary context (grams, etc.) in PROCEDURAL mode.
        """
        # 1. Strict Patterns: Always block these (nutritional units/labels)
        strict_patterns = [
            r"~?\b\d+\s*(?:kcal|calories)\b",                # e.g. "500 kcal"
            r"\b(?:Calories|Protein|Fat|Carbs|Sugar):\s*~?\d+", # e.g. "Calories: 500"
            r"\b(?:provides|contains)\s*~?\d+\s*(?:g|mg)\b",    # e.g. "provides 20g"
            r"~?\b\d+\s*Scoville\b",                            # e.g. "50000 Scoville"
            r"\bScoville\b(?:\s+\w+){0,3}\s+~?\d+\b"            # e.g. "Scoville ... 50000"
        ]
        
        # 2. Contextual Patterns: Units like 'g', 'mg', '%' which might be culinary OR nutritional
        # We only catch them if they are explicitly linked to nutrient names (Protein, Carb, etc.)
        # OR if we are NOT in PROCEDURAL mode (where '50g' is likely an ingredient).
        
        # Regex to find 'number + unit' (e.g., 20g, 50 mg)
        # We look around this match to decide if it's safe.
        contextual_unit_pattern = r"(~?\b\d+(?:-\d+)?\s*(?:g|mg|%)\b)" 

        governed_text = text
        
        # Apply Strict Patterns first
        for pattern in strict_patterns:
            governed_text = re.sub(pattern, "[qualitatively significant amount]", governed_text, flags=re.IGNORECASE)
            
        # Apply Contextual Patterns logic
        # If in PROCEDURAL and the line looks like an ingredient/step, we skip checking simple 'g' units
        # UNLESS they are preceded by "Protein", "Fat", etc.
        
        def contextual_replacement(match):
            snippet = match.group(0)
            start, end = match.span()
            
            # Look at surrounding text context (e.g. prev 20 chars, next 20 chars)
            pre_context = governed_text[max(0, start-25):start].lower()
            post_context = governed_text[end:min(len(governed_text), end+25)].lower()
            full_context = pre_context + post_context
            
            # Keywords that strongly imply NUTRITION context, not ingredient context
            # "sugar" and "fat" can be ingredients ("add sugar", "chicken fat").
            # So we only block them if they look like "Total Fat", "Added Sugars", or if we aren't in procedural mode.
            
            strict_nutrient_keywords = ["protein", "carb", "fiber", "sodium", "cholesterol", "vitamin"]
            ambiguous_keywords = ["sugar", "fat", "saturates"]
            
            # If explicitly labeled as a STRICT nutrient, BLOCK IT
            if any(k in full_context for k in strict_nutrient_keywords):
                return "[qualitatively significant amount]"
                
            # If mostly culinary (INGREDIENT CONTEXT)
            # In PROCEDURAL mode, '500g flour' is fine.
            if mode == ResponseMode.PROCEDURAL:
                 # Check ambiguous keywords only if they look like "Total Sugar" or "Saturated Fat"
                 # Simple "sugar" or "fat" is allowed in procedural (e.g. "Add 50g sugar")
                if any(k in full_context for k in ambiguous_keywords):
                     # If it says "Total Sugar" or "0g fat" (maybe implies nutrition info?)
                     # But "0g fat" fits the pattern \d+g.
                     # Let's trust that in Procedural mode, "sugar" and "fat" are usually ingredients.
                     pass 
                return snippet # Allow it
            
            # In CONVERSATION/DIAGNOSTIC...
            
            # In CONVERSATION/DIAGNOSTIC, '50g' is suspicious, but '50g of flour' is okay.
            # If followd by 'of [ingredient]', allow.
            if re.search(r"\bof\s+[a-z]+", post_context):
                return snippet
                
            # Default to blocking raw numbers in non-procedural modes to be safe?
            # E.g. "It has 50g." -> Block.
            # "Add 50g." -> Block (should be procedural).
            return "[qualitatively significant amount]"

        governed_text = re.sub(contextual_unit_pattern, contextual_replacement, governed_text, flags=re.IGNORECASE)

        # Final cleanup replacement
        if "[qualitatively significant amount]" in governed_text:
            governed_text = re.sub(r"\[qualitatively significant amount\].*?(\.|$)", 
                                   "a level suited to the dish's profile, providing a rich and balanced energy source. ", 
                                   governed_text)
            
        return governed_text

    def _build_prompt(
        self,
        mode: ResponseMode,
        synthesis_data: Optional[Dict[str, Any]]
    ) -> str:
        constraints = {
            ResponseMode.CONVERSATION: CONVERSATION_CONSTRAINTS,
            ResponseMode.DIAGNOSTIC: DIAGNOSTIC_CONSTRAINTS,
            ResponseMode.PROCEDURAL: PROCEDURAL_CONSTRAINTS,
            ResponseMode.NUTRITION_ANALYSIS: NUTRITION_ANALYSIS_CONSTRAINTS,
        }

        prompt = NUTRI_CORE_PERSONA + "\n\n" + constraints[mode]
        
        if mode == ResponseMode.NUTRITION_ANALYSIS:
            prompt += "\n\n" + NUTRITION_CONFIDENCE_POLICY

        # Inject synthesis data
        if synthesis_data:
            if mode == ResponseMode.PROCEDURAL:
                recipe_context = synthesis_data.get('recipe', '')
                if recipe_context:
                    prompt += f"\n\nSCIENTIFIC CONTEXT FOR RECIPE:\n{recipe_context}"
            elif mode == ResponseMode.DIAGNOSTIC:
                analysis = synthesis_data.get('analysis', synthesis_data.get('recipe', ''))
                if analysis:
                    prompt += f"\n\nANALYSIS CONTEXT:\n{analysis}"

        return prompt
