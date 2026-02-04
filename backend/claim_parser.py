import re
import uuid
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Literal, Dict, Any, Optional

logger = logging.getLogger(__name__)

ClaimType = Literal["quantitative", "mechanistic", "qualitative"]

@dataclass
class Claim:
    claim_id: str
    text: str
    type: ClaimType
    subject: Optional[str] = None
    predicate: Optional[str] = None
    metadata: dict = field(default_factory=dict)

class ClaimParser:
    """
    LLM-assisted claim extraction pipeline.
    Ensures high-fidelity extraction of atomic, verifiable propositions.
    """
    
    def __init__(self, llm_engine=None):
        self.llm = llm_engine
        self.quantitative_patterns = [
            r"\b(high|low|rich|source|contains|mg|g|mcg|%|percent|daily value)\b",
            r"\d+",
        ]
        self.mechanistic_patterns = [
            r"\b(supports|aids|helps|promotes|prevents|inhibits|regulates|modulates|boosts)\b",
            r"\b(digestion|metabolism|immune|absorption|synthesis)\b",
        ]

    def parse(self, text: str) -> List[Claim]:
        """
        Parses full text into a list of atomic Claims.
        Uses LLM if available, falls back to deterministic split.
        """
        claims = []
        
        if self.llm:
            try:
                claims = self._llm_assisted_parse(text)
                if claims:
                    return claims
            except Exception as e:
                logger.error(f"[CLAIM_PARSER] LLM parse failed: {e}. Falling back to deterministic split.")

        # Fallback to sentence-level extraction
        sentences = self._split_sentences(text)
        for sentence in sentences:
            atoms = self._atomic_split(sentence)
            for atom in atoms:
                clean_atom = atom.strip().strip(".")
                if not clean_atom:
                    continue
                
                claims.append(self._create_claim(clean_atom))
        
        return claims

    def _llm_assisted_parse(self, text: str) -> List[Claim]:
        """
        Constrained LLM pass to extract claims into JSON.
        """
        prompt = f"""
Extract all atomic nutrition and chemical claims from the following text.
One claim must be one verifiable proposition. Split conjunctions.
Format as JSON list: [{{"text": "...", "subject": "...", "predicate": "...", "type": "quantitative|mechanistic|qualitative"}}]

RULES:
1. No silent inference.
2. Atomic propositions only.
3. Classify type:
   - quantitative: nutrient amounts, "high in", "contains X mg"
   - mechanistic: "supports digestion", "boosts immune system"
   - qualitative: "delicious", "traditional", "healthy" (if vague)

TEXT:
{text}
"""
        response = self.llm.generate_text(
            messages=[{"role": "user", "content": prompt}],
            max_new_tokens=1024,
            temperature=0.0
        )
        
        try:
            # Simple JSON extraction from response
            json_str = re.search(r"\[.*\]", response, re.DOTALL).group()
            data = json.loads(json_str)
            
            extracted = []
            for item in data:
                # Validation: Reject claims with missing predicate or subject if possible
                if not item.get("text") or not item.get("subject") or not item.get("predicate"):
                    logger.warning(f"[CLAIM_PARSER] Rejecting malformed claim: {item}")
                    continue
                    
                extracted.append(self._create_claim(
                    item["text"], 
                    claim_type=item.get("type", "qualitative"),
                    subject=item.get("subject"),
                    predicate=item.get("predicate")
                ))
            return extracted
        except Exception as e:
            logger.error(f"[CLAIM_PARSER] JSON parse error: {e}")
            return []

    def _create_claim(self, text: str, claim_type: Optional[ClaimType] = None, subject: Optional[str] = None, predicate: Optional[str] = None) -> Claim:
        # Stable ID generation via sha256
        normalized_text = text.lower().strip()
        claim_id = f"C-{hashlib.sha256(normalized_text.encode()).hexdigest()[:8]}"
        
        return Claim(
            claim_id=claim_id,
            text=text,
            type=claim_type or self._classify_type(text),
            subject=subject,
            predicate=predicate
        )

    def _split_sentences(self, text: str) -> List[str]:
        return re.split(r"(?<=[.!?])\s+", text)

    def _atomic_split(self, sentence: str) -> List[str]:
        splitters = [r"\s+and\s+", r"\s+while\s+", r"\s+as\s+well\s+as\s+"]
        pattern = "|".join(splitters)
        parts = re.split(pattern, sentence, flags=re.IGNORECASE)
        return parts

    def _classify_type(self, text: str) -> ClaimType:
        text_lower = text.lower()
        if any(re.search(p, text_lower) for p in self.quantitative_patterns):
            return "quantitative"
        if any(re.search(p, text_lower) for p in self.mechanistic_patterns):
            return "mechanistic"
        return "qualitative"
