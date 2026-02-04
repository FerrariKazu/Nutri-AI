import logging
import os
import ollama
from typing import List, Dict, Optional, Generator
from .base import LLMClient

logger = logging.getLogger(__name__)

class OllamaClient(LLMClient):
    """Legacy wrapper for Ollama-served models"""
    
    def __init__(self, model_name: str):
        host = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
        self.client = ollama.Client(host=host, timeout=300.0)
        self.model_name = model_name
        self._validate_connection()

    def _validate_connection(self):
        try:
            self.client.list()
            logger.info(f"✅ [Ollama] Connected to {self.model_name}")
        except Exception as e:
            logger.error(f"❌ [Ollama] Connection failed: {e}")

    def health_check(self) -> Dict:
        try:
            models = self.client.list()
            return {
                "status": "online",
                "provider": "ollama",
                "model": self.model_name,
                "available_models": [m.get('name') or m.get('model') for m in models['models']]
            }
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def stream_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2024,
        temperature: float = 0.3
    ) -> Generator[str, None, None]:
        
        valid_messages = [
            {"role": m["role"], "content": m["content"].strip()}
            for m in messages if m.get("content", "").strip()
        ]

        if not valid_messages:
            yield "Error: No input messages."
            return

        try:
            logger.info(f"🔄 [Ollama] Streaming {len(valid_messages)} msgs")
            stream = self.client.chat(
                model=self.model_name,
                messages=valid_messages,
                stream=True,
                options={
                    "num_predict": 1024,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_ctx": 4096,
                }
            )
            
            for chunk in stream:
                content = chunk.get('message', {}).get('content', '')
                if content:
                    yield content
                    
        except Exception as e:
            logger.error(f"❌ [Ollama] Stream error: {e}")
            yield f"[Error: {e}]"

    def generate_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
        stream_callback: Optional[callable] = None
    ) -> str:
        
        # Pre-process messages (JSON instruction injection if needed)
        if json_mode:
             # Add strictly formatted instruction
             # (Simplified logic from original LLMQwen3)
             messages[-1]["content"] += "\n\nRETURN JSON ONLY."

        valid_messages = [m for m in messages if m.get("content")]
        
        try:
            full_content = ""
            if stream_callback:
                # Reuse stream_text logic? Or direct client call logic?
                # Direct call to support stream_callback matching original implementation
                stream = self.client.chat(
                    model=self.model_name,
                    messages=valid_messages,
                    stream=True,
                    options={
                        "num_predict": max_new_tokens,
                        "temperature": temperature,
                        "num_ctx": 8192
                    }
                )
                for chunk in stream:
                    token = chunk.get('message', {}).get('content', '')
                    if token:
                        full_content += token
                        stream_callback(token)
            else:
                resp = self.client.chat(
                    model=self.model_name,
                    messages=valid_messages,
                    stream=False,
                    options={
                        "num_predict": max_new_tokens,
                        "temperature": temperature,
                        "num_ctx": 4096
                    }
                )
                full_content = resp.get('message', {}).get('content', '')
                
            if json_mode:
                return self._extract_json(full_content)
            return full_content

        except Exception as e:
            logger.error(f"❌ [Ollama] Generate error: {e}")
            raise e

    def _extract_json(self, text: str) -> str:
        # Simplified JSON extractor
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        return text
