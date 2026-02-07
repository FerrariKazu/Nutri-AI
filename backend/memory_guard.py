"""
Nutri Memory Guard - Circuit Breaker for Memory Pressure
Prevents system thrashing by downgrading execution profile or capping generation.
"""

import logging
import psutil
from backend.execution_profiles import ExecutionProfile

logger = logging.getLogger(__name__)


class MemoryGuard:
    """Circuit breaker for memory pressure detection"""
    
    # Thresholds
    SWAP_THRESHOLD_MB = 1500  # Downgrade/Cap if swap usage > 1.5GB
    SWAP_CRITICAL_MB = 2500   # Force FAST / Heavy Cap if swap > 2.5GB
    
    @staticmethod
    def check_pressure() -> tuple[bool, float]:
        """
        Check if system is under memory pressure.
        
        Returns:
            (is_under_pressure, swap_used_mb)
        """
        try:
            swap = psutil.swap_memory()
            mem = psutil.virtual_memory()
            
            swap_used_mb = swap.used / (1024**2)
            available_gb = mem.available / (1024**3)
            
            # Intelligent Check:
            # If we have > 2GB of available RAM, we are NOT under pressure,
            # even if swap is high (kernel being lazily swappy).
            if available_gb > 2.0:
                return False, swap_used_mb
                
            is_pressure = swap_used_mb > MemoryGuard.SWAP_THRESHOLD_MB
            
            if is_pressure:
                logger.warning(f"Memory pressure detected: {swap_used_mb:.1f}MB swap in use (Available RAM: {available_gb:.2f}GB)")
            
            return is_pressure, swap_used_mb
        except Exception as e:
            logger.error(f"Failed to check memory pressure: {e}")
            return False, 0.0

    
    @staticmethod
    def safe_profile(requested: ExecutionProfile) -> ExecutionProfile:
        """
        Downgrade profile if memory pressure detected.
        
        Args:
            requested: User's requested execution profile
            
        Returns:
            Safe execution profile (possibly downgraded)
        """
        is_pressure, swap_mb = MemoryGuard.check_pressure()
        
        if not is_pressure:
            return requested
        
        # Critical pressure: force FAST
        if swap_mb > MemoryGuard.SWAP_CRITICAL_MB:
            logger.warning(
                f"CRITICAL memory pressure ({swap_mb:.1f}MB swap), "
                f"forcing FAST mode (requested: {requested.value})"
            )
            return ExecutionProfile.FAST
        
        # Moderate pressure: downgrade complex profiles
        if requested in [ExecutionProfile.OPTIMIZE, ExecutionProfile.RESEARCH]:
            logger.warning(
                f"Memory pressure detected ({swap_mb:.1f}MB swap), "
                f"downgrading {requested.value} → SENSORY"
            )
            return ExecutionProfile.SENSORY
        
        # FAST and SENSORY are already lightweight
        return requested
    
    @staticmethod
    def get_safe_token_limit(requested_tokens: int) -> int:
        """
        Cap max_new_tokens if system is under pressure.
        """
        is_pressure, swap_mb = MemoryGuard.check_pressure()
        
        if not is_pressure:
            return requested_tokens
            
        limit = 4096
        if swap_mb > MemoryGuard.SWAP_CRITICAL_MB:
            limit = 2048
            
        if requested_tokens > limit:
            logger.warning(f"Memory Pressure: Capping tokens {requested_tokens} -> {limit}")
            return limit
            
        return requested_tokens

    @staticmethod
    def log_memory_stats():
        """Log current memory statistics for observability"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            logger.info(
                f"Memory: {mem.percent:.1f}% used "
                f"({mem.used / (1024**3):.2f}GB / {mem.total / (1024**3):.2f}GB)"
            )
            logger.info(
                f"Swap: {swap.percent:.1f}% used "
                f"({swap.used / (1024**2):.1f}MB / {swap.total / (1024**2):.1f}MB)"
            )
        except Exception as e:
            logger.error(f"Failed to log memory stats: {e}")
