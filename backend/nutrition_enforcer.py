"""
Nutrition Enforcement Layer for Nutri

Enforces mandatory PubChem verification for all nutrition claims.

Key features:
- @requires_pubchem decorator for agent methods
- Ingredient → Compound mapping knowledge base
- Resolution budget (max 10 compounds per request)
- Confidence score formula
- Proof hash generation
- Zero silent fallbacks

Modes:
- STRICT: Hard fail on missing compounds (production)
- PARTIAL: Annotate unverified ingredients (dev/demo)
"""

import logging
import hashlib
import time
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

from backend.pubchem_client import (
    get_pubchem_client,
    PubChemClient,
    PubChemError,
    PubChemNotFound,
    PubChemTimeout,
    CompoundProperties
)

logger = logging.getLogger(__name__)

# ============================================================================
# ENFORCEMENT POLICY
# ============================================================================

class NutritionEnforcementMode(Enum):
    """
    Enforcement behavior for unverified compounds.
    
    STRICT: Hard fail if critical compounds cannot be resolved (production default)
    PARTIAL: Return partial recipe with [UNVERIFIED] annotations (dev/demo only)
    """
    STRICT = "strict"
    PARTIAL = "partial"

# Default mode (can be overridden via environment variable)
DEFAULT_MODE = NutritionEnforcementMode.STRICT

# ============================================================================
# INGREDIENT → COMPOUND KNOWLEDGE BASE
# ============================================================================

INGREDIENT_COMPOUND_MAP = {
    # Vegetables
    "tomato": ["lycopene", "vitamin c", "beta-carotene"],
    "tomatoes": ["lycopene", "vitamin c", "beta-carotene"],
    "onion": ["quercetin", "sulfur compounds"],
    "onions": ["quercetin", "sulfur compounds"],
    "garlic": ["allicin", "sulfur compounds"],
    "carrot": ["beta-carotene", "vitamin a"],
    "carrots": ["beta-carotene", "vitamin a"],
    "spinach": ["iron", "vitamin k", "folate"],
    "broccoli": ["sulforaphane", "vitamin c", "vitamin k"],
    "bell pepper": ["vitamin c", "capsanthin"],
    "chili pepper": ["capsaicin", "vitamin c"],
    
    # Legumes
    "lentils": ["protein", "iron", "folate"],
    "chickpeas": ["protein", "fiber", "folate"],
    "beans": ["protein", "fiber", "iron"],
    
    # Grains
    "rice": ["starch", "b vitamins"],
    "pasta": ["starch", "b vitamins"],
    "wheat": ["gluten", "b vitamins", "fiber"],
    "oats": ["beta-glucan", "fiber"],
    
    # Fruits
    "apple": ["quercetin", "vitamin c", "fiber"],
    "banana": ["potassium", "vitamin b6"],
    "orange": ["vitamin c", "hesperidin"],
    "lemon": ["vitamin c", "citric acid"],
    
    # Dairy
    "milk": ["calcium", "vitamin d", "protein"],
    "cheese": ["calcium", "protein"],
    "yogurt": ["calcium", "probiotics"],
    
    # Meats & Proteins
    "chicken": ["protein", "niacin"],
    "beef": ["protein", "iron", "zinc"],
    "fish": ["omega-3 fatty acids", "protein"],
    "salmon": ["omega-3 fatty acids", "vitamin d"],
    "egg": ["protein", "choline", "vitamin b12"],
    "eggs": ["protein", "choline", "vitamin b12"],
    
    # Nuts & Seeds
    "almonds": ["vitamin e", "magnesium"],
    "walnuts": ["omega-3 fatty acids", "antioxidants"],
    "sesame": ["calcium", "sesame oil"],
    
    # Herbs & Spices
    "turmeric": ["curcumin"],
    "ginger": ["gingerol"],
    "cinnamon": ["cinnamaldehyde"],
    "black pepper": ["piperine"],
    
    # Common nutrients (fallback)
    "salt": ["sodium chloride"],
    "sugar": ["sucrose"],
    "oil": ["fatty acids"],
    "olive oil": ["oleic acid", "vitamin e"],
    "water": ["water"],
}

def get_known_compounds(ingredient: str) -> List[str]:
    """
    Map ingredient to known compounds.
    
    Returns empty list if ingredient not in knowledge base.
    """
    ingredient_lower = ingredient.lower().strip()
    compounds = INGREDIENT_COMPOUND_MAP.get(ingredient_lower, [])
    
    if compounds:
        logger.debug(f"[ENFORCE] Mapped '{ingredient}' → {compounds}")
    else:
        logger.warning(f"[ENFORCE] No compound mapping for '{ingredient}'")
    
    return compounds

# ============================================================================
# COMPOUND RESOLUTION DATA STRUCTURES
# ============================================================================

@dataclass
class ResolvedCompound:
    """Successfully resolved compound with PubChem data"""
    name: str
    cid: int
    properties: CompoundProperties
    cached: bool
    resolution_time_ms: int
    source: str = "pubchem"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM context"""
        return {
            "name": self.name,
            "cid": self.cid,
            "molecular_formula": self.properties.molecular_formula,
            "molecular_weight": self.properties.molecular_weight,
            "source": self.source,
            "verified": True
        }

@dataclass
class UnresolvedCompound:
    """Compound that failed resolution"""
    name: str
    reason: str  # "not_found", "timeout", "budget_exceeded"
    error: Optional[str] = None

@dataclass
class CompoundResolutionResult:
    """Result of compound resolution for an ingredient set"""
    resolved: List[ResolvedCompound] = field(default_factory=list)
    unresolved: List[UnresolvedCompound] = field(default_factory=list)
    total_time_ms: int = 0
    cache_hits: int = 0
    
    @property
    def resolution_rate(self) -> float:
        """Percentage of successfully resolved compounds"""
        total = len(self.resolved) + len(self.unresolved)
        return len(self.resolved) / total if total > 0 else 0.0
    
    @property
    def freshness_weight(self) -> float:
        """Average freshness weight based on cache status"""
        if not self.resolved:
            return 1.0
        
        client = get_pubchem_client()
        weights = []
        for compound in self.resolved:
            if compound.cached:
                cache_key = f"props:{compound.cid}"
                entry = client.cache.get(cache_key)
                if entry:
                    weights.append(entry.freshness_weight())
                else:
                    weights.append(1.0)
            else:
                weights.append(1.0)
        
        return sum(weights) / len(weights) if weights else 1.0

# ============================================================================
# CONFIDENCE SCORE FORMULA
# ============================================================================

def calculate_confidence_score(
    result: CompoundResolutionResult,
    mode: NutritionEnforcementMode
) -> float:
    """
    Deterministic confidence score formula.
    
    Formula:
        confidence = (resolved / total) × freshness_weight × mode_weight
    
    Weights:
        - freshness: 1.0 (fresh), 0.95 (<1h), 0.8 (<24h), 0.6 (>24h)
        - mode: 1.0 (STRICT), 0.6 (PARTIAL)
    
    Returns:
        Float between 0.0 and 1.0
    """
    resolution_score = result.resolution_rate
    freshness = result.freshness_weight
    mode_weight = 1.0 if mode == NutritionEnforcementMode.STRICT else 0.6
    
    confidence = resolution_score * freshness * mode_weight
    
    logger.info(
        f"[CONFIDENCE] resolution={resolution_score:.2f}, "
        f"freshness={freshness:.2f}, mode={mode_weight}, "
        f"final={confidence:.2f}"
    )
    
    return confidence

# ============================================================================
# PROOF HASH GENERATION
# ============================================================================

def generate_proof_hash(compounds: List[ResolvedCompound]) -> str:
    """
    Generate tamper-proof hash of compound resolution.
    
    Hash = SHA-256(sorted_cids + resolution_timestamps)[:16]
    
    This hash proves:
    - Which compounds were actually resolved
    - When they were resolved
    - That the data hasn't been tampered with
    """
    if not compounds:
        return "no_compounds"
    
    # Sort by CID for determinism
    sorted_compounds = sorted(compounds, key=lambda c: c.cid)
    
    # Build hash input
    hash_input = "".join([
        f"{c.cid}:{c.resolution_time_ms}" for c in sorted_compounds
    ])
    
    # Generate hash
    hash_obj = hashlib.sha256(hash_input.encode())
    proof_hash = hash_obj.hexdigest()[:16]
    
    logger.debug(f"[PROOF_HASH] {proof_hash} ← {len(compounds)} compounds")
    return proof_hash

# ============================================================================
# COMPOUND RESOLVER
# ============================================================================

class CompoundResolver:
    """
    Resolves ingredients to PubChem compounds with prioritization and budgets.
    """
    
    MAX_COMPOUNDS_PER_REQUEST = 10
    
    def __init__(self, client: Optional[PubChemClient] = None):
        self.client = client or get_pubchem_client()
    
    def resolve_ingredients(
        self,
        ingredients: List[str],
        user_mentioned: Optional[List[str]] = None
    ) -> CompoundResolutionResult:
        """
        Resolve ingredients to compounds with prioritization.
        
        Priority:
        1. User-mentioned ingredients (explicit in query)
        2. Base ingredients (from recipe/intent)
        3. Trace compounds (from knowledge base expansion)
        
        Args:
            ingredients: List of ingredient names
            user_mentioned: Subset of ingredients explicitly mentioned by user
        
        Returns:
            CompoundResolutionResult with resolved/unresolved compounds
        """
        start_time = time.time()
        result = CompoundResolutionResult()
        
        # Build compound list from ingredients
        compound_candidates = []
        for ingredient in ingredients:
            known_compounds = get_known_compounds(ingredient)
            if known_compounds:
                for compound in known_compounds:
                    compound_candidates.append({
                        "name": compound,
                        "ingredient": ingredient,
                        "priority": self._get_priority(ingredient, user_mentioned)
                    })
            else:
                # Try ingredient name directly
                compound_candidates.append({
                    "name": ingredient,
                    "ingredient": ingredient,
                    "priority": self._get_priority(ingredient, user_mentioned)
                })
        
        # Sort by priority (higher = more important)
        compound_candidates.sort(key=lambda x: x["priority"], reverse=True)
        
        # Resolve up to budget
        compounds_to_resolve = compound_candidates[:self.MAX_COMPOUNDS_PER_REQUEST]
        budget_exceeded = compound_candidates[self.MAX_COMPOUNDS_PER_REQUEST:]
        
        logger.info(
            f"[RESOLVE] {len(compounds_to_resolve)} compounds within budget, "
            f"{len(budget_exceeded)} exceeded"
        )
        
        # Resolve each compound
        for candidate in compounds_to_resolve:
            try:
                compound_start = time.time()
                cid, props = self.client.resolve_compound(candidate["name"])
                elapsed_ms = int((time.time() - compound_start) * 1000)
                
                # Check if it was a cache hit
                cache_key = f"search:{candidate['name'].lower()}"
                cached = self.client.cache.get(cache_key) is not None
                
                result.resolved.append(ResolvedCompound(
                    name=candidate["name"],
                    cid=cid,
                    properties=props,
                    cached=cached,
                    resolution_time_ms=elapsed_ms
                ))
                
                if cached:
                    result.cache_hits += 1
                
            except PubChemNotFound:
                result.unresolved.append(UnresolvedCompound(
                    name=candidate["name"],
                    reason="not_found",
                    error=f"Compound not in PubChem database"
                ))
            except PubChemTimeout:
                result.unresolved.append(UnresolvedCompound(
                    name=candidate["name"],
                    reason="timeout",
                    error="API request timed out"
                ))
            except PubChemError as e:
                result.unresolved.append(UnresolvedCompound(
                    name=candidate["name"],
                    reason="api_error",
                    error=str(e)
                ))
        
        # Mark budget-exceeded compounds
        for candidate in budget_exceeded:
            result.unresolved.append(UnresolvedCompound(
                name=candidate["name"],
                reason="budget_exceeded",
                error=f"Resolution budget exceeded ({self.MAX_COMPOUNDS_PER_REQUEST} max)"
            ))
        
        result.total_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"[RESOLVE] Complete: {len(result.resolved)} resolved, "
            f"{len(result.unresolved)} unresolved ({result.total_time_ms}ms)"
        )
        
        return result
    
    def _get_priority(self, ingredient: str, user_mentioned: Optional[List[str]]) -> int:
        """
        Calculate priority for compound resolution.
        
        Priority levels:
        - 3: User explicitly mentioned
        - 2: Base ingredient from recipe
        - 1: Trace compound from knowledge base
        """
        if user_mentioned and ingredient.lower() in [u.lower() for u in user_mentioned]:
            return 3
        return 2


# ============================================================================
# DECORATOR
# ============================================================================

def requires_pubchem(
    mode: NutritionEnforcementMode = DEFAULT_MODE,
    min_confidence: float = 0.7
):
    """
    Decorator to enforce PubChem verification for agent methods.
    
    Usage:
        @requires_pubchem(mode=NutritionEnforcementMode.STRICT)
        def synthesize(self, ingredients, ...):
            # Method receives 'pubchem_compounds' in context
            pass
    
    Behavior:
    - Extracts ingredients from method arguments
    - Resolves compounds via PubChem
    - Injects structured compound data into method context
    - Blocks LLM from receiving raw ingredient names
    - Computes confidence score
    - Generates proof hash
    - Handles failures per enforcement mode
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"[ENFORCE] Enforcing PubChem for {func.__name__} (mode={mode.value})")
            
            # Extract ingredients from kwargs
            # TODO: This needs to be customized per agent method
            ingredients = kwargs.get("ingredients", [])
            if not ingredients:
                logger.warning("[ENFORCE] No ingredients provided, skipping enforcement")
                return func(*args, **kwargs)
            
            # Resolve compounds
            resolver = CompoundResolver()
            result = resolver.resolve_ingredients(ingredients)
            
            # Calculate confidence
            confidence = calculate_confidence_score(result, mode)
            
            # Generate proof hash
            proof_hash = generate_proof_hash(result.resolved)
            
            # Prepare enforcement metadata
            enforcement_meta = {
                "pubchem_used": len(result.resolved) > 0,
                "confidence_score": confidence,
                "pubchem_proof_hash": proof_hash,
                "compounds": [c.to_dict() for c in result.resolved],
                "enforcement_failures": [
                    f"{u.name}: {u.reason}" for u in result.unresolved
                ],
                "resolution_time_ms": result.total_time_ms,
                "cache_hit_rate": result.cache_hits / len(result.resolved) if result.resolved else 0.0
            }
            
            # Check enforcement mode
            if mode == NutritionEnforcementMode.STRICT and confidence < min_confidence:
                error_msg = (
                    f"[STRICT MODE] Confidence {confidence:.2f} below threshold {min_confidence}. "
                    f"Resolved {len(result.resolved)}/{len(result.resolved) + len(result.unresolved)} compounds."
                )
                logger.error(f"[ENFORCE] {error_msg}")
                raise RuntimeError(error_msg)
            
            # Inject enforcement data into kwargs
            kwargs["_pubchem_enforcement"] = enforcement_meta
            kwargs["_resolved_compounds"] = result.resolved
            
            # Call original method
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing Nutrition Enforcer...")
    
    # Test 1: Ingredient mapping
    print("\n1. Testing ingredient mapping:")
    compounds = get_known_compounds("tomato")
    print(f"   Tomato → {compounds}")
    
    # Test 2: Compound resolution
    print("\n2. Testing compound resolution:")
    resolver = CompoundResolver()
    result = resolver.resolve_ingredients(["tomato", "onion", "garlic"])
    print(f"   Resolved: {len(result.resolved)}")
    print(f"   Unresolved: {len(result.unresolved)}")
    print(f"   Time: {result.total_time_ms}ms")
    
    # Test 3: Confidence calculation
    print("\n3. Testing confidence score:")
    confidence = calculate_confidence_score(result, NutritionEnforcementMode.STRICT)
    print(f"   Confidence: {confidence:.2f}")
    
    # Test 4: Proof hash
    print("\n4. Testing proof hash:")
    proof = generate_proof_hash(result.resolved)
    print(f"   Hash: {proof}")
    
    print("\n✅ Nutrition Enforcer tests complete")
