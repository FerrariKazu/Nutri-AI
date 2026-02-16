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
import asyncio

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
from backend.nutrition_enforcer import NutritionEnforcer

logger = logging.getLogger(__name__)


class NutriEngine:
    """
    Unified response generator with strict nutrition governance.
    """

    def __init__(self, llm: LLMQwen3, memory_store):
        self.llm = llm
        self.memory = memory_store

    @NutritionEnforcer.requires_pubchem
    def generate(
        self,
        session_id: str,
        user_message: str,
        mode: ResponseMode,
        synthesis_data: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        trace: Optional[Any] = None,
        **kwargs
    ) -> str:
        logger.info(f"🎯 NutriEngine generating in {mode.value} mode")
        
        # 1. Build system prompt
        pubchem_data = kwargs.get("pubchem_data")
        system_prompt = self._build_prompt(mode, synthesis_data, pubchem_data)

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

        # [MANDATE] Primary claim generation from narrative context
        if trace and trace.trace_required:
            logger.info("[ENGINE] Executing primary claim extraction from narrative")
            claims = self.claim_parser.extract_claims_from_thought_stream(response)
            trace.set_claims(claims)
            
            # [INTEGRITY CHECKER]
            self._verify_narrative_integrity(response, trace)

        trace_json = trace.to_json() if trace and hasattr(trace, "to_dict") else None
        self.memory.add_message(session_id, "assistant", response, execution_trace=trace_json)

        # 7. Update session mode
        self.memory.set_response_mode(session_id, mode)

    async def extract_claims_fallback(self, text: str) -> List[Dict[str, Any]]:
        """
        Multi-tier extraction fallback to ensure mandatory intelligence.
        """
        if not text or len(text) < 20:
            return []

        logger.info("[ENGINE] Starting multi-tier claim extraction fallback")
        
        # --- Tier 1: Fast Regex Recovery ---
        # Look for simple "Subject contains X" or "Subject helps Y"
        tier1_claims = []
        patterns = [
            r"(\b[A-Za-z]+(?:\s+[A-Za-z]+)?)\b\s+is\s+rich\s+in\s+(\b[A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
            r"(\b[A-Za-z]+(?:\s+[A-Za-z]+)?)\b\s+(?:helps|supports|aids|promotes)\s+(\b[A-Za-z]+(?:\s+[A-Za-z]+)?)\b"
        ]
        for p in patterns:
            matches = re.finditer(p, text, re.IGNORECASE)
            for m in matches:
                subject, obj = m.groups()
                tier1_claims.append({
                    "claim_id": f"EXT-T1-{hash(m.group(0)) % 10000}",
                    "text": m.group(0),
                    "subject": subject,
                    "mechanism": f"Direct link between {subject} and {obj}",
                    "domain": "biological",
                    "verified": False,
                    "source": "model_output",
                    "origin": "extracted",
                    "confidence": "medium",
                    "verification_level": "heuristic"
                })
        
        if tier1_claims:
            logger.info(f"[ENGINE] Tier 1 found {len(tier1_claims)} claims.")
            return tier1_claims

        # --- Tier 2: LLM Extraction ---
        # Since we use LLMQwen3, we can't easily switch "tiers" of models,
        # so we'll use a specialized prompt for extraction.
        try:
            from backend.claim_parser import ClaimParser
            
            def run_extraction():
                parser = ClaimParser(llm_engine=self.llm)
                return parser.parse(text)
            
            # 🏎️ Run in executor to prevent blocking heartbeats
            loop = asyncio.get_event_loop()
            raw_claims = await asyncio.wait_for(
                loop.run_in_executor(None, run_extraction),
                timeout=25.0 # Max wait for extraction
            )
            
            extracted = []
            for c in raw_claims:
                extracted.append({
                    "claim_id": c.claim_id,
                    "text": c.text,
                    "subject": c.subject or "unknown_entity",
                    "mechanism": c.predicate or "None specified",
                    "domain": "biological",
                    "verified": False,
                    "source": "model_output",
                    "origin": "extracted",
                    "confidence": "medium",
                    "verification_level": "heuristic"
                })
            
            if extracted:
                logger.info(f"[ENGINE] Tier 2 LLM extraction succeeded with {len(extracted)} claims.")
                return extracted
        except asyncio.TimeoutError:
            logger.warning("[ENGINE] LLM extraction pass TIMED OUT. Dropping to heuristic fallback.")
        except Exception as e:
            logger.error(f"[ENGINE] LLM extraction failed: {e}")

        return []

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

    def _verify_narrative_integrity(self, text: str, trace: Any):
        """
        [INTEGRITY MANDATE]
        Checks if the assistant text asserts a mechanism that isn't in trace.
        """
        mechanism_keywords = ["because", "due to", "causes", "activates", "inhibits", "mechanism", "receptor", "cid:"]
        if any(k in text.lower() for k in mechanism_keywords):
            if not trace.claims:
                logger.error("🚨 [INTEGRITY VIOLATION] Narrative asserts mechanism but Trace claims are empty!")
                trace.validation_status = "invalid"
            else:
                logger.info("✅ [INTEGRITY] Narrative mechanism matches trace presence.")

    def _build_prompt(
        self,
        mode: ResponseMode,
        synthesis_data: Optional[Dict[str, Any]],
        pubchem_data: Optional[Any] = None
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

        # 🔬 Inject PubChem verified data directly into the system context
        if pubchem_data and hasattr(pubchem_data, "resolved") and pubchem_data.resolved:
            pubchem_block = "\n\n🔬 PUBCHEM VERIFIED INTELLIGENCE (MANDATORY PROOF):\n"
            pubchem_block += "The following compounds have been verified via PubChem API. Use ONLY these facts for health/chemical claims.\n"
            for c in pubchem_data.resolved:
                props = c.properties
                pubchem_block += f"- {c.name} (CID: {c.cid}): {props.get('MolecularFormula', 'N/A')}, MW: {props.get('MolecularWeight', 'N/A')}\n"
            prompt += pubchem_block

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
