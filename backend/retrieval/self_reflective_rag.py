"""
Self-Reflective RAG — Nutri Phase 4

Post-generation verification loop that evaluates LLM answers against
retrieved context and triggers corrective actions when needed.
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
MAX_REFLECTION_PASSES = 1
MAX_TOTAL_LATENCY = 2.0  # seconds


REFLECTION_PROMPT = """You are verifying a retrieval-augmented answer for accuracy.

Question:
{query}

Context (retrieved chunks):
{context}

Generated Answer:
{answer}

Evaluate whether the answer is fully supported by the provided context.

Rules:
- SUFFICIENT: The answer is well-supported by the context. No important gaps.
- INSUFFICIENT_CONTEXT: The answer attempts to address the question but the context is missing key information.
- HALLUCINATION_RISK: The answer contains claims not supported by the provided context.

Respond in EXACTLY this format (two lines only):
DECISION: <SUFFICIENT|INSUFFICIENT_CONTEXT|HALLUCINATION_RISK>
CONFIDENCE: <0.0 to 1.0>
"""

STRICT_REGEN_PROMPT = """You are a scientific nutrition assistant. Answer ONLY using the provided context.
Do NOT add any information not explicitly stated in the context.
If the context does not contain enough information, say so clearly.

Question:
{query}

Context:
{context}

Provide a precise, evidence-grounded answer:"""


def _parse_reflection_response(response: str) -> Tuple[str, float]:
    """
    Parse the LLM reflection response into decision and confidence.

    Returns:
        (decision, confidence) tuple.
    """
    decision = "SUFFICIENT"
    confidence = 0.5

    # Parse decision
    decision_match = re.search(
        r"DECISION:\s*(SUFFICIENT|INSUFFICIENT_CONTEXT|HALLUCINATION_RISK)",
        response,
        re.IGNORECASE,
    )
    if decision_match:
        decision = decision_match.group(1).upper()

    # Parse confidence
    confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", response, re.IGNORECASE)
    if confidence_match:
        try:
            confidence = float(confidence_match.group(1))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.5

    return decision, confidence


def evaluate_answer(
    query: str,
    answer: str,
    context_chunks: List[Dict[str, Any]],
    llm_client=None,
) -> Dict[str, Any]:
    """
    Evaluate whether the generated answer is supported by the context.

    Args:
        query: Original user query.
        answer: LLM-generated answer.
        context_chunks: List of context chunk dicts with 'text' key.
        llm_client: TogetherClient instance (or compatible).

    Returns:
        Dict with 'decision', 'confidence', 'raw_response'.
    """
    if llm_client is None:
        try:
            from backend.llm.factory import LLMFactory
            llm_client = LLMFactory.create_client(agent_name="reflection_engine")
        except Exception as e:
            logger.error(f"[REFLECTION] Failed to init local LLM client: {e}")
            return {"decision": "SUFFICIENT", "confidence": 0.0, "raw_response": ""}

    context_text = "\n---\n".join(
        c.get("text", "") for c in context_chunks if c.get("text")
    )

    prompt = REFLECTION_PROMPT.format(
        query=query, context=context_text, answer=answer
    )

    try:
        messages = [
            {"role": "system", "content": "You are an answer verification assistant."},
            {"role": "user", "content": prompt},
        ]
        raw = llm_client.generate_text(messages)
        decision, confidence = _parse_reflection_response(raw)

        logger.info(
            f"[REFLECTION] decision={decision} confidence={confidence:.2f}"
        )

        return {
            "decision": decision,
            "confidence": confidence,
            "raw_response": raw,
        }
    except Exception as e:
        logger.error(f"[REFLECTION] LLM call failed: {e}")
        return {"decision": "SUFFICIENT", "confidence": 0.0, "raw_response": ""}


def run_reflective_pipeline(
    query: str,
    initial_answer: str,
    context_chunks: List[Dict[str, Any]],
    hybrid_retriever=None,
    llm_client=None,
    pipeline_start_time: Optional[float] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full self-reflective RAG pipeline.

    Flow:
        1. Evaluate answer against context
        2. If SUFFICIENT → return as-is
        3. If INSUFFICIENT_CONTEXT → second retrieval pass (k=40, no taste boost)
        4. If HALLUCINATION_RISK → regenerate with stricter prompt
        5. MAX_REFLECTION_PASSES = 1, MAX_TOTAL_LATENCY = 2s

    Returns:
        Dict with 'answer', 'decision', 'confidence', 'reflection_pass',
        'second_retrieval', 'telemetry'.
    """
    start_time = pipeline_start_time or time.perf_counter()

    result = {
        "answer": initial_answer,
        "decision": "SUFFICIENT",
        "confidence": 1.0,
        "reflection_pass": 0,
        "second_retrieval": False,
        "telemetry": {},
    }

    # Global latency guard: check if we have time for reflection
    elapsed = time.perf_counter() - start_time
    if elapsed > MAX_TOTAL_LATENCY:
        logger.warning(
            f"[REFLECTION] Skipping — elapsed {elapsed:.2f}s > {MAX_TOTAL_LATENCY}s limit"
        )
        result["telemetry"]["reflection_skipped"] = True
        return result

    # Step 1: Evaluate
    evaluation = evaluate_answer(query, initial_answer, context_chunks, llm_client)
    decision = evaluation["decision"]
    confidence = evaluation["confidence"]

    result["decision"] = decision
    result["confidence"] = confidence
    result["reflection_pass"] = 1

    # Step 2: Act on decision
    if decision == "SUFFICIENT":
        logger.info("[REFLECTION] Answer is sufficient. Returning.")
        return result

    if decision == "INSUFFICIENT_CONTEXT" and hybrid_retriever is not None:
        # Second retrieval pass: larger pool, no taste boost, keep semantic dedup
        logger.info("[REFLECTION] Insufficient context — running second retrieval pass")

        elapsed_check = time.perf_counter() - start_time
        if elapsed_check > MAX_TOTAL_LATENCY:
            logger.warning("[REFLECTION] Latency guard — skipping second pass")
            result["telemetry"]["second_pass_skipped"] = True
            return result

        second_pass = hybrid_retriever.search(
            query=query,
            top_k=8,
            k_vector=40,
            k_bm25=40,
            tier=tier,
            enable_taste_boost=False,
            enable_semantic_dedup=True,
        )

        expanded_chunks = second_pass.get("results", [])
        result["second_retrieval"] = True
        result["telemetry"]["second_pass_chunks"] = len(expanded_chunks)

        # Regenerate answer with expanded context
        if llm_client and expanded_chunks:
            try:
                context_text = "\n---\n".join(
                    c.get("text", "") for c in expanded_chunks if c.get("text")
                )
                messages = [
                    {"role": "system", "content": "You are a scientific nutrition assistant."},
                    {"role": "user", "content": f"Question: {query}\n\nContext:\n{context_text}\n\nProvide a precise answer:"},
                ]
                result["answer"] = llm_client.generate_text(messages)
            except Exception as e:
                logger.error(f"[REFLECTION] Regeneration failed: {e}")

        return result

    if decision == "HALLUCINATION_RISK":
        # Regenerate with stricter prompt using same context
        logger.warning("[REFLECTION] Hallucination risk — regenerating with strict prompt")

        elapsed_check = time.perf_counter() - start_time
        if elapsed_check > MAX_TOTAL_LATENCY:
            logger.warning("[REFLECTION] Latency guard — skipping regeneration")
            result["telemetry"]["regen_skipped"] = True
            return result

        if llm_client and context_chunks:
            try:
                context_text = "\n---\n".join(
                    c.get("text", "") for c in context_chunks if c.get("text")
                )
                strict_prompt = STRICT_REGEN_PROMPT.format(
                    query=query, context=context_text
                )
                messages = [
                    {"role": "system", "content": "You must ONLY use the provided context. Do not hallucinate."},
                    {"role": "user", "content": strict_prompt},
                ]
                result["answer"] = llm_client.generate_text(messages)
            except Exception as e:
                logger.error(f"[REFLECTION] Strict regeneration failed: {e}")

        return result

    return result
