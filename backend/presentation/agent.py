import logging
import json
from typing import Dict, Any, List, Optional
from backend.llm_qwen3 import LLMQwen3
from backend.sse_utils import safe_json

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

FRIENDLY_RECIPE_PROMPT = """
You are a chef who loves explaining why flavors work, without talking about yourself.
Your goal is to format the provided recipe data into clean, beautiful Markdown.

🧠 TONE RULES:
- Write with warmth, expertise, and sensory detail ("creamy", "bright", "seared").
- Use natural transitions ("This works because...", "The acidity balances...").
- BE HUMAN, BUT INVISIBLE. You are the text, not the speaker.

⛔ STRICTURES (CRITICAL):
- NO greetings ("Hey", "Hello", "I'm Nutri").
- NO introductions ("Here is your recipe", "Sure!").
- NO footers ("Enjoy!", "Let me know if you like it").
- NO emojis in the body (Use 1 relevant food emoji in the Title).
- NO persona identity ("As an AI...", "I think...").

📝 FORMATTING STRUCTURE:
- Start IMMEDIATELY with the Dish Title (using #).
- Follow strictly:

  # 🍕 [Dish Title]

  [1 short paragraph (2-3 sentences max) that subtly acknowledges the user's request and sets the mood. Example: "This pizza leans creamy and smooth, balancing the rich white sauce with sharp garlic notes."]

  ### Ingredients
  - [Item]
  - [Item]

  ### Steps
  1. [Step 1]
  2. [Step 2]

  ### Why This Works
  - **[Concept]:** [Explanation]

- Use bullet points (-) for ingredients.
- Use numbered lists (1. 2. 3.) for steps.
- Leave a BLANK LINE between every section.
"""

CONVERSATIONAL_PROMPT = """
You are Nutri.

Your goal is to have a friendly, human connection with the user.
You are NOT generating a recipe right now.
You are NOT explaining science right now (unless asked).

────────────────────────────────
STRICT BOUNDARIES
────────────────────────────────
❌ DO NOT output a recipe.
❌ DO NOT list ingredients.
❌ DO NOT give instructions.
❌ DO NOT output nutritional data.

────────────────────────────────
TONE
────────────────────────────────
- Warm, curious, and welcoming.
- Use an emoji or two (🙂, 🍎, 👋).
- Keep it brief (2-3 sentences max).
- REQUIRED: End with an engaging "Food Hook" question to spark curiosity.
  (e.g., "Ever tried pairing chocolate with olive oil?", "Do you prefer spicy or sweet breakfasts?")

Example:
"Hey there! 👋 I'm Nutri. I love deconstructing food and inventing new flavor combinations. Have you ever wondered why popcorn smells so good?"
"""


class FinalPresentationAgent:
    """
    Agent responsible for the final human-facing transformation of Nutri's scientific output.
    Now strictly separated into 'Recipe Mode' (Friendly Chef) and 'Conversation Mode'.
    """
    
    def __init__(self, llm: LLMQwen3):
        self.llm = llm
        
    def converse(
        self,
        user_message: str,
        stream_callback: Optional[callable] = None
    ) -> str:
        """
        Handling for pure conversation/greeting/meta-intents.
        Strictly prevents recipe generation.
        """
        messages = [
            {"role": "system", "content": CONVERSATIONAL_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        logger.info("👋 Presentation Agent in CONVERSATIONAL mode")
        
        # 1. Generate fully to check safeguards
        full_response = self.llm.generate_text(messages)
        
        # 2. SAFEGUARD: Check for recipe leakage
        forbidden_terms = ["Ingredients:", "### Ingredients", "Steps:", "### Steps", "Calories:", "Why This Works"]
        if any(term in full_response for term in forbidden_terms):
            logger.warning("🚨 Recipe leakage detected in Conversation Mode! Regenerating with correction.")
            
            # Retry with negative constraint
            messages.append({"role": "assistant", "content": full_response})
            messages.append({"role": "user", "content": "STOP. You just generated a recipe context. I only said hello. Please reset and just say a friendly conversational greeting. Do not mention ingredients."})
            
            full_response = self.llm.generate_text(messages)
            
        # 3. Output (Mock Streaming)
        if stream_callback:
            chunk_size = 5
            for i in range(0, len(full_response), chunk_size):
                stream_callback(full_response[i:i+chunk_size])
                
        return full_response

    def present_recipe(
        self,
        user_request: str,
        internal_result: Dict[str, Any],
        context: Dict[str, Any],
        stream_callback: Optional[callable] = None
    ) -> str:
        """
        Transforms internal scientific data into a clean, professional Markdown recipe.
        Uses 'Friendly Chef' persona but strictly enforces NO PERSONA IDENTITY statements.
        """
        audience = context.get("audience_mode", "standard")
        verbosity = context.get("verbosity", "standard")
        intent = context.get("intent", "meal")
        
        # Prepare the context for the LLM
        system_message = f"{FRIENDLY_RECIPE_PROMPT}\n\n"
        system_message += f"CONTEXT:\n- Audience: {audience}\n- Verbosity: {verbosity}\n- Intent: {intent}"
        
        # Sanitize internal result for prompt inclusion
        safe_result = safe_json(internal_result)
        
        # We pass the internal result as a structured block
        user_input_prompt = f"USER REQUEST: {user_request}\n\nINTERNAL DEEP RESULT:\n{json.dumps(safe_result, indent=2)}\n\n"
        user_input_prompt += "Produce the formatted Markdown recipe now. Start with the Title."

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input_prompt}
        ]
        
        logger.info(f"🍳 Presentation Agent in FRIENDLY RECIPE mode (audience={audience})")
        
        try:
            # 1. Generate FULLY first (Buffering for Safety)
            # We sacrifice TTFT (Time To First Token) to ensure we can strip greetings.
            full_answer = self.llm.generate_text(messages)
            
            # 2. SANITIZATION (The Hard Assertion)
            # Check if the output starts with a greeting or persona tag
            lines = full_answer.split('\n')
            if lines:
                first_line_clean = lines[0].lower().strip()
                # Forbidden triggers
                triggers = ["hey", "hello", "hi ", "i'm nutri", "i am nutri", "sure!", "here is", "certainly"]
                
                # If first line contains a trigger OR doesn't start with Markdown Header #
                # We allow it ONLY if it's clearly a title without greetings.
                # But our prompt strictly asks for # Title first.
                
                if any(t in first_line_clean for t in triggers) or not first_line_clean.startswith("#"):
                    if not first_line_clean.startswith("#") and len(lines) > 1:
                        # Heuristic: If first line isn't a Header, and it looks chatty, strip it.
                        logger.warning(f"🚨 Persona Leakage (Header Check): '{lines[0]}'. Stripping.")
                        lines = lines[1:]
                        full_answer = "\n".join(lines).strip()
                    elif any(t in first_line_clean for t in triggers):
                        logger.warning(f"🚨 Persona Leakage (Trigger Check): '{lines[0]}'. Stripping.")
                        lines = lines[1:]
                        full_answer = "\n".join(lines).strip()
                        
                    # Double check new first line
                    if lines and any(t in lines[0].lower().strip() for t in triggers):
                         # Recursive strip (rare but possible)
                         logger.warning("🚨 Double Leakage detected. Stripping second line too.")
                         lines = lines[1:]
                         full_answer = "\n".join(lines).strip()

            # 3. Stream the sanitized result
            if stream_callback:
                chunk_size = 10 # Slightly faster chunks
                for i in range(0, len(full_answer), chunk_size):
                    stream_callback(full_answer[i:i+chunk_size])
            
            return full_answer

        except Exception as e:
            logger.error(f"❌ Presentation Agent failed: {e}")
            # Fallback
            recipe = internal_result.get("recipe", "")
            return f"# Error Generating Format\n\n{recipe}"
