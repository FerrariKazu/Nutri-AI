"""
V2 Intent Sandbox — Phase 1 of the Nutri V2 Orchestrator Migration.

This module runs Pass 1 (Intent Detection) implicitly alongside the V1 pipeline.
It logs structured JSON output for accuracy review without blocking the main stream.
"""

import logging
import json
import asyncio
from enum import Enum
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

logger = logging.getLogger(__name__)


# ─── Constants ──────────────────────────────────────────────────────────────────

VALID_INTENTS = {"recipe_analysis", "general_nutrition", "scientific_query", "chit_chat", "medical_violation"}
MAX_INGREDIENTS = 20


# ─── Pydantic Schemas for Pass 1 (Strict Mode) ─────────────────────────────────

class ExtractedIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_name: str = Field(min_length=1, description="Normalized ingredient name")
    raw_text_span: str = Field(min_length=1, description="Exact substring from user prompt")
    quantity: float = Field(ge=0, description="Numeric quantity (0.0 if missing)")
    unit: str = Field(default="", description="Unit of measurement")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence 0.0–1.0")


class IntentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_category: str = Field(description="Intent classification")
    extracted_ingredients: List[ExtractedIngredient] = Field(default_factory=list, max_length=MAX_INGREDIENTS)
    user_constraints: List[str] = Field(default_factory=list)

    @field_validator("intent_category")
    @classmethod
    def validate_intent(cls, v: str) -> str:
        if v not in VALID_INTENTS:
            raise ValueError(f"Invalid intent_category '{v}'. Must be one of: {VALID_INTENTS}")
        return v


# ─── Deterministic Confidence Recalibration ─────────────────────────────────────

def recalibrate_confidence(ingredient: Dict[str, Any]) -> float:
    """
    Override LLM-generated confidence with deterministic heuristics.
    LLMs inflate confidence — this provides a trustworthy baseline.
    """
    quantity = ingredient.get("quantity", 0)
    unit = ingredient.get("unit", "")
    raw_span = ingredient.get("raw_text_span", "")

    # Base: quantity was explicitly provided
    if quantity > 0 and unit:
        score = 0.90
    elif quantity > 0 and not unit:
        score = 0.60  # No unit = ambiguous
    else:
        score = 0.40  # No quantity at all

    # Penalty: vague language in the raw span
    vague_markers = ["some", "a bit", "like", "ish", "few", "couple", "bunch", "little"]
    if any(marker in raw_span.lower() for marker in vague_markers):
        score -= 0.15

    # Penalty: fractional/complex quantities
    if "/" in raw_span:
        score -= 0.05  # Fractions are parseable but add ambiguity

    # Bonus: standard units increase reliability
    standard_units = {"g", "grams", "gram", "kg", "oz", "ml", "cup", "cups", "tbsp", "tsp", "tablespoon", "teaspoon", "liter", "litre"}
    if unit.lower() in standard_units:
        score += 0.05

    return max(0.0, min(1.0, round(score, 2)))


# ─── System Prompt ──────────────────────────────────────────────────────────────

INTENT_SYSTEM_PROMPT = """You are the Nutri Intent Classifier. Analyze the user's request and output STRICTLY valid JSON.
DO NOT output markdown blocks, conversational text, or explanations. Output ONLY the JSON object.

Schema:
{
  "intent_category": "recipe_analysis | general_nutrition | scientific_query | chit_chat | medical_violation",
  "extracted_ingredients": [
    {"canonical_name": "", "raw_text_span": "", "quantity": 0.0, "unit": "", "confidence": 0.0}
  ],
  "user_constraints": []
}

Rules:
- If the user asks for medical diagnosis, treatment, or prescriptions → "medical_violation"
- If the user says hello, asks about the UI, or makes small talk → "chit_chat"
- If the user mentions specific foods → extract them into "extracted_ingredients"
- If an ingredient mentions NO quantity, still extract it with quantity: 0.0 and unit: ""
- For each ingredient, set "confidence" between 0.0 and 1.0 based on how clear the quantity/unit is
- If no ingredients are mentioned, return an empty array for "extracted_ingredients"
- Only use these intent values: recipe_analysis, general_nutrition, scientific_query, chit_chat, medical_violation
- If a message contains BOTH medical and nutrition content, classify as "medical_violation" (safety-first)
"""


# ─── Intent Detector ───────────────────────────────────────────────────────────

class IntentDetector:
    """
    Pass 1: Intent & Requirement Detection (Sandbox Mode).
    Runs implicitly and logs outputs without blocking the main V1 stream.
    """

    def __init__(self, llm_engine):
        self.llm = llm_engine

    async def analyze_intent_sandbox(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Run intent detection asynchronously. Returns validated dict or None on failure.
        """
        try:
            logger.info("🧪 [V2 SANDBOX] Running Pass 1 Intent Detection...")

            messages = [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]

            response_text = await asyncio.wait_for(
                asyncio.to_thread(self.llm.generate_text, messages),
                timeout=5.0
            )

            # Strip markdown fences if present
            clean_text = response_text
            if "```json" in clean_text:
                clean_text = clean_text.split("```json", 1)[1]
            if "```" in clean_text:
                clean_text = clean_text.split("```", 1)[0]
            clean_text = clean_text.strip()

            # Stage 1: Raw JSON parse
            try:
                raw_payload = json.loads(clean_text)
            except json.JSONDecodeError:
                logger.error(f"❌ [V2 SANDBOX] Pass 1 JSON Parse Failed.\nRaw: {response_text[:500]}")
                return None

            # Stage 2: Filter — remove items without a name
            raw_payload["extracted_ingredients"] = [
                ing for ing in raw_payload.get("extracted_ingredients", [])
                if ing.get("canonical_name", "").strip()
            ]

            # Stage 3: Recalibrate ingredient confidence deterministically
            for ing in raw_payload["extracted_ingredients"]:
                ing["confidence"] = recalibrate_confidence(ing)

            # Stage 3: Pydantic strict validation
            try:
                validated = IntentPayload(**raw_payload)
            except Exception as validation_err:
                logger.error(f"❌ [V2 SANDBOX] Pass 1 Schema Validation Failed: {validation_err}")
                return None

            result = validated.model_dump()
            logger.info(f"✅ [V2 SANDBOX] Pass 1 Success: {json.dumps(result)}")
            return result

        except asyncio.TimeoutError:
            logger.error("⏱️ [V2 SANDBOX] Pass 1 TIMEOUT exceeded (5.0s limit).")
            return None
        except Exception as e:
            logger.error(f"⚠️ [V2 SANDBOX] Pass 1 Error: {e}")
            return None
