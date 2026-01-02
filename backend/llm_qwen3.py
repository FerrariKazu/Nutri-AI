"""
Qwen3 LLM Engine (Ollama Version)
Wrapper for Qwen3 model via local Ollama instance
"""

import logging
import os
import json
from typing import Dict, List, Optional
import ollama

logger = logging.getLogger(__name__)

class LLMQwen3:
    """Wrapper for Ollama-served Qwen models"""
    
    def __init__(self, model_name: str = "qwen3:8b"):
        """
        Initialize Ollama wrapper with enhanced validation
        
        Args:
            model_name: Name of the model in Ollama
        """
        host = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
        # Increase timeout for complex extraction tasks
        self.client = ollama.Client(host=host, timeout=120.0)
        self.model_name = self._validate_model(model_name)
        self._validate_connection()
    
    def _validate_model(self, model_name: str) -> str:
        """Ensure model exists in Ollama"""
        try:
            models = self.client.list()
            available_models = []
            if 'models' in models:
                available_models = [m.get('name') or m.get('model') for m in models['models']]

            for model in available_models:
                if model_name == model:
                    logger.info(f"✅ Using model: {model}")
                    return model

            raise ValueError(f"Model '{model_name}' not found in Ollama. Available models: {available_models}")

        except Exception as e:
            raise ConnectionError(f"Ollama connection failed: {e}")
    
    def _validate_connection(self):
        """Validate Ollama connection and log status"""
        try:
            models = self.client.list()
            logger.info(f"✅ Connected to Ollama. Available models: {[m.get('name') or m.get('model') for m in models['models']]}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Ollama: {e}")
            raise ConnectionError(f"Ollama connection failed: {e}")

    def stream_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2024,
        temperature: float = 0.3
    ):
        """
        Generate streaming text using Ollama chat API with guaranteed non-empty output.
        """
        if not messages or all(not m.get("content", "").strip() for m in messages):
            raise ValueError("No input provided to Ollama")

        yielded_any = False
        try:
            logger.info(f"🔄 Streaming with model: {self.model_name}")
            
            if not messages or not isinstance(messages, list):
                raise ValueError("No messages provided to Ollama (stream)")

            messages = [
                {"role": m["role"], "content": m["content"].strip()}
                for m in messages
                if m.get("content", "").strip()
            ]

            if not messages:
                raise ValueError("All messages empty in stream_text")


            stream = self.client.chat(
                model=self.model_name,
                messages=messages,
                stream=True,
                options={
                    "num_predict": max_new_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                }
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    if content:
                        yield content
                        yielded_any = True
            
            if not yielded_any:
                logger.error("⚠️ Stream completed but no content yielded")
                yield "I apologize, but I couldn't generate a response. Please try again."
                    
        except Exception as e:
            logger.error(f"❌ Ollama streaming error: {e}")
            if not yielded_any:
                yield f"Error: Unable to generate response. Please try again. ({str(e)[:100]})"
            raise

    def generate_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2024,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """
        Generate text using Ollama chat API with robust validation and JSON extraction.
        """
        if not messages or not isinstance(messages, list):
            raise ValueError("No messages provided to Ollama")

        # If json_mode is requested, append a clear instruction to the last message
        if json_mode:
            # Check if user message exists, otherwise add one
            has_user = any(m.get("role") == "user" for m in messages)
            if not has_user:
                messages.append({"role": "user", "content": "Generate the requested JSON data."})
            
            # Add strict instruction to the last user message
            for m in reversed(messages):
                if m.get("role") == "user":
                    m["content"] += "\n\nCRITICAL: Return ONLY valid JSON. No conversational filler. Start with [ or { and end with ] or }."
                    break

        # Pre-flight logging
        v_roles = [m.get("role") for m in messages]
        v_lengths = [len(str(m.get("content", ""))) for m in messages]
        logger.info(
            f"Ollama Call - model={self.model_name} json={json_mode} "
            f"count={len(messages)} roles={v_roles} lens={v_lengths}"
        )
        
        valid_messages: List[Dict] = []
        has_user = False
        for m in messages:
            role = m.get("role")
            content = str(m.get("content", "")).strip()
            if role in ["user", "system", "assistant"] and content:
                valid_messages.append({"role": role, "content": content})
                if role == "user": has_user = True

        if not has_user:
            raise ValueError("No user message present before Ollama call")

        # Use 0.7 temperature by default to prevent "stuck" models
        # But if json_mode is True, maybe slightly lower is safer, but not 0.1
        current_temp = temperature if not json_mode else 0.4

        for attempt in range(2):
            try:
                response = self.client.chat(
                    model=self.model_name,
                    messages=valid_messages,
                    options={
                        "num_predict": max_new_tokens,
                        "temperature": current_temp,
                        "top_p": 0.9,
                    },
                )

                if not response:
                    logger.error(f"❌ Ollama returned empty response object (attempt {attempt+1})")
                    continue

                content = response.get("message", {}).get("content", "")
                if not content or not content.strip():
                    logger.error(f"⚠️ Ollama returned empty content (attempt {attempt+1})")
                    current_temp += 0.2
                    continue

                if json_mode:
                    logger.info(f"Raw Ollama output (json_mode=True): {content}")
                    content = self._extract_json(content)

                logger.info(f"✅ Generated {len(content)} characters (model: {self.model_name})")
                return content

            except Exception as e:
                logger.error(f"❌ Ollama API error (attempt {attempt+1}): {e}")
                if attempt == 1: raise
        
        raise RuntimeError("Ollama failed to return content after retries")

    def _extract_json(self, text: str) -> str:
        """Robustly extract JSON from text, handling potential markdown blocks."""
        text = text.strip()
        # Look for JSON code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # Look for generic code blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
                
        # Look for first { or [ and last } or ]
        start_brace = text.find('{')
        start_bracket = text.find('[')
        
        start = -1
        if start_brace != -1 and (start_bracket == -1 or (start_bracket != -1 and start_brace < start_bracket)):
            start = start_brace
            end = text.rfind('}') + 1
        elif start_bracket != -1:
            start = start_bracket
            end = text.rfind(']') + 1
            
        if start != -1 and end > start:
            result = text[start:end].strip()
            # Double check if it looks like JSON
            if (result.startswith('{') and result.endswith('}')) or (result.startswith('[') and result.endswith(']')):
                return result
            
        return text

    def health_check(self) -> Dict:
        """Return system health info"""
        try:
            models = self.client.list()
            return {
                "status": "online",
                "provider": "ollama",
                "model": self.model_name,
                "available_models": [m.get('name') or m.get('model') for m in models['models']]
            }
        except Exception as e:
            return {
                "status": "offline",
                "error": str(e)
            }
