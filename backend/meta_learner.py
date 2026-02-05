"""
Nutri Meta-Learner (Policy Layer)

A deterministic, sub-1ms decision engine that sets execution strategy
BEFORE any heavy lifting begins. It balances user intent with system constraints.
"""

import logging
import psutil
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
from backend.execution_profiles import ExecutionProfile, ExecutionRouter
from backend.gpu_monitor import gpu_monitor

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPolicy:
    """Decision output from the Meta-Learner"""
    profile: ExecutionProfile
    enabled_agents: Set[str]
    speculative_agents: Set[str]
    latency_budget: Dict[str, float]
    downgraded_reason: Optional[str] = None

class MetaLearner:
    """
    Policy engine that decides HOW to execute a request.
    Does NOT use LLMs. Uses heuristics, system metrics, and history.
    """
    
    # Constants for policy thresholds
    SWAP_LIMIT_MB = 1500  # Force FAST if swap usage > 1.5GB
    SHORT_QUERY_LENGTH = 15  # Words
    
    # Agents available in the system (for enabling/disabling)
    AGENTS_CORE = {"intent", "recipe", "presentation"}
    AGENTS_SENSORY = {"sensory_model", "explanation"}
    AGENTS_OPTIMIZE = {"frontier", "selector"}
    AGENTS_SPECULATIVE = {"recipe_renderer"}
    
    def __init__(self):
        logger.info("MetaLearner initialized")

    def decide_policy(
        self, 
        user_message: str, 
        explicit_mode: Optional[str] = None,
        history_stats: Optional[Dict[str, Any]] = None
    ) -> ExecutionPolicy:
        """
        Decide the execution policy for a request.
        
        Args:
            user_message: The user's input text
            explicit_mode: Optional override ("fast", "sensory", "optimize")
            history_stats: Optional stats about previous execution (not used in v1)
            
        Returns:
            ExecutionPolicy object
        """
        # 1. Check System Health & GPU Degraded Mode
        system_health = self._check_system_health()
        
        # 2. Determine Base Profile
        if gpu_monitor.degraded_mode:
            profile = ExecutionProfile.FAST
            downgrade_reason = "[GPU_DEGRADED_MODE] VRAM leak protection active."
            logger.warning(f"Policy forced FAST: {downgrade_reason}")
        elif system_health["status"] == "critical":
            # Force downgrade under pressure
            profile = ExecutionProfile.FAST
            downgrade_reason = f"System load critical: {system_health['reason']}"
            logger.warning(f"Policy enforced downgrade: {downgrade_reason}")
        else:
            # Use standard routing logic
            # If message is very short and generic, default to FAST to avoid over-engineering
            word_count = len(user_message.split())

            
            base_profile = ExecutionRouter.determine_profile(user_message, explicit_mode)
            
            if (not explicit_mode and 
                word_count < self.SHORT_QUERY_LENGTH and 
                base_profile == ExecutionProfile.FAST):
                # Double confirm it's FAST for short queries
                profile = ExecutionProfile.FAST
                downgrade_reason = None
            else:
                profile = base_profile
                downgrade_reason = None

        # 3. Enable Agents based on Profile
        enabled_agents = self._get_agents_for_profile(profile)
        
        # 4. Check for Luxury Constraints
        # If load is high but not critical, disable luxury agents but keep profile structure?
        # For v1, we strictly follow profile map, but could prune here.
        
        # 5. Select Speculative Agents
        # Always try to speculatively render a recipe if we are in a goal-oriented mode
        # Pruned in DEGRADED mode
        speculative_agents = set()
        if not gpu_monitor.degraded_mode and profile in [ExecutionProfile.FAST, ExecutionProfile.SENSORY]:
            speculative_agents.add("recipe_renderer")

            
        # 6. Set Latency Budget
        # Targets for specific milestones
        latency_budget = self._calculate_budget(profile)
        
        policy = ExecutionPolicy(
            profile=profile,
            enabled_agents=enabled_agents,
            speculative_agents=speculative_agents,
            latency_budget=latency_budget,
            downgraded_reason=downgrade_reason
        )
        
        logger.info(f"Policy Decision: {profile.value} | Agents: {len(enabled_agents)} | Spec: {len(speculative_agents)}")
        return policy

    def _check_system_health(self) -> Dict[str, Any]:
        """Check swap and memory usage."""
        try:
            swap = psutil.swap_memory()
            swap_used_mb = swap.used / (1024 * 1024)
            
            if swap_used_mb > self.SWAP_LIMIT_MB:
                return {"status": "critical", "reason": f"Swap {swap_used_mb:.0f}MB > {self.SWAP_LIMIT_MB}MB"}
                
            return {"status": "healthy"}
        except Exception as e:
            logger.error(f"Failed to check system health: {e}")
            return {"status": "unknown"}

    def _get_agents_for_profile(self, profile: ExecutionProfile) -> Set[str]:
        """Map profile to required agents."""
        agents = self.AGENTS_CORE.copy()
        
        if profile == ExecutionProfile.SENSORY:
            agents.update(self.AGENTS_SENSORY)
            
        elif profile == ExecutionProfile.OPTIMIZE:
            agents.update(self.AGENTS_SENSORY)
            agents.update(self.AGENTS_OPTIMIZE)
            
        elif profile == ExecutionProfile.RESEARCH:
            agents.update(self.AGENTS_SENSORY)
            agents.update(self.AGENTS_OPTIMIZE)
            # Add any research-specific agents here
            
        return agents

    def _calculate_budget(self, profile: ExecutionProfile) -> Dict[str, float]:
        """Define latency targets (seconds) for monitoring."""
        if profile == ExecutionProfile.FAST:
            return {"first_token": 2.0, "layer1": 5.0, "total": 10.0}
        elif profile == ExecutionProfile.SENSORY:
             return {"first_token": 2.0, "layer1": 5.0, "layer2": 15.0, "total": 30.0}
        else:
             return {"first_token": 2.0, "layer1": 5.0, "layer3": 60.0, "total": 120.0}
