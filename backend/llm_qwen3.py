"""
Qwen3 LLM Engine (Ollama Version)
Wrapper for Qwen3 model via local Ollama instance
"""

import logging
import os
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
        self.client = ollama.Client(host=host)
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
        
        Yields:
            String chunks of generated text
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
        temperature: float = 0.3
    ) -> str:
        """
        Generate text using Ollama chat API with strict validation.
        """
        if not messages or not isinstance(messages, list):
            raise ValueError("No messages provided to Ollama")

        roles = []
        lengths = []
        for m in messages:
            role = str(m.get("role"))
            content = str(m.get("content", ""))
            roles.append(role)
            lengths.append(len(content))

        logger.info(
            f"Ollama preflight - model={self.model_name} "
            f"count={len(messages)} roles={roles} lens={lengths}"
        )

        valid_messages: List[Dict] = []
        has_user = False

        for m in messages:
            if not isinstance(m, Dict):
                continue
            role = m.get("role")
            content = str(m.get("content", "")).strip()
            if role not in ["user", "system", "assistant"]:
                continue
            if not content:
                continue
            valid_messages.append({"role": role, "content": content})
            if role == "user":
                has_user = True

        if not valid_messages:
            logger.error("All messages empty or invalid before Ollama call")
            raise ValueError("All messages empty or invalid before Ollama call")

        if not has_user:
            logger.error("No user message present before Ollama call")
            raise ValueError("No user message present before Ollama call")

        v_roles = [m["role"] for m in valid_messages]
        v_lengths = [len(m["content"]) for m in valid_messages]
        logger.info(
            f"Ollama payload - model={self.model_name} "
            f"count={len(valid_messages)} roles={v_roles} lens={v_lengths}"
        )
        logger.info(f"Final message payload: {valid_messages}")

        response = self.client.chat(
            model=self.model_name,
            messages=valid_messages,
            options={
                "num_predict": max_new_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            },
        )

        if response and response.get("usage"):
            logger.info(f"Ollama usage: {response['usage']}")

        if not response:
            logger.error("❌ Ollama returned empty response object")
            raise RuntimeError("Ollama returned empty response object")

        content = response.get("message", {}).get("content", "")

        if not content or not content.strip():
            logger.error("⚠️ Ollama returned empty content")
            raise RuntimeError("Ollama returned empty content from chat API")

        logger.info(f"✅ Generated {len(content)} characters")
        return content

    def health_check(self) -> Dict:
        """Return system health info"""
        try:
            models = self.client.list()
            return {
                "status": "online",
                "provider": "ollama",
                "model": self.model_name,
                "available_models": [m['name'] for m in models['models']]
            }
        except Exception as e:
            return {
                "status": "offline",
                "error": str(e)
            }
