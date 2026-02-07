"""
Nutri Food Synthesis System - Phase 1 & Phase 2

A reasoning pipeline that invents chemically feasible, nutritionally constrained meals
using retrieved scientific knowledge.

Phase 1: Single-pass RAG + food synthesis reasoning
Phase 2: Intent & constraint extraction agent (Agent 1)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

# Add project root to path for direct execution
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.retriever.faiss_retriever import FaissRetriever
from backend.retriever.router import IndexType
from backend.llm_qwen3 import LLMQwen3
from backend.refinement_engine import RefinementEngine, RefinementResult, FeedbackDelta
from backend.verification.claim_verifier import ClaimVerifier, VerificationReport, VerifiedClaim
from backend.nutrition.vectorizer import NutritionVectorizer, IngredientExtractor
from backend.nutrition.solver import NutritionConstraintSolver, OptimizationResult
from backend.sensory.sensory_types import (
    SensoryProfile, SensoryOptimizationResult, PhysicalProperties, 
    ParetoFrontierResult, SelectionResult, UserPreferences, 
    ExplanationResult, CounterfactualReport, SensitivityRanking,
    MultiCounterfactualReport, IterationState, DesignSessionResult
)
from backend.sensory.property_mapper import SensoryPropertyMapper
from backend.sensory.predictor import SensoryPredictor
from backend.sensory.optimizer import SensoryOptimizer
from backend.sensory.frontier import SensoryParetoOptimizer
from backend.presentation.agent import FinalPresentationAgent
from backend.sensory.selector import VariantSelector
from backend.sensory.explainer import ExplanationLayer
from backend.sensory.counterfactual_engine import CounterfactualEngine
from backend.sensory.explanation_counterfactual import CounterfactualExplainer
from backend.sensory.counterfactual_multi_engine import MultiCounterfactualEngine
from backend.sensory.explanation_interactive import InteractiveExplainer
from backend.sensory.interactive_design_loop import InteractiveDesignLoop

from backend.nutrition_enforcer import (
    CompoundResolver,
    calculate_confidence_score,
    generate_proof_hash,
    NutritionEnforcementMode,
    ResolvedCompound,
    NutritionEnforcer
)
from backend.pubchem_client import PubChemError

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS (VERBATIM FROM REQUIREMENTS)
# =============================================================================

PHASE1_SYSTEM_PROMPT = """You are Nutri, a food formulation and cooking science system.

Your task is to INVENT meals and recipes from first principles,
not recall existing recipes.

You must:
- Treat ingredients as chemical and nutritional components
- Reason about reactions, texture, flavor, and feasibility
- Obey physical and chemical constraints
- Obey nutritional constraints when provided

You are NOT allowed to:
- Assume missing ingredients
- Invent impossible reactions
- Rely on "common recipes" unless justified chemically

You must think in this order:
1. Assign functional roles to ingredients (protein, fat, water, acid, structure)
2. Determine which chemical reactions are possible
3. Design texture and structure
4. Design flavor layering
5. Estimate nutrition conservatively
6. Explain WHY the recipe works chemically

If something is not possible, you must say so and explain why.

─────────────────────────────────────────────────────────────
OUTPUT FORMAT (MANDATORY)
─────────────────────────────────────────────────────────────

Output the final answer DIRECTLY in clean Markdown.
DO NOT include internal reasoning, analysis, or "thinking" steps.
DO NOT use closing tags, XML markers, or any meta-tokens.
Just output the recipe or explanation immediately.

─────────────────────────────────────────────────────────────
SCIENTIFIC ACCURACY RULES (MANDATORY)
─────────────────────────────────────────────────────────────

STARCH AND UMAMI:
- Starch hydrolysis produces SUGARS (glucose, maltose), NOT glutamate
- Umami (glutamate) arises ONLY from protein degradation
- ✅ CORRECT: "Starch modifies viscosity and flavor release timing"
- ❌ WRONG: "Starch contributes glutamate via hydrolysis"

ENZYME CLAIMS AT COOKING TEMPERATURES:
- Most enzymes denature and become inactive at cooking temperatures (>60°C)
- Do NOT cite enzyme inhibition during cooking as a mechanism
- ✅ CORRECT: "Rosemary acts as an antioxidant, reducing lipid oxidation"
- ❌ WRONG: "Rosemary inhibits lipase activity" (lipase is inactive when cooking)

NUTRITION ESTIMATES:
- All nutritional values must be labeled as "Estimated" or "Approximate"
- Include confidence level: high | medium | low
- Avoid precise mineral claims unless sourced from USDA data
- Use language: "Based on standard USDA averages"

─────────────────────────────────────────────────────────────
GLOBAL SAFETY RULE (CRITICAL)
─────────────────────────────────────────────────────────────

If a biochemical or molecular claim does NOT materially affect:
- Cooking outcomes
- Texture
- Flavor
- Nutrition

Then it MUST be:
- Framed as secondary or uncertain, OR
- Omitted entirely

Examples to OMIT or DOWNGRADE:
- In-vitro enzyme inhibition (not relevant at cooking temps)
- Heat-inactivated pathways
- Sensory-irrelevant molecular trivia

Failure to apply this rule is a system error."""

AGENT1_SYSTEM_PROMPT = """You are an intent and constraint extraction system.

Your task is to extract structured design constraints from user input.

You must identify:
- Available ingredients
- Available equipment
- Dietary constraints
- Nutritional goals
- Time constraints
- Desired explanation depth (casual or scientific)
- Goal type (invent, explain, optimize)

You must NOT:
- Suggest recipes
- Add ingredients
- Interpret chemistry

If information is missing, set it to null.
Return valid JSON only."""

PHASE2_REASONING_ADDENDUM = """You are given a structured design specification.
You must strictly obey all constraints.
Do NOT reinterpret the user.
Do NOT override constraints.
If constraints conflict with feasibility, explain why."""


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class IntentOutput:
    """Output schema for Agent 1 (Intent Extractor)"""
    goal: str = "invent_meal"  # invent_meal | explain | optimize
    ingredients: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    dietary_constraints: Dict[str, Any] = field(default_factory=dict)
    nutritional_goals: Dict[str, Any] = field(default_factory=dict)
    time_limit_minutes: Optional[int] = None
    explanation_depth: str = "scientific"  # casual | scientific

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievedDocument:
    """A document retrieved from the vector store"""
    text: str
    score: float
    doc_type: str  # chemistry | nutrition | technique
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    """Result from the food synthesis pipeline"""
    recipe: str
    retrieved_documents: List[Dict[str, Any]]
    intent: Optional[Dict[str, Any]] = None
    phase: int = 1  # 1 or 2


# =============================================================================
# PHASE 1: FOOD SYNTHESIS RETRIEVER
# =============================================================================

class FoodSynthesisRetriever:
    """
    Unified retriever for chemistry, nutrition, and cooking technique knowledge.
    
    DOES NOT retrieve recipes (recipes are OUTPUTS, not INPUTS).
    
    Uses existing FaissRetriever infrastructure to search:
    - chemistry: Ingredient chemistry, reactions, compounds
    - science: Cooking physics, texture formation, heat effects
    - usda_foundation: Nutrition data for raw ingredients
    - usda_branded: Nutrition data for processed foods
    """
    
    # Index types to search (explicitly NO recipes)
    SEARCH_INDEXES = [
        IndexType.CHEMISTRY,
        IndexType.SCIENCE,
        IndexType.USDA_FOUNDATION,
        IndexType.USDA_BRANDED,
    ]
    
    # Map index types to document types
    # Map index types to document types
    INDEX_TO_DOC_TYPE = {
        IndexType.CHEMISTRY: "chemistry",
        IndexType.SCIENCE: "technique",
        IndexType.USDA_FOUNDATION: "nutrition",
        IndexType.USDA_BRANDED: "nutrition",
        IndexType.OPEN_NUTRITION: "nutrition",
    }
    
    # Phase-Aware Routing Table
    PHASE_INDEX_MAP = {
        # Phase 1-2: Intent & Broad Feasibility (Fast, Low Mem)
        1: [IndexType.SCIENCE, IndexType.USDA_FOUNDATION],
        2: [IndexType.SCIENCE, IndexType.USDA_FOUNDATION],
        
        # Phase 3-5: Validation & Variant Gen (Needs specific products)
        3: [IndexType.SCIENCE, IndexType.USDA_FOUNDATION, IndexType.USDA_BRANDED],
        4: [IndexType.SCIENCE, IndexType.USDA_FOUNDATION, IndexType.USDA_BRANDED],
        5: [IndexType.SCIENCE, IndexType.USDA_FOUNDATION, IndexType.USDA_BRANDED],
        
        # Phase 6-8: Optimization & Frontiers (Deep Science)
        6: [IndexType.SCIENCE, IndexType.CHEMISTRY],
        7: [IndexType.SCIENCE, IndexType.CHEMISTRY],
        8: [IndexType.SCIENCE, IndexType.CHEMISTRY],
        
        # Phase 9-12: Scoring & Explanation (Full Spectrum minus Branded if heavy)
        9: [IndexType.SCIENCE, IndexType.CHEMISTRY, IndexType.USDA_FOUNDATION, IndexType.OPEN_NUTRITION],
        10: [IndexType.SCIENCE, IndexType.CHEMISTRY, IndexType.USDA_FOUNDATION],
        11: [IndexType.SCIENCE, IndexType.CHEMISTRY, IndexType.USDA_FOUNDATION],
        12: [IndexType.SCIENCE, IndexType.CHEMISTRY, IndexType.USDA_FOUNDATION],
        
        # Phase 13: Final Response (No Retrieval)
        13: [] 
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the retriever with safe memory management.
        
        Args:
            project_root: Root directory of the project (auto-detected if None)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        
        # Use IndexManager for safe lazy-loading
        from backend.retriever.index_manager import IndexManager
        self.index_manager = IndexManager(self.project_root)
        
        logger.info(f"FoodSynthesisRetriever initialized at {self.project_root}")
    
    def retrieve_for_phase(
        self,
        phase: int,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3
    ) -> List[RetrievedDocument]:
        """
        Retrieve documents relevant for a specific pipeline phase.
        Respects memory budgets by only loading phase-critical indices.
        """
        allowed_indices = self.PHASE_INDEX_MAP.get(phase, [IndexType.SCIENCE])
        
        logger.info(f"🔎 Phase {phase} Retrieval: Query='{query[:50]}...' Indices={[t.value for t in allowed_indices]}")
        
        return self.retrieve(
            query=query,
            top_k=top_k,
            min_score=min_score,
            target_indices=allowed_indices
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        target_indices: Optional[List[IndexType]] = None
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents from specified (or default) indexes.
        
        Args:
            query: Search query
            top_k: Number of results per index
            min_score: Minimum similarity score threshold
            target_indices: Specific indices to search. If None, uses defaults (NOT RECOMMENDED for memory safety).
            
        Returns:
            List of RetrievedDocument objects, sorted by score
        """
        all_results: List[RetrievedDocument] = []
        
        # Default to safe indices if none specified
        if target_indices is None:
            target_indices = [IndexType.SCIENCE, IndexType.USDA_FOUNDATION]
            logger.warning("Implicit retrieval requested. Defaulting to safe indices (Science, Foundation).")
        
        for index_type in target_indices:
            # Use IndexManager to get the retriever safely
            # This handles lazy loading and eviction automatically
            retriever = self.index_manager.get_retriever(index_type)
            
            if retriever is None:
                continue
            
            try:
                results = retriever.search(query, top_k=top_k, min_score=min_score)
                
                doc_type = self.INDEX_TO_DOC_TYPE.get(index_type, "unknown")
                
                for r in results:
                    doc = RetrievedDocument(
                        text=r.get('text', ''),
                        score=r.get('score', 0.0),
                        doc_type=doc_type,
                        source=r.get('source', index_type.value),
                        metadata=r.get('metadata', {})
                    )
                    all_results.append(doc)
                    
                logger.info(f"Retrieved {len(results)} docs from {index_type.value}")
                
            except Exception as e:
                logger.error(f"Search failed on {index_type}: {e}")
        
        # Sort by score descending
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Log retrieved documents (LOGGING REQUIREMENT)
        logger.info(f"Total retrieved: {len(all_results)} documents")
        for i, doc in enumerate(all_results[:5]):
            logger.debug(f"  [{i+1}] {doc.doc_type}: {doc.text[:100]}... (score: {doc.score:.3f})")
        
        return all_results[:top_k * 2]  # Return more for synthesis


# =============================================================================
# PHASE 2: INTENT & CONSTRAINT EXTRACTION AGENT
# =============================================================================

class IntentAgent:
    """
    Agent 1: Intent & Constraint Extraction System
    
    Extracts structured design constraints from user input.
    Does NO food reasoning - only extraction and normalization.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the intent extraction agent.
        
        Args:
            model_name: Optional model override
        """
        self.llm = LLMQwen3(agent_name="intent_agent", model_name=model_name)
        logger.info("IntentAgent initialized")
    
    def extract(self, user_input: str, stream_callback: Optional[callable] = None) -> IntentOutput:
        """
        Extract structured constraints from user input.
        
        Args:
            user_input: Raw user query
            stream_callback: Optional callback for token streaming
            
        Returns:
            IntentOutput with extracted constraints
        """
        logger.info(f"Extracting intent from: {user_input[:100]}...")
        
        messages = [
            {"role": "system", "content": AGENT1_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = self.llm.generate_text(
                messages=messages,
                max_new_tokens=2048, # Increased from 512
                temperature=0.1,  # Low temperature for structured extraction
                stream_callback=stream_callback
            )
            
            # Log Agent 1 output (LOGGING REQUIREMENT)
            logger.info(f"Agent 1 raw output: {response}")
            
            # Parse JSON from response
            intent = self._parse_json_response(response)
            
            logger.info(f"Extracted intent: {intent.to_dict()}")
            return intent
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Return default intent on failure
            return IntentOutput(
                goal="invent_meal",
                ingredients=self._extract_ingredients_fallback(user_input),
                explanation_depth="scientific"
            )
    
    def _parse_json_response(self, response: str) -> IntentOutput:
        """Parse JSON from LLM response."""
        # Try to find JSON in response
        try:
            # Look for JSON block
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                
                return IntentOutput(
                    goal=data.get('goal', 'invent_meal'),
                    ingredients=data.get('ingredients', []),
                    equipment=data.get('equipment', []),
                    dietary_constraints=data.get('dietary_constraints', {}),
                    nutritional_goals=data.get('nutritional_goals', {}),
                    time_limit_minutes=data.get('time_limit_minutes'),
                    explanation_depth=data.get('explanation_depth', 'scientific')
                )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
        
        return IntentOutput()
    
    def _extract_ingredients_fallback(self, text: str) -> List[str]:
        """Simple fallback ingredient extraction."""
        # Basic keyword extraction - not sophisticated
        common_ingredients = [
            'egg', 'flour', 'butter', 'sugar', 'salt', 'milk', 'chicken',
            'beef', 'pork', 'fish', 'rice', 'pasta', 'tomato', 'onion',
            'garlic', 'olive oil', 'cheese', 'bread', 'potato', 'carrot'
        ]
        
        text_lower = text.lower()
        found = [ing for ing in common_ingredients if ing in text_lower]
        return found


# =============================================================================
# FOOD SYNTHESIS ENGINE
# =============================================================================

class FoodSynthesisEngine:
    """
    Single LLM call processor for food synthesis reasoning.
    
    Uses retrieved knowledge to invent chemically feasible meals.
    """
    
    def __init__(self, model_name: Optional[str] = None, enforcement_mode: NutritionEnforcementMode = NutritionEnforcementMode.STRICT):
        """
        Initialize the synthesis engine.
        
        Args:
            model_name: Optional model override
            enforcement_mode: PubChem enforcement mode (STRICT or PARTIAL)
        """
        self.llm = LLMQwen3(agent_name="synthesis_engine", model_name=model_name)
        self.compound_resolver = CompoundResolver()
        self.enforcement_mode = enforcement_mode
        
        # 📋 PHASE 1-3 Intelligence Hardening Components
        from backend.claim_parser import ClaimParser
        from backend.claim_verifier import ClaimVerifier
        from backend.nutrition_uncertainty import UncertaintyCalculator
        from backend.usda_client import USDAClient
        
        self.claim_parser = ClaimParser(llm_engine=self.llm)
        self.usda_client = USDAClient()
        self.claim_verifier = ClaimVerifier(
            pubchem_client=self.compound_resolver.client,
            usda_client=self.usda_client,
            rag_engine=None # Will be connected via orchestrator if needed
        )
        self.uncertainty_calculator = UncertaintyCalculator()
        
        logger.info(f"FoodSynthesisEngine initialized (enforcement={enforcement_mode.value})")
    
    @NutritionEnforcer.requires_pubchem
    def synthesize(
        self,
        user_query: str,
        retrieved_docs: List[RetrievedDocument],
        intent: Optional[IntentOutput] = None,
        stream_callback: Optional[callable] = None,
        boundary_token: Optional[str] = None,
        **kwargs
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate a novel recipe with chemical explanation.
        
        Args:
            user_query: Original user request
            retrieved_docs: Documents from retriever
            intent: Optional structured constraints from Agent 1
            stream_callback: Optional callback for token streaming
            
        Returns:
            Tuple of (generated_recipe, enforcement_metadata)
        """
        # 🔬 PUBCHEM ENFORCEMENT (Injected via Decorator)
        enforcement_meta = {}
        compound_context = ""
        resolution_result = kwargs.get("pubchem_data")

        if resolution_result:
            logger.info(f"[PUBCHEM_ENFORCE] Received {len(resolution_result.resolved)} resolved compounds")
            
            try:
                # Calculate confidence
                confidence = calculate_confidence_score(
                    resolution_result,
                    self.enforcement_mode
                )
                
                # Generate proof hash
                proof_hash = generate_proof_hash(resolution_result.resolved)
                
                # Build enforcement metadata
                enforcement_meta = {
                    "pubchem_used": len(resolution_result.resolved) > 0,
                    "confidence_score": confidence,
                    "pubchem_proof_hash": proof_hash,
                    "compounds_resolved": len(resolution_result.resolved),
                    "compounds_failed": len(resolution_result.unresolved),
                    "resolution_time_ms": resolution_result.total_time_ms,
                    "enforcement_failures": [
                        f"{u.name}: {u.reason}" for u in resolution_result.unresolved
                    ],
                    "resolved_compounds": [
                        {
                            "name": c.name,
                            "cid": c.cid,
                            "cached": c.cached,
                            "resolution_time_ms": c.resolution_time_ms,
                            "properties": c.properties
                        } for c in resolution_result.resolved
                    ]
                }
                
                # Build compound context for LLM
                compound_context = self._build_compound_context(resolution_result.resolved)
                
                # STRICT mode enforcement
                if self.enforcement_mode == NutritionEnforcementMode.STRICT and confidence < 0.7:
                    error = f"[STRICT MODE] Confidence {confidence:.2f} below threshold. Resolved {len(resolution_result.resolved)}/{len(resolution_result.resolved) + len(resolution_result.unresolved)} compounds."
                    logger.error(error)
                    return (f"⚠️ Unable to generate recipe: {error}", enforcement_meta)
                
                logger.info(
                    f"[PUBCHEM_ENFORCE] Resolution complete. confidence={confidence:.2f}, hash={proof_hash}"
                )
                
            except Exception as e:
                logger.error(f"[PUBCHEM_ENFORCE] Processing resolution failed: {e}")
                if self.enforcement_mode == NutritionEnforcementMode.STRICT:
                    return (f"⚠️ Unable to generate recipe: PubChem resolution failed", enforcement_meta)
        
        # Build context from retrieved documents
        context = self._build_context(retrieved_docs)
        
        # Build system prompt
        if intent:
            # Phase 2: Include constraint addendum
            system_prompt = f"{PHASE1_SYSTEM_PROMPT}\n\n{PHASE2_REASONING_ADDENDUM}"
            user_content = self._build_constrained_query(
                user_query, intent, context, compound_context
            )
        else:
            # Phase 1: Simple synthesis
            system_prompt = PHASE1_SYSTEM_PROMPT
            user_content = self._build_simple_query(user_query, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        logger.info("Generating food synthesis...")
        
        try:
            response = self.llm.generate_text(
                messages=messages,
                max_new_tokens=4096,  # Increased for complete recipes
                temperature=0.4,  # Slightly creative but grounded
                stream_callback=stream_callback,
                boundary_token=boundary_token
            )
            
            # Log final reasoning output (LOGGING REQUIREMENT)
            logger.info(f"Synthesis output length: {len(response)} chars")
            
            # 📋 TIER 1 INTELLIGENCE HARDENING (PHASE 4)
            # 1. Atomic Claim Extraction
            claims = self.claim_parser.parse(response)
            
            # 2. Claim Verification
            verifications = self.claim_verifier.verify_claims(claims)
            
            # 3. Uncertainty Modeling
            # Detect active variance drivers (Heuristic for now)
            active_drivers = []
            if "optional" in response.lower() or "substitution" in response.lower():
                active_drivers.append("ingredient_substitution")
            if "serving" not in response.lower() and "portion" not in response.lower():
                active_drivers.append("portion_ambiguity")
            if str(enforcement_meta.get("confidence_score", 1.0)) < "1.0":
                active_drivers.append("incomplete_resolution")
            
            uncertainty_report = self.uncertainty_calculator.calculate(
                claims=verifications,
                global_drivers=active_drivers
            )
            
            # 4. Integrate into enforcement metadata
            enforcement_meta.update({
                "claims": [v.__dict__ for v in verifications],
                "final_confidence": uncertainty_report.response_confidence,
                "variance_drivers": uncertainty_report.variance_drivers,
                "uncertainty_explanation": uncertainty_report.explanation,
                "weakest_link_id": uncertainty_report.weakest_link_id,
                "verification_summary": {
                    "verified_claims": sum(1 for v in verifications if v.verified),
                    "unverified_claims": sum(1 for v in verifications if not v.verified),
                    "total_claims": len(verifications),
                    "conflicts_detected": any(v.metadata.get("has_conflict") for v in verifications)
                }
            })
            
            # Return response with hardened enforcement metadata
            return (response, enforcement_meta)
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return (f"Error: Unable to generate recipe. {str(e)}", enforcement_meta)
    
    def _build_context(self, docs: List[RetrievedDocument]) -> str:
        """Build context string from retrieved documents."""
        if not docs:
            return "No scientific knowledge retrieved."
        
        sections = {
            "chemistry": [],
            "nutrition": [],
            "technique": []
        }
        
        for doc in docs:
            if doc.doc_type in sections:
                sections[doc.doc_type].append(doc.text)
        
        context_parts = []
        
        if sections["chemistry"]:
            context_parts.append("## Chemistry Knowledge\n" + "\n".join(sections["chemistry"][:3]))
        
        if sections["nutrition"]:
            context_parts.append("## Nutrition Data\n" + "\n".join(sections["nutrition"][:3]))
        
        if sections["technique"]:
            context_parts.append("## Cooking Techniques\n" + "\n".join(sections["technique"][:3]))
        
        return "\n\n".join(context_parts)
    
    def _build_simple_query(self, query: str, context: str) -> str:
        """Build Phase 1 query."""
        return f"""Based on the following scientific knowledge:

{context}

User request: {query}

Invent a novel dish following the reasoning steps in your instructions."""
    
    def _build_compound_context(self, compounds: List[ResolvedCompound]) -> str:
        """
        Build structured compound context for LLM.
        
        LLM receives ONLY this structured data, not raw ingredient names.
        This prevents hallucination by gating information flow.
        """
        if not compounds:
            return ""
        
        compound_lines = []
        for c in compounds:
            compound_lines.append(
                f"- **{c.name}** (CID: {c.cid}): "
                f"{c.properties.molecular_formula}, "
                f"MW {c.properties.molecular_weight:.1f}g/mol"
            )
        
        return "\n".join([
            "\n## PubChem-Verified Compounds (Use ONLY These)",
            "The following compounds have been verified via PubChem.",
            "Base your chemical reasoning EXCLUSIVELY on these verified compounds.",
            "",
            *compound_lines
        ])
    
    def _build_constrained_query(
        self,
        query: str,
        intent: IntentOutput,
        context: str,
        compound_context: str = ""
    ) -> str:
        """Build Phase 2 query with structured constraints."""
        # Defensive: Handle both IntentOutput object and dict
        if hasattr(intent, "to_dict"):
            constraints = intent.to_dict()
        elif isinstance(intent, dict):
            constraints = intent
        else:
            logger.warning(f"Unknown intent type: {type(intent)}. Defaulting to empty constraints.")
            constraints = {}
        
        constraint_section = f"""Based on the following scientific knowledge:

{context}
{compound_context}

## Design Constraints (MUST OBEY)
```json
{json.dumps(constraints, indent=2)}
```

User request: {query}

Invent a novel dish following the reasoning steps in your instructions.
You MUST obey all constraints above."""


# =============================================================================
# NUTRI PIPELINE - MAIN ORCHESTRATOR
# =============================================================================

class NutriPipeline:
    """
    Main orchestrator for the Nutri food synthesis system.
    
    Phase 1: Input → Retrieval → Synthesis
    Phase 2: Input → Agent 1 → Retrieval → Synthesis
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_phase2: bool = True
    ):
        """
        Initialize the full Nutri pipeline.
        
        Args:
            model_name: Optional model override
            use_phase2: Whether to use Agent 1 for intent extraction
        """
        self.retriever = FoodSynthesisRetriever()
        self.engine = FoodSynthesisEngine(model_name=model_name)
        self.intent_agent = IntentAgent(model_name=model_name) if use_phase2 else None
        self.presentation_agent = FinalPresentationAgent(self.engine.llm)
        self.use_phase2 = use_phase2
        
        logger.info(f"NutriPipeline initialized (Phase {'2' if use_phase2 else '1'})")
    
    def synthesize(self, user_input: str) -> SynthesisResult:
        """
        Process user input and generate a novel recipe.
        
        Args:
            user_input: User's request
            
        Returns:
            SynthesisResult with recipe, retrieved docs, and intent
        """
        logger.info(f"Processing request: {user_input[:100]}...")
        
        intent = None
        
        # Phase 2: Extract intent first
        if self.use_phase2 and self.intent_agent:
            intent = self.intent_agent.extract(user_input)
            
            # Build retrieval query from ingredients if available
            if intent.ingredients:
                retrieval_query = f"{user_input} {' '.join(intent.ingredients)}"
            else:
                retrieval_query = user_input
        else:
            retrieval_query = user_input
        
        # Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve_for_phase(2, retrieval_query, top_k=2)
        
        # Synthesize recipe
        recipe = self.engine.synthesize(
            user_query=user_input,
            retrieved_docs=retrieved_docs,
            intent=intent,
            stream_callback=stream_callback,
            boundary_token=boundary_token
        )
        
        # Build result
        result = SynthesisResult(
            recipe=recipe,
            retrieved_documents=[
                {
                    "text": doc.text[:200] + "..." if len(doc.text) > 200 else doc.text,
                    "type": doc.doc_type,
                    "score": doc.score,
                    "source": doc.source
                }
                for doc in retrieved_docs[:5]
            ],
            intent=intent.to_dict() if intent else None,
            phase=2 if self.use_phase2 else 1
        )
        
        logger.info(f"Synthesis complete: Phase {result.phase}")
        return result
    
    def synthesize_phase1(self, user_input: str) -> SynthesisResult:
        """
        Force Phase 1 processing (no intent extraction).
        
        Args:
            user_input: User's request
            
        Returns:
            SynthesisResult
        """
        # Temporarily disable phase 2
        original = self.use_phase2
        self.use_phase2 = False
        
        try:
            result = self.synthesize(user_input)
            result.phase = 1
            return result
        finally:
            self.use_phase2 = original
    
    def refine(
        self,
        previous: SynthesisResult,
        feedback: str
    ) -> RefinementResult:
        """
        Phase 3: Refine a previously generated recipe based on user feedback.
        
        Args:
            previous: Previous SynthesisResult from synthesize()
            feedback: User's refinement feedback (e.g., "More protein", "Make it crispier")
            
        Returns:
            RefinementResult with refined recipe, changes, and chemical justification
        """
        logger.info(f"Refining recipe with feedback: {feedback[:100]}...")
        
        # Lazy-load refinement engine
        if not hasattr(self, '_refinement_engine') or self._refinement_engine is None:
            self._refinement_engine = RefinementEngine()
        
        # Retrieve additional knowledge based on feedback
        retrieved_docs = self.retriever.retrieve_for_phase(3, feedback, top_k=5)
        docs_for_refinement = [
            {
                "text": doc.text,
                "type": doc.doc_type,
                "score": doc.score,
                "source": doc.source
            }
            for doc in retrieved_docs
        ]
        
        # Execute refinement
        result = self._refinement_engine.refine(
            previous_recipe=previous.recipe,
            original_intent=previous.intent or {},
            feedback=feedback,
            retrieved_docs=docs_for_refinement
        )
        
        logger.info(f"Refinement complete: confidence={result.confidence}")
        return result

    def verify(self, result: Any) -> VerificationReport:
        """
        Phase 4: Verify scientific claims in a synthesis result.
        
        Args:
            result: SynthesisResult or RefinementResult
            
        Returns:
            VerificationReport with verified/flagged claims
        """
        # Lazy-load verifier
        if not hasattr(self, '_verifier') or self._verifier is None:
            self._verifier = ClaimVerifier()
            
        # Extract text to verify (recipe + justification if available)
        text_to_verify = ""
        if hasattr(result, 'recipe'):
            text_to_verify += result.recipe
            
        if hasattr(result, 'chemical_justification'):
            text_to_verify += "\n\n" + result.chemical_justification
            
        logger.info("Verifying scientific claims...")
        report = self._verifier.verify(text_to_verify, self.retriever)
        
        logger.info(f"Verification complete: {len(report.verified_claims)} verified, {len(report.flagged_claims)} flagged")
        return report

    def optimize(self, result: Any, goals: Dict[str, Any]) -> OptimizationResult:
        """
        Phase 5: Optimize nutrition.
        
        Args:
            result: SynthesisResult or RefinementResult (recipe source)
            goals: Constraints e.g. {"maximize": "protein", "constraints": {"calories": {"max": 600}}}
            
        Returns:
             OptimizationResult with math stats and re-explained recipe
        """
        # Lazy load components
        if not hasattr(self, '_ingredient_extractor') or self._ingredient_extractor is None:
            self._ingredient_extractor = IngredientExtractor()
            self._nutrition_vectorizer = NutritionVectorizer()
            self._solver = NutritionConstraintSolver()
            
        recipe_text = getattr(result, 'recipe', str(result))
        logger.info("Starting nutrition optimization...")
        
        # 1. Extract ingredients
        ingredients_data = self._ingredient_extractor.extract(recipe_text)
        if not ingredients_data:
            res = OptimizationResult({}, {}, ["Failed to extract ingredients from recipe text"], "low")
            res.recipe_explanation = "Error: Could not extract ingredients for optimization. Please check if the recipe format is standard."
            return res
            
        # 2. Vectorize
        vectorized_ingredients = []
        for ing in ingredients_data:
            name = ing['name']
            vector = self._nutrition_vectorizer.vectorize(name, self.retriever)
            ing['vector'] = vector
            vectorized_ingredients.append(ing)
            
        # 3. Solve
        opt_result = self._solver.solve(vectorized_ingredients, goals)
        
        if opt_result.confidence == "low":
            opt_result.recipe_explanation = "Optimization failed to find a valid solution within safety bounds."
            return opt_result

        # 4. Re-explain recipe
        reexplained_recipe = self._reexplain_optimization(recipe_text, opt_result)
        opt_result.recipe_explanation = reexplained_recipe
        return opt_result

    def _reexplain_optimization(self, original_recipe: str, opt_result: OptimizationResult) -> str:
        """Ask LLM to update recipe with optimized amounts."""
        
        changes = []
        for name, amount in opt_result.optimized_ratios.items():
            orig = opt_result.original_totals.get(name) # Wait, original_totals stores nutrients, need original amounts
            # We don't have direct mapping of original amounts in opt_result easily unless we passed them.
            # But specific amounts are in opt_result.optimized_ratios.
            changes.append(f"{name}: {amount:.1f}g")
            
        changes_str = "\n".join(changes)
        
        prompt = f"""You are Nutri. The user has requested a NUTRITION OPTIMIZATION.
        
Original Recipe:
{original_recipe}

The scientific solver has calculated these OPTIMAL INGREDIENT QUANTITIES to meet nutritional goals:
{changes_str}

Task:
1. Rewrite the recipe with these EXACT new quantities.
2. Explain how these changes impact the nutrition (e.g. "Increased protein by increasing chicken to 150g").
3. Verify if cooking times need slight adjustment based on quantity changes.

Keep the same format as the original."""

        messages = [
            {"role": "system", "content": PHASE1_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        try:
            return self.engine.llm.generate_text(messages, max_new_tokens=2048, temperature=0.3)
        except Exception as e:
            return f"Optimization successful, but re-explanation failed: {e}. New amounts: {changes_str}"

    def predict_sensory(self, recipe_text: str, ingredients: Optional[List[Dict]] = None) -> SensoryProfile:
        """
        Phase 6: Predict the sensory profile (texture, flavor, mouthfeel) of a recipe.
        
        Args:
            recipe_text: Full text of the recipe
            ingredients: Optional list of extracted ingredients with amounts (g).
                        If None, they will be extracted automatically.
                        
        Returns:
            SensoryProfile with predicted vectors and scientific justification.
        """
        logger.info("Predicting sensory profile...")
        
        # 1. Lazy-load sensory components
        if not hasattr(self, '_sensory_mapper') or self._sensory_mapper is None:
            self._sensory_mapper = SensoryPropertyMapper(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_sensory_predictor') or self._sensory_predictor is None:
            self._sensory_predictor = SensoryPredictor(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_ingredient_extractor') or self._ingredient_extractor is None:
            self._ingredient_extractor = IngredientExtractor(model_name=self.engine.llm.model_name)
            
        # 2. Extract ingredients if not provided
        if not ingredients:
            logger.info("No ingredients provided for sensory mapping, extracting...")
            ingredients = self._ingredient_extractor.extract(recipe_text)
            
        if not ingredients:
            return SensoryProfile(
                scientific_explanation="Could not extract ingredients for sensory mapping.",
                confidence="low",
                warnings=["Insufficient ingredient data for mechanistic prediction."]
            )
            
        # 3. Map ingredients to physical properties
        properties_list = []
        aggregated_provenance = {"used_recipes_store": False, "used_open_nutrition": False}
        
        for ing in ingredients:
            name = ing.get("name")
            amount = ing.get("amount_g", 0)
            if name and amount > 0:
                props, provenance = self._sensory_mapper.map_ingredient(name, amount, self.retriever)
                properties_list.append(props)
                # Propagate provenance
                if provenance["used_recipes_store"]: aggregated_provenance["used_recipes_store"] = True
                if provenance["used_open_nutrition"]: aggregated_provenance["used_open_nutrition"] = True
                
        # 4. Predict sensory outcome
        return self._sensory_predictor.predict(recipe_text, properties_list, aggregated_provenance)

    def optimize_sensory(self, recipe_text: str, max_iter: int = 3) -> SensoryOptimizationResult:
        """
        Closed-loop sensory optimization (Phase 7).
        """
        logger.info("Starting closed-loop sensory optimization...")

        # 1. Lazy-load sensory components
        if not hasattr(self, '_sensory_mapper') or self._sensory_mapper is None:
            self._sensory_mapper = SensoryPropertyMapper(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_sensory_predictor') or self._sensory_predictor is None:
            self._sensory_predictor = SensoryPredictor(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_ingredient_extractor') or self._ingredient_extractor is None:
            self._ingredient_extractor = IngredientExtractor(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_sensory_optimizer') or self._sensory_optimizer is None:
            from backend.sensory.optimizer import SensoryOptimizer
            self._sensory_optimizer = SensoryOptimizer(self.engine, self._sensory_predictor)

        # 2. Extract ingredients
        ingredients = self._ingredient_extractor.extract(recipe_text)
        if not ingredients:
            return SensoryOptimizationResult(
                final_recipe=recipe_text,
                final_profile=SensoryProfile(scientific_explanation="Could not extract ingredients."),
                log=[], success=False, message="Extraction failed."
            )

        # 3. Map ingredients to properties (needed for each iteration evaluation)
        properties_list = []
        aggregated_provenance = {"used_recipes_store": False, "used_open_nutrition": False}
        for ing in ingredients:
            name = ing.get("name")
            amount = ing.get("amount_g", 0)
            if name and amount > 0:
                props, provenance = self._sensory_mapper.map_ingredient(
                    name, 
                    amount, 
                    self.retriever,
                    idx=i+1,
                    total=len(ingredients_list)
                )
                properties_list.append(props)
                if provenance["used_recipes_store"]: aggregated_provenance["used_recipes_store"] = True
                if provenance["used_open_nutrition"]: aggregated_provenance["used_open_nutrition"] = True

        # 4. Run closed-loop optimization
        return self._sensory_optimizer.optimize(recipe_text, properties_list, aggregated_provenance, max_iter=max_iter)

    def generate_sensory_frontier(self, recipe_text: str, objectives: Optional[Dict[str, str]] = None) -> ParetoFrontierResult:
        """
        Generates multiple recipe variants on the sensory Pareto frontier (Phase 8).
        """
        logger.info("Generating sensory Pareto frontier variants...")

        # 1. Lazy-load sensory components
        if not hasattr(self, '_sensory_mapper') or self._sensory_mapper is None:
            self._sensory_mapper = SensoryPropertyMapper(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_sensory_predictor') or self._sensory_predictor is None:
            self._sensory_predictor = SensoryPredictor(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_ingredient_extractor') or self._ingredient_extractor is None:
            self._ingredient_extractor = IngredientExtractor(model_name=self.engine.llm.model_name)
        if not hasattr(self, '_sensory_frontier') or self._sensory_frontier is None:
            from backend.sensory.frontier import SensoryParetoOptimizer
            self._sensory_frontier = SensoryParetoOptimizer(self.engine, self._sensory_predictor)

        # 2. Extract and Map (once for properties, used for all predictions)
        ingredients = self._ingredient_extractor.extract(recipe_text)
        properties_list = []
        aggregated_provenance = {"used_recipes_store": False, "used_open_nutrition": False}
        
        if ingredients:
            for i, ing in enumerate(ingredients):
                name = ing.get("name")
                amount = ing.get("amount_g", 0)
                if name and amount > 0:
                    props, provenance = self._sensory_mapper.map_ingredient(
                        name, 
                        amount, 
                        self.retriever,
                        idx=i+1,
                        total=len(ingredients)
                    )
                    properties_list.append(props)
                    if provenance["used_recipes_store"]: aggregated_provenance["used_recipes_store"] = True
                    if provenance["used_open_nutrition"]: aggregated_provenance["used_open_nutrition"] = True

        # 3. Generate Frontier
        return self._sensory_frontier.generate_frontier(recipe_text, properties_list, aggregated_provenance, objectives=objectives)

    def select_sensory_variant(self, frontier: ParetoFrontierResult, prefs: UserPreferences) -> SelectionResult:
        """
        Selects the best variant from the Pareto frontier based on user preferences (Phase 9).
        """
        logger.info(f"Selecting best variant for preferences: {prefs}")
        
        if not hasattr(self, '_variant_selector') or self._variant_selector is None:
            from backend.sensory.selector import VariantSelector
            self._variant_selector = VariantSelector()
            
        return self._variant_selector.select(frontier, prefs)

    def explain_sensory(self, profile: SensoryProfile, mode: str = "scientific") -> ExplanationResult:
        """
        Adapts the sensory explanation to the specified audience mode (Phase 10).
        """
        logger.info(f"Adapting sensory explanation to mode: {mode}")
        
        if not hasattr(self, '_sensory_explainer') or self._sensory_explainer is None:
            from backend.sensory.explainer import ExplanationLayer
            self._sensory_explainer = ExplanationLayer(self.engine)
            
        return self._sensory_explainer.explain(profile, mode)

    def simulate_sensory_counterfactual(self, profile: SensoryProfile, parameter: str, delta: float, mode: str = "scientific") -> Dict[str, Any]:
        """
        Predicts sensory changes under parameter modifications (Phase 11).
        Returns both the raw report and the audience-calibrated explanation.
        """
        logger.info(f"Simulating counterfactual for {parameter} with delta {delta}")
        
        if not hasattr(self, '_cf_engine') or self._cf_engine is None:
            self._cf_engine = CounterfactualEngine()
        if not hasattr(self, '_cf_explainer') or self._cf_explainer is None:
            self._cf_explainer = CounterfactualExplainer(self.engine)
            
        report = self._cf_engine.simulate(profile, parameter, delta)
        explanation = self._cf_explainer.explain(report, mode)
        
        return {
            "report": report,
            "explanation": explanation
        }

    def get_sensory_sensitivity(self, dimension: str, top_n: int = 3) -> SensitivityRanking:
        """
        Returns the top parameters affecting a sensory dimension (Phase 11).
        """
        if not hasattr(self, '_cf_engine') or self._cf_engine is None:
            self._cf_engine = CounterfactualEngine()
            
        return self._cf_engine.get_sensitivity_ranking(dimension, top_n)

    def simulate_multi_parameter_counterfactual(self, profile: SensoryProfile, deltas: Dict[str, float], mode: str = "scientific") -> Dict[str, Any]:
        """
        Simulates the joint effect of multiple parameter changes (Phase 12).
        Returns both the raw multi-report and the calibrated explanation.
        """
        logger.info(f"Simulating multi-parameter counterfactual for {deltas}")
        
        if not hasattr(self, '_multi_cf_engine') or self._multi_cf_engine is None:
            self._multi_cf_engine = MultiCounterfactualEngine()
        if not hasattr(self, '_multi_cf_explainer') or self._multi_cf_explainer is None:
            self._multi_cf_explainer = InteractiveExplainer(self.engine)
            
        report = self._multi_cf_engine.simulate_multi(profile, deltas)
        explanation = self._multi_cf_explainer.explain_multi(report, mode)
        
        return {
            "report": report,
            "explanation": explanation
        }

    def design_sensory_iteration(self, 
                                 current_profile: SensoryProfile, 
                                 iteration_number: int,
                                 proposed_deltas: Dict[str, float],
                                 target_goals: Dict[str, str],
                                 mode: str = "scientific") -> IterationState:
        """
        Executes a design iteration for iterative recipe refinement (Phase 13).
        """
        logger.info(f"Running design iteration {iteration_number} with deltas {proposed_deltas}")
        
        if not hasattr(self, '_design_loop') or self._design_loop is None:
            if not hasattr(self, '_multi_cf_engine') or self._multi_cf_engine is None:
                self._multi_cf_engine = MultiCounterfactualEngine()
            if not hasattr(self, '_multi_cf_explainer') or self._multi_cf_explainer is None:
                self._multi_cf_explainer = InteractiveExplainer(self.engine)
            
            self._design_loop = InteractiveDesignLoop(self._multi_cf_engine, self._multi_cf_explainer)
            
        return self._design_loop.run_iteration(
            current_profile, 
            iteration_number, 
            proposed_deltas, 
            target_goals, 
            mode
        )







# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_pipeline(phase: int = 2, model_name: Optional[str] = None) -> NutriPipeline:
    """
    Factory function to create a NutriPipeline instance.
    
    Args:
        phase: 1 (synthesis only) or 2 (intent extraction + synthesis)
        model_name: Optional model override
        
    Returns:
        Configured NutriPipeline
    """
    return NutriPipeline(
        model_name=model_name,
        use_phase2=(phase == 2)
    )


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("NUTRI FOOD SYNTHESIS SYSTEM")
    print("=" * 60)
    
    # Create pipeline
    pipeline = create_pipeline(phase=2)
    
    # Test query
    test_query = "I have eggs, flour, butter, and sugar. Make something creative."
    
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    
    print(f"\nQuery: {test_query}\n")
    print("-" * 60)
    
    # Run synthesis
    result = pipeline.synthesize(test_query)
    
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    
    if result.intent:
        print("\n📋 Extracted Intent:")
        print(json.dumps(result.intent, indent=2))
    
    print(f"\n📚 Retrieved {len(result.retrieved_documents)} documents")
    for doc in result.retrieved_documents:
        print(f"  - [{doc['type']}] {doc['source']} (score: {doc['score']:.3f})")
    
    print("\n🍳 Generated Recipe:")
    print("-" * 60)
    print(result.recipe)
    print("=" * 60)
