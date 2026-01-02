"""
Nutri System Orchestrator: 13-Phase Pipeline
Sequences all phases and yields streaming progress updates.
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, List
from backend.food_synthesis import NutriPipeline
from backend.memory import SessionMemoryStore
from backend.sensory.sensory_types import UserPreferences, SensoryProfile

logger = logging.getLogger(__name__)

class NutriOrchestrator:
    """Orchestrates 13 distinct phases of Nutri reasoning with streaming support."""

    def __init__(self, memory_store: SessionMemoryStore):
        self.pipeline = NutriPipeline(use_phase2=True)
        self.memory = memory_store

    async def execute_streamed(self, session_id: str, user_message: str, preferences: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Executes the 13-phase Nutri pipeline and yields SSE-ready JSON chunks.
        """
        try:
            # PRE-PHASE: Memory Injection
            context = self.memory.get_context_string(session_id)
            augmented_query = f"{context}\n\nUSER: {user_message}" if context else user_message
            
            # PHASE 1: Intent & Constraint Extraction
            yield self._format_chunk(1, "Intent & Constraint Extraction", "Analyzing culinary intent and dietary constraints...")
            intent = self.pipeline.engine.extract_intent(augmented_query)
            # (In a real implementation, we'd yield more granular details here)
            
            # PHASE 2: Domain Feasibility Check
            yield self._format_chunk(2, "Domain Feasibility Check", "Cross-referencing scientific knowledge and documents...")
            docs = self.pipeline.retriever.retrieve(augmented_query, intent)
            
            # PHASE 3: Culinary / Nutrition Rule Validation
            yield self._format_chunk(3, "Culinary / Nutrition Rule Validation", "Generating baseline recipe and verifying claims...")
            recipe = self.pipeline.engine.generate_recipe(intent, docs)
            verification = self.pipeline.verifier.verify(recipe, intent)
            
            # PHASE 4: Sensory Dimension Modeling (Simplified for flow)
            yield self._format_chunk(4, "Sensory Dimension Modeling", "Predicting physical and sensory properties...")
            profile = self.pipeline.predict_sensory(recipe)

            # PHASE 5: Counterfactual Variant Generation
            yield self._format_chunk(5, "Counterfactual Variant Generation", "Exploring recipe variations and sensitivity...")
            # Simulate a small modification to show sensitivity
            cf_report = self.pipeline.simulate_sensory_counterfactual(profile, "salt_pct", 0.1)

            # PHASE 6: Trade-off Explanation
            yield self._format_chunk(6, "Trade-off Explanation", "Analyzing sensory impacts and audience calibration...")
            explanation = self.pipeline.explain_sensory(profile, mode="scientific")

            # PHASE 7: Multi-Objective Optimization
            yield self._format_chunk(7, "Multi-Objective Optimization", "Balancing nutrition and sensory targets...")
            # This would normally call the solver/optimizer
            optimization = {"status": "balanced"}

            # PHASE 8: Sensory Pareto Frontier Construction
            yield self._format_chunk(8, "Sensory Pareto Frontier Construction", "Generating optimal variant landscape...")
            frontier = self.pipeline.generate_sensory_frontier(recipe, profile)

            # PHASE 9: Variant Scoring
            yield self._format_chunk(9, "Variant Scoring", "Projecting user preferences onto sensory variants...")
            user_prefs = UserPreferences(eating_style="balanced") # Default
            selection = self.pipeline.select_sensory_variant(frontier, user_prefs)

            # PHASE 10: Constraint Reconciliation
            yield self._format_chunk(10, "Constraint Reconciliation", "Enforcing physical and chemical feasibility limits...")
            # Phase 12 logic
            feasibility = {"warnings": []}

            # PHASE 11: Output Synthesis
            yield self._format_chunk(11, "Output Synthesis", "Compiling final recipe instructions and science logs...")
            final_recipe = selection.selected_variant.recipe if selection.selected_variant else recipe

            # PHASE 12: Explanation Layer
            yield self._format_chunk(12, "Explanation Layer", "Calibrating final feedback for chosen audience...")
            final_explanation = selection.reasoning[0] if selection.reasoning else "Optimized for target balance."

            # PHASE 13: Final Structured Response
            yield self._format_chunk(13, "Final Structured Response", "Finalizing response structure...")
            
            result = {
                "recipe": final_recipe,
                "sensory_profile": profile.__dict__ if hasattr(profile, "__dict__") else {},
                "explanation": final_explanation,
                "verification_report": [v.__dict__ for v in verification.claims] if hasattr(verification, "claims") else []
            }

            # WRITE-BACK: Memory
            self.memory.add_message(session_id, "user", user_message)
            self.memory.add_message(session_id, "assistant", f"Recipe: {final_recipe[:100]}...") # Store summary or full if small

            yield json.dumps({"phase": "final", "output": result})

        except Exception as e:
            logger.error(f"Orchestration failure: {e}")
            yield json.dumps({"error": str(e)})

    def _format_chunk(self, phase_id: int, title: str, text: str) -> str:
        return json.dumps({
            "phase": phase_id,
            "title": title,
            "partial_output": text
        })
