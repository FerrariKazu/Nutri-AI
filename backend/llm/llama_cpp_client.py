import logging
import json
import httpx
from typing import List, Dict, Optional, Generator
from .base import LLMClient
from llm_runtime.llama_cpp.config import LLAMA_HOST, LLAMA_PORT
from backend.memory_guard import MemoryGuard

logger = logging.getLogger(__name__)

class LlamaCppClient(LLMClient):
    """Client for llama.cpp server (OpenAI compatible API)"""

    def __init__(self):
        self.base_url = f"http://{LLAMA_HOST}:{LLAMA_PORT}/v1"
        self.is_ready = False
        logger.info(f"🔄 [LlamaCpp] Initializing client for {self.base_url}")
        self.wait_for_readiness()

    def wait_for_readiness(self, timeout: int = 120):
        """
        Wait for llama-server to fully load the model before accepting requests.
        
        This prevents 503 errors that occur when the server is still loading.
        Implements exponential backoff retry with clear progress logging.
        
        Args:
            timeout: Maximum seconds to wait for server readiness
        """
        import time
        
        logger.info("=" * 60)
        logger.info("⏳ Waiting for llama-server model to load...")
        logger.info(f"   Note: Large models can take 30-120 seconds to initialize.")
        logger.info(f"   Timeout: {timeout} seconds")
        logger.info("=" * 60)
        
        start_time = time.time()
        attempt = 0
        backoff = 2  # Start with 2 second intervals
        
        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            try:
                resp = httpx.get(f"{self.base_url}/models", timeout=5.0)
                
                if resp.status_code == 200:
                    load_time = int(time.time() - start_time)
                    logger.info("=" * 60)
                    logger.info(f"✅ [LlamaCpp] Model loaded successfully!")
                    logger.info(f"   Load time: {load_time} seconds")
                    logger.info(f"   Server: {self.base_url}")
                    logger.info("=" * 60)
                    self.is_ready = True
                    
                    # Log GPU status if available
                    try:
                        from .cuda_monitor import log_gpu_status
                        log_gpu_status()
                    except Exception as e:
                        logger.debug(f"Could not log GPU status: {e}")
                    
                    return
                    
                elif resp.status_code == 503:
                    # Server is up but model still loading
                    logger.info(f"⏳ [{elapsed}s] Model still loading... (attempt {attempt})")
                    
                else:
                    logger.warning(f"⚠️  [{elapsed}s] Unexpected status {resp.status_code}")
                    
            except httpx.ConnectError:
                logger.info(f"⏳ [{elapsed}s] Waiting for llama-server to start... (attempt {attempt})")
                
            except Exception as e:
                logger.debug(f"Connection attempt {attempt} failed: {e}")
            
            # Exponential backoff (max 10 seconds between attempts)
            time.sleep(min(backoff, 10))
            backoff *= 1.5
        
        # Timeout reached
        logger.error("=" * 60)
        logger.error(f"❌ [LlamaCpp] Model failed to load within {timeout} seconds!")
        logger.error(f"   Check llama.log for errors.")
        logger.error(f"   Common issues:")
        logger.error(f"   - Insufficient VRAM for the selected model")
        logger.error(f"   - llama-server not running")
        logger.error(f"   - Wrong port (expecting {LLAMA_PORT})")
        logger.error("=" * 60)
        raise RuntimeError(f"LlamaCpp server not ready after {timeout}s")

    def health_check(self) -> Dict:
        """Check health status of llama-server"""
        if not self.is_ready:
            return {
                "status": "loading",
                "provider": "llama_cpp",
                "details": "Model is still loading. Please wait."
            }
        
        try:
            resp = httpx.get(f"{self.base_url}/models", timeout=2.0)
            return {
                "status": "online" if resp.status_code == 200 else "error",
                "provider": "llama_cpp",
                "details": resp.json() if resp.status_code == 200 else str(resp.status_code)
            }
        except Exception as e:
            return {"status": "offline", "provider": "llama_cpp", "error": str(e)}

    def stream_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2048,
        temperature: float = 0.3,
        boundary_token: Optional[str] = None
    ) -> Generator[str, None, None]:
        
        # Ensure model is ready before attempting inference
        if not self.is_ready:
            logger.error("❌ [LlamaCpp] Attempted to use client before model is ready!")
            yield "[Error: Model not loaded yet. Please wait for initialization.]"
            return
        
        # Enforce Memory Limits
        safe_tokens = MemoryGuard.get_safe_token_limit(max_new_tokens)
        
        payload = {
            "model": "qwen3", 
            "messages": messages,
            "max_tokens": safe_tokens,
            "temperature": temperature,
            "stream": True,
            "top_p": 0.9,
        }

        try:
            logger.info(f"🔄 [LlamaCpp] Streaming to {self.base_url} (limit={safe_tokens}, boundary={boundary_token})")
            
            with httpx.stream("POST", f"{self.base_url}/chat/completions", json=payload, timeout=600.0) as response:
                if response.status_code != 200:
                     error_msg = response.read().decode('utf-8')
                     logger.error(f"❌ [LlamaCpp] HTTP Error {response.status_code}: {error_msg}")
                     yield f"Error: {response.status_code}"
                     return

                # Buffer for defensive parsing (if boundary needed)
                content_buffer = "" 
                found_boundary = False if boundary_token else True
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')
                        
                    if line.startswith("data: "):
                        json_str = line[6:]
                        if json_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            
                            # INTERNAL REASONING SUPPRESSION
                            # 1. Discard reasoning_content channel entirely
                            raw_content = delta.get("content")
                            if raw_content is None:
                                continue
                                
                            content = str(raw_content)
                            
                            if not found_boundary and boundary_token:
                                # DEFENSIVE BUFFERING
                                # We capture everything in case the boundary is missing/truncated
                                content_buffer += content
                                
                                if boundary_token in content_buffer:
                                    # Boundary found in buffer! Extract everything after it.
                                    parts = content_buffer.split(boundary_token)
                                    after_boundary = parts[-1].lstrip()
                                    if after_boundary:
                                        yield after_boundary
                                    found_boundary = True
                                    logger.info(f"🎯 Boundary {boundary_token} reached. Starting stream.")
                                    content_buffer = "" # Clear buffer to free memory
                                continue # Keep buffering/searching
                            
                            # Once boundary found (or if none required), yield standard content
                            if content:
                                yield content
                        
                        except json.JSONDecodeError:
                            continue

                # DIAGNOSTIC & FALLBACK: Check for boundary miss
                if boundary_token and not found_boundary:
                    logger.warning(f"⚠️ [LlamaCpp] Stream ended without boundary '{boundary_token}'.")
                    
                    if len(content_buffer) > 50:
                        logger.warning(f"   Fallback: Yielding buffered content ({len(content_buffer)} chars).")
                        yield content_buffer
                        yield f"\n\n[Note: Output completed without explicit final marker.]"
                    else:
                        logger.error("   Buffer too small; assuming true failure.")
                        yield f"\n\n[System Error: Model reasoning was truncated. Please try again or rephrase.]"

        except Exception as e:
             logger.error(f"❌ [LlamaCpp] Stream Exception: {e}")
             yield f"[Connection Error: {e}]"

    def generate_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
        stream_callback: Optional[callable] = None,
        boundary_token: Optional[str] = None
    ) -> str:
        
        # Ensure model is ready before attempting inference
        if not self.is_ready:
            error_msg = "Model not loaded yet. Please wait for initialization."
            logger.error(f"❌ [LlamaCpp] {error_msg}")
            raise RuntimeError(error_msg)
        
        # Enforce Memory Limits
        safe_tokens = MemoryGuard.get_safe_token_limit(max_new_tokens)
        
        if json_mode:
            messages[-1]["content"] += "\n\nRETURN JSON ONLY."
            
        try:
            if stream_callback:
                full_content = ""
                for token in self.stream_text(
                    messages=messages, 
                    max_new_tokens=safe_tokens, 
                    temperature=temperature,
                    boundary_token=boundary_token
                ):
                    full_content += token
                    stream_callback(token)
                
                if json_mode:
                    return self._extract_json(full_content)
                return full_content
            
            else:
                payload = {
                    "model": "qwen3",
                    "messages": messages,
                    "max_tokens": safe_tokens,
                    "temperature": temperature,
                    "stream": False
                }
                
                resp = httpx.post(f"{self.base_url}/chat/completions", json=payload, timeout=600.0)
                resp.raise_for_status()
                data = resp.json()
                
                content = data["choices"][0]["message"]["content"]
                logger.info(f"✅ [LlamaCpp] Generated {len(content)} chars")
                
                if json_mode:
                    return self._extract_json(content)
                return content
                
        except Exception as e:
            logger.error(f"❌ [LlamaCpp] Generate Error: {e}")
            raise e

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if "<think>" in text: 
            text = text.split("</think>")[-1].strip()

        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start: return text[start:end].strip()
            
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start: return text[start:end].strip()
            
        start_brace = text.find('{')
        start_bracket = text.find('[')
        
        start = -1
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            end = text.rfind('}') + 1
        elif start_bracket != -1:
            start = start_bracket
            end = text.rfind(']') + 1
            
        if start != -1 and end > start:
            return text[start:end].strip()
            
        return text
