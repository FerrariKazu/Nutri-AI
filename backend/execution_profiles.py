"""
Nutri Execution Profiles - Tiered Reasoning System
Defines execution modes and intent-based routing for progressive streaming.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionProfile(Enum):
    """Execution modes for tiered reasoning"""
    FAST = "fast"           # Default: Intent + Synthesis (2 LLM calls, <10s)
    SENSORY = "sensory"     # +Sensory modeling (4-5 calls, <30s)
    OPTIMIZE = "optimize"   # +Frontier optimization (10-12 calls, 2-5min)
    RESEARCH = "research"   # All 13 phases (current behavior, 10-15min)


class ExecutionRouter:
    """Intent-based routing to determine execution profile"""
    
    # Keywords that trigger specific profiles
    OPTIMIZE_KEYWORDS = [
        "best", "optimize", "compare", "variants", "better",
        "improve", "perfect", "ideal", "alternatives"
    ]
    
    SENSORY_KEYWORDS = [
        "texture", "taste", "smooth", "crisp", "tender", "chewy",
        "mouthfeel", "crunchy", "soft", "juicy", "rich", "coating",
        "sensory", "feel", "crispness", "tenderness",
        "bitter", "bitterness", "sweet", "sweetness", "sour", "sourness",
        "salty", "saltiness", "umami", "aromatic", "fragrant"
    ]
    
    @staticmethod
    def determine_profile(
        user_message: str, 
        explicit_mode: Optional[str] = None
    ) -> ExecutionProfile:
        """
        Determine execution profile from user intent.
        
        Args:
            user_message: User's natural language request
            explicit_mode: Optional explicit override ("fast", "sensory", "optimize", "research")
            
        Returns:
            ExecutionProfile enum
        """
        # 1. Explicit override takes precedence
        if explicit_mode:
            try:
                profile = ExecutionProfile(explicit_mode.lower())
                logger.info(f"Explicit execution mode: {profile.value}")
                return profile
            except ValueError:
                logger.warning(f"Invalid execution_mode '{explicit_mode}', falling back to auto-detect")
        
        # 2. Intent-based detection
        msg_lower = user_message.lower()
        
        # OPTIMIZE: User wants comparison or optimization
        if any(keyword in msg_lower for keyword in ExecutionRouter.OPTIMIZE_KEYWORDS):
            logger.info("Auto-detected OPTIMIZE profile (optimization keywords found)")
            return ExecutionProfile.OPTIMIZE
        
        # SENSORY: User asks about texture, taste, or mouthfeel
        if any(keyword in msg_lower for keyword in ExecutionRouter.SENSORY_KEYWORDS):
            logger.info("Auto-detected SENSORY profile (sensory keywords found)")
            return ExecutionProfile.SENSORY
        
        # 3. Default to FAST for immediate response
        logger.info("Defaulting to FAST profile (no specific keywords detected)")
        return ExecutionProfile.FAST
    
    @staticmethod
    def validate_profile(profile: ExecutionProfile) -> ExecutionProfile:
        """
        Validate and potentially downgrade profile based on system state.
        (Actual memory-based downgrade happens in MemoryGuard)
        
        Args:
            profile: Requested execution profile
            
        Returns:
            Validated (possibly downgraded) profile
        """
        # For now, just return as-is
        # MemoryGuard will handle actual safety checks
        return profile
