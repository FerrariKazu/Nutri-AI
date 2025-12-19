"""
LLM Engine for Qwen2.5-7B-Instruct
Handles model loading, generation, and self-correction
"""

import torch
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from threading import Thread
from typing import Dict, List, Optional
import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class LLMEngine:
    """Qwen2.5-7B-Instruct wrapper with GPU support"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.model_name = config.MODEL_NAME
        self.load_model()
    
    def load_model(self):
        """Load model with GPU auto-detection"""
        logger.info(f"Loading model: {self.model_name}")
        
        # Check GPU availability
        if torch.cuda.is_available() and config.USE_GPU:
            self.device = "cuda"
            torch_dtype = torch.float16
            logger.info(f"✅ GPU detected: {torch.cuda.get_device_name(0)}")
            logger.info(f"✅ CUDA version: {torch.version.cuda}")
        else:
            self.device = "cpu"
            torch_dtype = torch.float32
            logger.warning("⚠️ GPU not available, using CPU (slower)")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            logger.info(f"✅ Model loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Model loading failed: {e}")
            raise
    
    def build_prompt(
        self,
        user_message: str,
        rag_context: List[Dict],
        memory: List[Dict],
        constraints: Dict
    ) -> str:
        """Build complete prompt with system, RAG, memory, and constraints"""
        
        prompt_parts = [config.SYSTEM_PROMPT]
        
        # Add RAG context
        if rag_context:
            prompt_parts.append("\n=== RELEVANT RECIPES ===")
            for i, recipe in enumerate(rag_context[:config.TOP_K_RAG], 1):
                prompt_parts.append(f"\n[Recipe #{i}]")
                prompt_parts.append(f"Title: {recipe.get('title', 'Unknown')}")
                prompt_parts.append(f"Ingredients: {', '.join(recipe.get('ingredients', [])[:10])}")
                
                # Add nutrition if available
                nutrition = recipe.get('nutrition', {})
                if nutrition:
                    prompt_parts.append(
                        f"Nutrition: Calories {nutrition.get('calories', 'N/A')}, "
                        f"Protein {nutrition.get('protein', 'N/A')}g, "
                        f"Fat {nutrition.get('fat', 'N/A')}g, "
                        f"Carbs {nutrition.get('carbs', 'N/A')}g"
                    )
                
                # Add truncated instructions
                instructions = recipe.get('directions', '')
                if instructions:
                    prompt_parts.append(f"Instructions (truncated): {instructions[:250]}...")
            
            prompt_parts.append("=== END RECIPES ===\n")
        
        # Add conversation memory
        if memory:
            prompt_parts.append("\n=== RECENT CONVERSATION ===")
            for msg in memory[-10:]:  # Last 10 messages
                role = msg.get('role', 'user').upper()
                text = msg.get('text', '')
                prompt_parts.append(f"{role}: {text}")
            prompt_parts.append("=== END CONVERSATION ===\n")
        
        # Add user context
        prompt_parts.append("\n=== USER CONTEXT ===")
        prompt_parts.append(f"ingredients_on_hand: {constraints.get('ingredients', 'none')}")
        prompt_parts.append(f"dislikes: {constraints.get('dislikes', 'none')}")
        prompt_parts.append(f"dietary_constraints: {constraints.get('dietary_constraints', 'none')}")
        prompt_parts.append(f"goal: {constraints.get('goal', 'meal')}")
        prompt_parts.append(f"innovation_level: {constraints.get('innovation_level', 1)}")
        prompt_parts.append("=== END CONTEXT ===\n")
        
        # Add task
        prompt_parts.append("\nTASK:")
        prompt_parts.append(f"User request: {user_message}")
        prompt_parts.append("\nProvide a detailed, chemistry-focused response. If creating a recipe, use mobile-friendly formatting.")
        
        return "\n".join(prompt_parts)
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Dict:
        """Generate response from model"""
        
        max_tokens = max_tokens or config.MAX_NEW_TOKENS
        temperature = temperature or config.TEMPERATURE
        
        try:
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=config.TOP_P,
                    top_k=config.TOP_K,
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove prompt from response
            if response.startswith(prompt):
                response = response[len(prompt):].strip()
            
            return {
                "answer": response,
                "raw_generation": response,
                "regenerated": False
            }
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return {
                "answer": f"Error generating response: {str(e)}",
                "raw_generation": "",
                "regenerated": False
            }
    
    def self_correct(
        self,
        response: str,
        constraints: Dict
    ) -> tuple[str, bool]:
        """Check for constraint violations and regenerate if needed"""
        
        dislikes = constraints.get('dislikes', '').lower().split(',')
        dislikes = [d.strip() for d in dislikes if d.strip()]
        
        if not dislikes:
            return response, False
        
        # Check for violations
        response_lower = response.lower()
        violations = [d for d in dislikes if d in response_lower]
        
        if violations:
            logger.warning(f"⚠️ Constraint violation detected: {violations}")
            return response, True  # Needs regeneration
        
        return response, False
    
    def query(
        self,
        session_id: str,
        user_message: str,
        rag_context: List[Dict],
        constraints: Dict,
        memory: List[Dict]
    ) -> Dict:
        """Main query method with self-correction"""
        
        # Build prompt
        prompt = self.build_prompt(user_message, rag_context, memory, constraints)
        
        # First generation
        result = self.generate(prompt)
        
        # Self-correction check
        answer, needs_regen = self.self_correct(result['answer'], constraints)
        
        if needs_regen:
            # Regenerate with stricter prompt
            dislikes = constraints.get('dislikes', '')
            strict_prompt = f"{prompt}\n\nIMPORTANT: Do NOT use these ingredients: {dislikes}"
            
            result = self.generate(strict_prompt, temperature=0.0)
            result['regenerated'] = True
            logger.info("✅ Regenerated response with stricter constraints")
        
        # Add sources
        result['sources'] = rag_context
        
        return result
    
    def health_check(self) -> Dict:
        """Return system health info"""
        return {
            "model": self.model_name,
            "device": self.device,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A"
        }


# Global instance
llm_engine = None

def get_llm_engine() -> LLMEngine:
    """Get or create LLM engine instance"""
    global llm_engine
    if llm_engine is None:
        llm_engine = LLMEngine()
    return llm_engine
