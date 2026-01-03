"""
Nutri Execution Plans - Phase Scheduling and Dependency Management
Defines which phases run immediately vs deferred for each execution profile.
"""

import logging
from dataclasses import dataclass
from typing import List
from backend.execution_profiles import ExecutionProfile

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """Phase execution plan for a given profile"""
    profile: ExecutionProfile
    immediate_phases: List[int]     # Block initial response until complete
    deferred_phases: List[int]      # Run after initial response, stream updates
    background_phases: List[int]    # Optional, lowest priority
    
    @classmethod
    def from_profile(cls, profile: ExecutionProfile) -> "ExecutionPlan":
        """
        Create execution plan from profile.
        
        Phase IDs:
            1: Intent Extraction
            2: Knowledge Retrieval (RAG)
            3: Synthesis
            4: Sensory Modeling
            5: Verification
            6: Explanation Control
            7: Sensory Optimization
            8: Pareto Frontier Generation
            9: Variant Selection
            10-13: Advanced phases (counterfactuals, etc.)
        
        Args:
            profile: Execution profile enum
            
        Returns:
            ExecutionPlan with phase assignments
        """
        if profile == ExecutionProfile.FAST:
            # Fastest path: Intent + Synthesis only
            plan = cls(
                profile=profile,
                immediate_phases=[1, 2, 3],  # Intent, RAG, Synthesis
                deferred_phases=[],
                background_phases=[]  # Explanation optional
            )
            logger.info(f"FAST profile: {len(plan.immediate_phases)} immediate phases")
            
        elif profile == ExecutionProfile.SENSORY:
            # Add sensory modeling
            plan = cls(
                profile=profile,
                immediate_phases=[1, 2, 3, 4, 6],  # +Sensory, +Explanation
                deferred_phases=[],
                background_phases=[]
            )
            logger.info(f"SENSORY profile: {len(plan.immediate_phases)} immediate phases")
            
        elif profile == ExecutionProfile.OPTIMIZE:
            # Full optimization pipeline, but deferred
            plan = cls(
                profile=profile,
                immediate_phases=[1, 2, 3],  # Quick initial response
                deferred_phases=[4, 6, 8, 9],  # Sensory + Frontier + Selection, streamed
                background_phases=[]
            )
            logger.info(
                f"OPTIMIZE profile: {len(plan.immediate_phases)} immediate, "
                f"{len(plan.deferred_phases)} deferred phases"
            )
            
        elif profile == ExecutionProfile.RESEARCH:
            # All phases, current behavior
            plan = cls(
                profile=profile,
                immediate_phases=[1, 2, 3, 4, 5, 6, 8, 9],  # All phases synchronously
                deferred_phases=[],
                background_phases=[]
            )
            logger.info(f"RESEARCH profile: {len(plan.immediate_phases)} immediate phases (full pipeline)")
            
        else:
            # Fallback to FAST
            logger.warning(f"Unknown profile {profile}, falling back to FAST")
            return cls.from_profile(ExecutionProfile.FAST)
        
        return plan
    
    def get_total_phases(self) -> int:
        """Total number of phases to execute"""
        return len(self.immediate_phases) + len(self.deferred_phases) + len(self.background_phases)
    
    def is_fast_mode(self) -> bool:
        """Check if this is a fast execution (no deferred phases)"""
        return len(self.deferred_phases) == 0 and len(self.background_phases) == 0
