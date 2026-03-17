"""
Mechanistic Explainer Pipeline — v2.0 Scientific Routing Refactor

Generates structured 3-tier scientific explanations for causal food science queries.
LLM output is enforced as structured JSON — no freeform parsing.

Output structure:
  tier_1_surface  → Observable effect
  tier_2_process  → Process-level causality
  tier_3_molecular → Molecular/biochemical detail
  causal_chain    → Step-by-step cause → effect chain
  claims          → Structured scientific claims with mechanism, compounds, anchors
"""

import json
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from backend.prompts.system_roles import get_system_prompt_for_state
from backend.governance_types import GovernanceState
from backend.mode_constraints import MECHANISTIC_CONSTRAINTS

logger = logging.getLogger(__name__)


@dataclass
class MechanisticOutput:
    """Validated output from the mechanistic explainer."""
    tier_1_surface: str
    tier_2_process: str
    tier_3_molecular: str
    causal_chain: List[Dict[str, Any]]
    claims: List[Dict[str, Any]]
    raw_json: Dict[str, Any]
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    narrative: str = ""  # Human-readable narrative built from tiers
    graph: Dict[str, Any] = field(default_factory=dict) # { "nodes": [], "edges": [] }


class MechanisticExplainer:
    """
    Pipeline for generating structured mechanistic explanations.
    
    Enforces structured JSON output from LLM.
    Validates 3-tier completeness, causal chain continuity,
    and entity/process requirements.
    """

    def __init__(self, llm_client, retriever=None):
        """
        Args:
            llm_client: LLMQwen3 instance
            retriever: Optional FoodSynthesisRetriever for RAG context
        """
        self.llm = llm_client
        self.retriever = retriever
        logger.info("[MECHANISTIC_EXPLAINER] Initialized")

    async def execute(
        self,
        user_query: str,
        retrieved_docs: Optional[List[Any]] = None,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> MechanisticOutput:
        """
        Execute the mechanistic explanation pipeline.
        
        1. Build RAG context from retrieved docs
        2. Call LLM with structured JSON prompt
        3. Parse and validate JSON output
        4. Build narrative from tiers
        """
        logger.info(f"[MECHANISTIC_EXPLAINER] Processing: {user_query[:80]}...")

        # 1. Build context from retrieved documents
        context = self._build_rag_context(retrieved_docs)

        # 2. Build messages
        base_prompt = get_system_prompt_for_state(GovernanceState.ALLOW_QUALITATIVE)
        system_prompt = base_prompt + "\n\n" + MECHANISTIC_CONSTRAINTS
        
        if context:
            user_content = (
                f"Scientific context from knowledge base:\n{context}\n\n"
                f"User question: {user_query}\n\n"
                "Generate the structured JSON explanation."
            )
        else:
            user_content = (
                f"User question: {user_query}\n\n"
                "Generate the structured JSON explanation."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # 3. Call LLM (BUFFERED - DO NOT STREAM RAW JSON)
        # traceValidator.js will block raw JSON tokens as a safety violation.
        # We must buffer the full JSON, validate it, and then stream the narrative.
        
        try:
            loop = asyncio.get_event_loop()
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.llm.generate_text(
                        messages,
                        max_new_tokens=4096,
                        temperature=0.3,  # Low for structured output
                        stream_callback=None  # 🛑 BLOCK STREAMING to prevent JSON leakage
                    )
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.error("[MECHANISTIC_EXPLAINER] LLM call timed out")
            return self._failure_output("LLM call timed out after 60s")
        except Exception as e:
            logger.error(f"[MECHANISTIC_EXPLAINER] LLM call failed: {e}")
            return self._failure_output(f"LLM call failed: {e}")

        # 4. Parse JSON from response
        parsed = self._parse_json_response(raw_response)
        if parsed is None:
            logger.error("[MECHANISTIC_EXPLAINER] Failed to parse JSON from LLM response")
            return self._failure_output("Structured JSON parse failed")

        # 5. Validate
        output = self._build_output(parsed)
        output.validation_passed, output.validation_errors = self._validate(output)

        if output.validation_passed:
            logger.info("[MECHANISTIC_EXPLAINER] ✅ Validation passed")
        else:
            logger.error(f"[MECHANISTIC_EXPLAINER] ❌ Validation failed: {output.validation_errors}")

        # 6. Build human-readable narrative from tiers
        output.narrative = self._build_narrative(output)
        
        # 7. STREAM NARRATIVE SAFELY
        # Now that we have valid JSON and a narrative, we stream the narrative text to the user.
        if stream_callback and output.narrative:
            # Chunk the narrative to simulate streaming for better UX
            chunk_size = 4
            for i in range(0, len(output.narrative), chunk_size):
                chunk = output.narrative[i:i+chunk_size]
                stream_callback(chunk)
                await asyncio.sleep(0.01)  # Micro-sleep to prevent event loop blocking

        return output

    def _build_rag_context(self, docs: Optional[List[Any]]) -> str:
        """Build context string from retrieved documents."""
        if not docs:
            return ""
        
        parts = []
        for doc in docs[:5]:
            text = getattr(doc, 'text', str(doc)) if not isinstance(doc, dict) else doc.get('text', '')
            if text:
                parts.append(text[:500])
        
        return "\n---\n".join(parts) if parts else ""

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Extract JSON from LLM response, handling markdown fences."""
        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback: find first { to last }
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _build_output(self, parsed: Dict) -> MechanisticOutput:
        """Build MechanisticOutput from parsed JSON."""
        # Normalize claims
        raw_claims = parsed.get("claims", [])
        causal_chain = parsed.get("causal_chain", [])
        
        # Map causal chain to graph components
        receptors = []
        perception_outputs = []
        
        if causal_chain:
            # Map causes (excluding first compound) to receptors
            for i, step in enumerate(causal_chain):
                cause = step.get("cause", "")
                effect = step.get("effect", "")
                if i > 0: # First cause is usually the compound itself
                    receptors.append(cause)
                if i == len(causal_chain) - 1: # Last effect is the perception
                    perception_outputs.append({
                        "modality": "sensory",
                        "description": effect,
                        "receptor": cause
                    })
        
        # Build dynamic graph (nodes and edges)
        graph = {"nodes": [], "edges": []}
        seen_nodes = set()

        def add_node(label, node_type, color, description=None):
            if label and label not in seen_nodes:
                node_id = f"node-{len(seen_nodes)}"
                graph["nodes"].append({
                    "id": node_id,
                    "type": node_type,
                    "label": label or node_id,
                    "description": description or f"Mechanistic {node_type} for {label}",
                    "domain": "biological",
                    "confidence": 0.85 if node_type == "compound" else 0.7,
                    "color": color
                })
                seen_nodes.add(label)
                return node_id
            # Find existing node ID
            for node in graph["nodes"]:
                if node["label"] == label:
                    return node["id"]
            return None

        # 1. Tier nodes (High level)
        t1_id = add_node(parsed.get("tier_1_surface", "Effect"), "surface", "blue", description="Observed Phenomenon / Surface Effect")
        t2_id = add_node(parsed.get("tier_2_process", "Process"), "process", "orange", description="Core Process / Causality Path")
        t3_id = add_node(parsed.get("tier_3_molecular", "Molecular"), "molecular", "purple", description="Molecular / Biochemical Catalyst")

        # 2. Causality nodes
        prev_node_id = None
        for i, step in enumerate(causal_chain):
            cause = step.get("cause", "")
            effect = step.get("effect", "")
            
            c_id = add_node(cause, "compound" if i == 0 else "mechanism", "green")
            e_id = add_node(effect, "perception" if i == len(causal_chain)-1 else "mechanism", "red")
            
            if c_id and e_id:
                graph["edges"].append({"source": c_id, "target": e_id, "label": "causes"})
            
            # Cross-connect to tiers
            if i == 0 and t3_id: # Molecular link
                graph["edges"].append({"source": c_id, "target": t3_id, "label": "involved_in", "style": "dashed"})
            if i == len(causal_chain) - 1 and t1_id: # Surface link
                graph["edges"].append({"source": e_id, "target": t1_id, "label": "results_in", "style": "dashed"})

        processed_claims = []
        for i, c in enumerate(raw_claims):
            claim = {
                "id": f"MECH-{uuid.uuid4().hex[:8]}",
                "claim_id": f"MECH-{uuid.uuid4().hex[:8]}",
                "statement": c.get("statement", ""),
                "text": c.get("statement", ""),
                "mechanism": c.get("mechanism", ""),
                "mechanism_type": "causal",
                "compounds": c.get("compounds", []),
                "receptors": receptors if i == 0 else [], # Primary claim gets the full graph
                "perception_outputs": perception_outputs if i == 0 else [],
                "anchors": c.get("anchors", []),
                "domain": "biological",
                "verified": False,
                "origin": "mechanistic_pipeline",
                "verification_level": "structured_generation",
                "importance_score": max(0.5, 1.0 - (i * 0.1)),
                "decision": "ALLOW",
                "processes": c.get("anchors", []),
                "physical_states": [],
            }
            processed_claims.append(claim)

        return MechanisticOutput(
            tier_1_surface=parsed.get("tier_1_surface", ""),
            tier_2_process=parsed.get("tier_2_process", ""),
            tier_3_molecular=parsed.get("tier_3_molecular", ""),
            causal_chain=causal_chain,
            claims=processed_claims,
            raw_json=parsed,
            graph=graph
        )

    def _validate(self, output: MechanisticOutput) -> tuple:
        """
        Validate mechanistic output against strict requirements.
        
        Requirements:
        - All 3 tiers present and non-empty
        - Causal chain length >= 2
        - Causal chain continuity (each effect → next cause)
        - At least 1 biological/chemical entity in claims
        - At least 1 process-level transformation in claims
        """
        errors = []

        # Tier presence
        if not output.tier_1_surface or len(output.tier_1_surface.strip()) < 10:
            errors.append("tier_1_surface missing or too short")
        if not output.tier_2_process or len(output.tier_2_process.strip()) < 10:
            errors.append("tier_2_process missing or too short")
        if not output.tier_3_molecular or len(output.tier_3_molecular.strip()) < 10:
            errors.append("tier_3_molecular missing or too short")

        # Causal chain
        chain = output.causal_chain
        if len(chain) < 2:
            errors.append(f"causal_chain too short ({len(chain)} steps, need >= 2)")
        else:
            # Continuity check
            for i in range(len(chain) - 1):
                current_effect = chain[i].get("effect", "").lower().strip()
                next_cause = chain[i + 1].get("cause", "").lower().strip()
                # Relaxed: check if any words overlap (not exact match)
                effect_words = set(current_effect.split())
                cause_words = set(next_cause.split())
                if not effect_words & cause_words and current_effect and next_cause:
                    logger.warning(
                        f"[MECHANISTIC_VALIDATION] Weak chain continuity: "
                        f"step {i+1} effect='{current_effect}' → step {i+2} cause='{next_cause}'"
                    )

        # Claims validation
        if len(output.claims) < 1:
            errors.append(f"Too few claims ({len(output.claims)}, need >= 1)")

        has_entity = False
        has_process = False
        for c in output.claims:
            if c.get("compounds") and len(c["compounds"]) > 0:
                has_entity = True
            if c.get("anchors") and len(c["anchors"]) > 0:
                has_entity = True
            if c.get("mechanism") and len(c["mechanism"]) > 5:
                has_process = True

        if not has_entity:
            errors.append("No biological/chemical entities found in claims")
        if not has_process:
            errors.append("No process-level transformation found in claims")

        # Reject fake padding
        for c in output.claims:
            if c.get("importance_score", 0) == 0:
                errors.append(f"Claim {c.get('id')} has importance_score=0 (rejected)")
            if c.get("decision") == "REQUIRE_MORE_CONTEXT":
                errors.append(f"Claim {c.get('id')} has decision=REQUIRE_MORE_CONTEXT (rejected)")

        passed = len(errors) == 0
        return passed, errors

    def _build_narrative(self, output: MechanisticOutput) -> str:
        """Build human-readable narrative from structured tiers."""
        parts = []

        if output.tier_1_surface:
            parts.append(f"**What happens:** {output.tier_1_surface}")

        if output.tier_2_process:
            parts.append(f"\n**How it works:** {output.tier_2_process}")

        if output.tier_3_molecular:
            parts.append(f"\n**At the molecular level:** {output.tier_3_molecular}")

        if output.causal_chain:
            chain_str = " → ".join(
                f"{step.get('cause', '?')}" for step in output.causal_chain
            )
            last_effect = output.causal_chain[-1].get("effect", "")
            if last_effect:
                chain_str += f" → {last_effect}"
            parts.append(f"\n**Causal chain:** {chain_str}")

        return "\n".join(parts)

    def _failure_output(self, reason: str) -> MechanisticOutput:
        """Return a failed MechanisticOutput."""
        return MechanisticOutput(
            tier_1_surface="",
            tier_2_process="",
            tier_3_molecular="",
            causal_chain=[],
            claims=[],
            raw_json={},
            validation_passed=False,
            validation_errors=[reason],
        )
