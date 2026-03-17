"""
Hardened LLM Client for Together AI — Nutri Phase 3

Implements:
- DeepSeek-V3 primary + Llama-3.1-70B fallback
- Exponential backoff (3 retries)
- Strict timeout (30s)
- Context trimming (MAX_INPUT_TOKENS)
- Pydantic response validation (optional)
"""

import os
import json
import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class TogetherLLM:
    """
    Together AI client with resilience patterns.
    """
    
    PRIMARY_MODEL = "deepseek-ai/DeepSeek-V3"
    FALLBACK_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    
    # Nutri Phase 3 Limits
    MAX_INPUT_TOKENS = 16000
    MAX_OUTPUT_TOKENS = 2000
    API_TIMEOUT = 30.0  # seconds
    MAX_RETRIES = 3

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            logger.warning("TOGETHER_API_KEY not found in environment.")
        
        self.base_url = "https://api.together.xyz/v1/chat/completions"
        
        # Configure requests session with retry strategy for network-level failures
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def _estimate_tokens(self, text: str) -> int:
        """Simple heuristic: 4 chars per token."""
        return len(text) // 4

    def _trim_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Trim messages to stay within MAX_INPUT_TOKENS."""
        total_tokens = sum(self._estimate_tokens(m["content"]) for m in messages)
        if total_tokens <= self.MAX_INPUT_TOKENS:
            return messages
            
        logger.warning(f"[LLM_HARDENING] Context exceeds limit ({total_tokens} tokens). Trimming.")
        # Keep system message, trim older entries if multiple (though systems usually only have 2-3)
        # For Nutri RAG, the first message is usually the system prompt.
        if len(messages) > 1:
            # Simple trim: keep first (system) and last (user)
            return [messages[0], messages[-1]]
        return messages

    def generate(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Synchronous generation with fallback.
        """
        model = model or self.PRIMARY_MODEL
        trimmed_messages = self._trim_messages(messages)
        
        payload = {
            "model": model,
            "messages": trimmed_messages,
            "max_tokens": self.MAX_OUTPUT_TOKENS,
            "temperature": temperature,
            "stream": stream
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            t0 = time.perf_counter()
            response = self.session.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            
            latency = (time.perf_counter() - t0) * 1000
            logger.info(f"[LLM_METRICS] model={model} latency={latency:.1f}ms")
            
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"[LLM_ERROR] Primary model ({model}) failed: {e}")
            
            # Fallback Logic
            if model == self.PRIMARY_MODEL:
                logger.info(f"[LLM_FALLBACK] Switched to {self.FALLBACK_MODEL}")
                return self.generate(messages, model=self.FALLBACK_MODEL, temperature=temperature)
            
            # If even fallback fails, raise
            raise RuntimeError(f"ALL LLM models failed for query. Last error: {e}")

    async def generate_async(self, messages: List[Dict[str, str]]) -> str:
        """Async wrapper."""
        return await asyncio.to_thread(self.generate, messages)
