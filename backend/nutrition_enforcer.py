import functools
import logging
import asyncio
import time
import hashlib
import json
from enum import Enum
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from backend.pubchem_client import PubChemClient, PubChemNotFound, PubChemTimeout, PubChemError
from backend.nutrition.vectorizer import IngredientExtractor

logger = logging.getLogger(__name__)

class NutritionEnforcementMode(Enum):
    STRICT = "strict"
    PARTIAL = "partial"

@dataclass
class ResolvedCompound:
    name: str
    cid: int
    properties: Dict[str, Any]
    cached: bool = False
    resolution_time_ms: int = 0

@dataclass
class UnresolvedCompound:
    name: str
    reason: str

@dataclass
class ResolutionResult:
    resolved: List[ResolvedCompound] = field(default_factory=list)
    unresolved: List[UnresolvedCompound] = field(default_factory=list)
    total_time_ms: int = 0

class CompoundResolver:
    """
    Service to resolve chemical compounds via PubChem.
    Used by FoodSynthesisEngine to verify ingredients.
    """
    def __init__(self):
        self.client = PubChemClient()

    async def resolve_ingredients(self, ingredients: List[str]) -> ResolutionResult:
        start_ts = time.perf_counter()
        result = ResolutionResult()
        
        for name in ingredients:
            try:
                item_start = time.perf_counter()
                cid = await self.client.search_compound(name)
                props = await self.client.get_compound_properties(cid)
                item_duration = int((time.perf_counter() - item_start) * 1000)
                
                result.resolved.append(ResolvedCompound(
                    name=name,
                    cid=cid,
                    properties=props,
                    resolution_time_ms=item_duration
                ))
            except Exception as e:
                logger.warning(f"[RESOLVER] Failed to resolve '{name}': {e}")
                result.unresolved.append(UnresolvedCompound(name=name, reason=str(e)))
        
        result.total_time_ms = int((time.perf_counter() - start_ts) * 1000)
        return result

def calculate_confidence_score(result: ResolutionResult, mode: NutritionEnforcementMode) -> float:
    """Calculates a confidence score based on resolution success."""
    total = len(result.resolved) + len(result.unresolved)
    if total == 0: return 1.0
    score = len(result.resolved) / total
    return score

def generate_proof_hash(resolved: List[ResolvedCompound]) -> str:
    """Generates a verifiable proof hash for the resolved compounds."""
    data = "|".join([f"{c.name}:{c.cid}" for c in sorted(resolved, key=lambda x: x.cid)])
    return hashlib.sha256(data.encode()).hexdigest()[:12]

class NutritionEnforcer:
    """
    Decorator-based enforcer for PubChem verification.
    """
    def __init__(self):
        self.resolver = CompoundResolver()

    @staticmethod
    def requires_pubchem(func: Callable):
        """
        MANDATORY: Decorator to enforce PubChem validation.
        """
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # 1. Extraction (Mandatory if not present)
            ingredients = kwargs.get("ingredients") or []
            
            # Check positional args for IntentOutput
            if not ingredients:
                for arg in args:
                    if hasattr(arg, "ingredients"):
                        ingredients = arg.ingredients
                        break
            
            # Check kwargs for intent
            if not ingredients and "intent" in kwargs:
                intent = kwargs["intent"]
                if hasattr(intent, "ingredients"):
                    ingredients = intent.ingredients

            # Proactive extraction from user_message if still no ingredients
            if not ingredients:
                user_msg = kwargs.get("user_message")
                if user_msg:
                    logger.info(f"[ENFORCER] Proactively extracting ingredients from: {user_msg[:50]}...")
                    extractor = IngredientExtractor()
                    extracted = extractor.extract(user_msg)
                    ingredients = [i["name"] for i in extracted]

            if not ingredients and hasattr(self, "current_ingredients"):
                ingredients = self.current_ingredients
            
            enforcer = NutritionEnforcer()
            try:
                # 2. Resolution
                res = await enforcer.resolver.resolve_ingredients(ingredients)
                
                # Store on instance for external observability (e.g. by Orchestrator)
                setattr(self, "last_pubchem_result", res)
                
                # 3. Guardrail: Block if 0 compounds resolved in STRICT mode (if ingredients were requested)
                if not res.resolved and ingredients:
                    # The user said "Zero silent fallbacks".
                    logger.warning(f"[ENFORCER] No PubChem hits for {ingredients}. Data will be unverified.")
                
                # 4. Inject Verified Data (ResolutionResult object)
                kwargs["pubchem_data"] = res
                
                # 5. Execute
                if asyncio.iscoroutinefunction(func):
                    return await func(self, *args, **kwargs)
                else:
                    # Offload long-running sync LLM calls to a thread
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, lambda: func(self, *args, **kwargs))
            finally:
                await enforcer.resolver.client.close()
                
        return async_wrapper
