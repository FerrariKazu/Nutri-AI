"""
Selective Memory System with Two-Stage Extraction

Implements:
- UserPreferences (persistent, user-scoped)
- SessionContext (ephemeral, session-scoped)
- Two-stage extraction: deterministic filter → LLM normalization
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """Persistent user preferences (localStorage + DB) with confidence metadata."""
    skill_level: Optional[str] = None  # "beginner", "intermediate", "expert"
    equipment: List[str] = field(default_factory=list)  # ["air fryer", "instant pot"]
    dietary_constraints: List[str] = field(default_factory=list)  # Only if EXPLICITLY stated
    
    # CONFIDENCE METADATA (Phase 6.1)
    skill_level_confidence: float = 0.0  # 0.0 - 1.0
    equipment_confidence: Dict[str, float] = field(default_factory=dict)  # {"air fryer": 0.9}
    dietary_confidence: Dict[str, float] = field(default_factory=dict)  # {"vegan": 0.95}
    
    # DECAY TRACKING
    last_confirmed_at: Optional[str] = None  # ISO timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        # Handle missing fields gracefully for backward compatibility
        return cls(
            skill_level=data.get('skill_level'),
            equipment=data.get('equipment', []),
            dietary_constraints=data.get('dietary_constraints', []),
            skill_level_confidence=data.get('skill_level_confidence', 0.0),
            equipment_confidence=data.get('equipment_confidence', {}),
            dietary_confidence=data.get('dietary_confidence', {}),
            last_confirmed_at=data.get('last_confirmed_at')
        )
    
    def apply_decay(self, decay_days: int = 90, decay_amount: float = 0.2):
        """
        Apply confidence decay if last_confirmed_at > decay_days.
        Reduces all confidence values by decay_amount.
        """
        if not self.last_confirmed_at:
            return  # No timestamp, no decay
        
        try:
            last_confirmed = datetime.fromisoformat(self.last_confirmed_at)
            days_since_confirmed = (datetime.now() - last_confirmed).days
            
            if days_since_confirmed > decay_days:
                # Apply decay
                self.skill_level_confidence = max(0.0, self.skill_level_confidence - decay_amount)
                
                for item in self.equipment_confidence:
                    self.equipment_confidence[item] = max(0.0, self.equipment_confidence[item] - decay_amount)
                
                for item in self.dietary_confidence:
                    self.dietary_confidence[item] = max(0.0, self.dietary_confidence[item] - decay_amount)
                
                logger.info(f"[MEMORY] Applied decay: {days_since_confirmed} days since last confirmation")
        except (ValueError, TypeError) as e:
            logger.warning(f"[MEMORY] Failed to parse last_confirmed_at: {e}")
    
    def should_inject(self, confidence_threshold: float = 0.6) -> bool:
        """
        Determine if this preference should be injected into LLM prompts.
        Returns False if all confidence values are below threshold.
        """
        if self.skill_level_confidence >= confidence_threshold:
            return True
        if any(conf >= confidence_threshold for conf in self.equipment_confidence.values()):
            return True
        if any(conf >= confidence_threshold for conf in self.dietary_confidence.values()):
            return True
        return False


@dataclass
class SessionContext:
    """Ephemeral session-only context."""
    current_dish: Optional[str] = None
    key_ingredients: List[str] = field(default_factory=list)
    technique: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionContext':
        return cls(**data)


class MemoryExtractor:
    """Two-stage preference extraction: Rule filter → LLM normalization."""
    
    # STAGE 1: Deterministic keyword triggers
    SKILL_TRIGGERS = [
        "i'm a beginner", "new to cooking", "never cooked", "first time", 
        "i'm experienced", "professional chef", "i'm an expert", "novice",
        "just starting", "beginner here"
    ]
    EQUIPMENT_TRIGGERS = [
        "i only have", "i don't have", "my only", "just have", "using a", 
        "got a", "all i have", "no access to"
    ]
    DIETARY_TRIGGERS = [
        "i'm vegan", "i don't eat", "allergic to", "can't have", 
        "vegetarian", "gluten-free", "dairy-free", "nut allergy",
        "lactose intolerant", "celiac"
    ]
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def extract_preferences(self, message: str, current_prefs: UserPreferences) -> Optional[Dict[str, Any]]:
        """
        Two-stage extraction:
        1. Deterministic filter (no LLM if no trigger)
        2. LLM normalization (only after trigger matched)
        
        Examples:
        - "I'm a beginner" → {"skill_level": "beginner"}
        - "I only have an air fryer" → {"equipment": ["air fryer"]}
        - "I'm vegan" → {"dietary_constraints": ["vegan"]}
        - "What's a good recipe?" → None  # No LLM call
        """
        msg_lower = message.lower()
        
        # STAGE 1: Check for explicit triggers
        has_skill_signal = any(trigger in msg_lower for trigger in self.SKILL_TRIGGERS)
        has_equipment_signal = any(trigger in msg_lower for trigger in self.EQUIPMENT_TRIGGERS)
        has_dietary_signal = any(trigger in msg_lower for trigger in self.DIETARY_TRIGGERS)
        
        # Early exit: No triggers = no extraction
        if not (has_skill_signal or has_equipment_signal or has_dietary_signal):
            return None
        
        logger.info(f"[MEMORY] Triggers detected - skill:{has_skill_signal}, equipment:{has_equipment_signal}, dietary:{has_dietary_signal}")
        
        # STAGE 2: LLM normalization (only after trigger)
        extraction_prompt = f"""Extract user preferences from this message. Return ONLY a JSON object with these fields (omit if not mentioned):
- skill_level: "beginner" | "intermediate" | "expert"
- equipment: list of equipment names
- dietary_constraints: list of dietary restrictions

Message: "{message}"

Return only valid JSON, no explanation."""

        try:
            response = self.llm.generate(extraction_prompt, max_tokens=150, temperature=0.1)
            
            # Parse JSON response
            extracted = json.loads(response.strip())
            
            # Validate and return WITH CONFIDENCE METADATA
            updates = {}
            now = datetime.now().isoformat()
            
            if has_skill_signal and "skill_level" in extracted:
                updates["skill_level"] = extracted["skill_level"]
                # Deterministic trigger → high confidence (0.9)
                updates["skill_level_confidence"] = 0.9
            if has_equipment_signal and "equipment" in extracted:
                equipment_list = extracted["equipment"]
                updates["equipment"] = equipment_list
                # Assign confidence per item (deterministic trigger → 0.9)
                updates["equipment_confidence"] = {item: 0.9 for item in equipment_list}
            if has_dietary_signal and "dietary_constraints" in extracted:
                dietary_list = extracted["dietary_constraints"]
                updates["dietary_constraints"] = dietary_list
                # Dietary constraints are safety-critical → higher confidence (0.95)
                updates["dietary_confidence"] = {item: 0.95 for item in dietary_list}
            
            # Add confirmation timestamp
            if updates:
                updates["last_confirmed_at"] = now
            
            logger.info(f"[MEMORY] Extracted preferences with confidence: {updates}")
            return updates if updates else None
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[MEMORY] Extraction failed: {e}")
            return None
    
    def extract_context(self, message: str, response: str) -> Optional[SessionContext]:
        """
        Extracts ephemeral context from current exchange.
        Summarized, not verbatim.
        
        Returns None if extraction yields empty context.
        """
        # Simple heuristic-based extraction (can be enhanced with LLM)
        msg_lower = message.lower()
        
        context = SessionContext()
        
        # Extract dish name from common patterns
        dish_patterns = ["making ", "cook ", "prepare ", "recipe for "]
        for pattern in dish_patterns:
            if pattern in msg_lower:
                idx = msg_lower.index(pattern)
                potential_dish = message[idx + len(pattern):].split()[0:3]  # Next 3 words
                context.current_dish = " ".join(potential_dish).rstrip(".,?!")
                break
        
        # Extract technique mentions
        techniques = ["frying", "baking", "roasting", "grilling", "steaming", "boiling", "sautéing"]
        for tech in techniques:
            if tech in msg_lower:
                context.technique = tech
                break
        
        # Return None if context is empty
        if not context.current_dish and not context.technique:
            return None
        
        return context
