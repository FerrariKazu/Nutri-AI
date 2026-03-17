import os
import requests
import json
import logging
import time
from typing import List, Dict, Optional, Generator
from .base import LLMClient

logger = logging.getLogger(__name__)

class LocalLlamaClient(LLMClient):
    """
    Lightweight client for local llama.cpp server (OpenAI compatible).
    Permanently replaces Together AI for Nutri Phase 4.
    """

    def __init__(self, model_name: str = "qwen3-4b"):
        self.base_url = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8081")
        self.model_name = model_name
        # Remove trailing slash if present
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        
        logger.info(f"🚀 [LocalLlama] Client initialized at {self.base_url} (model={model_name})")

    def health_check(self) -> Dict:
        """Check if local llama-server is responding."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5.0)
            return {
                "status": "online" if resp.status_code == 200 else "error",
                "provider": "local_llama",
                "model": self.model_name,
                "api_status": resp.status_code
            }
        except Exception as e:
            return {
                "status": "offline",
                "provider": "local_llama",
                "error": str(e)
            }

    def stream_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2048,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        """Stream tokens from local server."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "temperature": temperature,
            "stream": True
        }

        try:
            with requests.post(f"{self.base_url}/v1/chat/completions", json=payload, stream=True, timeout=60) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"❌ [LocalLlama] Stream failed: {e}")
            yield f"[Local LLM Error: {e}]"

    def generate_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 4096,
        temperature: float = 0.2,
        json_mode: bool = False,
        stream_callback: Optional[callable] = None
    ) -> str:
        """Generate full text from local server."""
        if json_mode:
            messages[-1]["content"] += "\n\nReturn the response in valid JSON format only."

        if stream_callback:
            full_content = ""
            for token in self.stream_text(messages, max_new_tokens, temperature):
                full_content += token
                stream_callback(token)
            return self._extract_json(full_content) if json_mode else full_content

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            return self._extract_json(content) if json_mode else content
        except Exception as e:
            logger.error(f"❌ [LocalLlama] Generation failed: {e}")
            return f"Error: Local LLM failed ({e})"

    def _extract_json(self, text: str) -> str:
        """Robust JSON extraction for local model output."""
        text = text.strip()
        # Clean <think> tags if Qwen/DeepSeek reasoning is on
        if "<think>" in text:
            text = text.split("</think>")[-1].strip()
            
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        import re
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
            
        start_brace = text.find('{')
        end_brace = text.rfind('}')
        if start_brace != -1 and end_brace > start_brace:
            return text[start_brace:end_brace+1].strip()
            
        return text
