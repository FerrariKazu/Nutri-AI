"""
Nutri Memory Guard
Protects the system from Out-Of-Memory (OOM) crashes by enforcing strict RAM limits.
"""

import psutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum RAM required to be free before loading a heavy index (in GB)
# Chemistry index is ~12GB, but swap can handle some overflow.
# Realistically, we need at least 2-3GB of *actual* RAM free to avoid severe thrashing.
MIN_FREE_RAM_GB = 2.0 

# Max system memory usage percentage allowed before forcing eviction
MAX_RAM_PERCENT = 90.0

def get_system_memory_status() -> dict:
    """Return current system memory stats."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / 1e9,
        "available_gb": mem.available / 1e9,
        "percent": mem.percent,
        "used_gb": mem.used / 1e9,
        "free_gb": mem.free / 1e9
    }

def check_memory_safety(required_gb: float = 0.5) -> bool:
    """
    Check if it is safe to allocate 'required_gb' of memory.
    Raises MemoryError if unsafe.
    
    Args:
        required_gb: Estimated GB required for the new allocation.
    """
    stats = get_system_memory_status()
    available = stats["available_gb"]
    percent = stats["percent"]
    
    logger.debug(f"Memory Check: Available={available:.2f}GB, Used={percent}%")
    
    # 1. Check absolute available RAM
    if available < required_gb:
        msg = f"Insufficient memory! Available: {available:.2f}GB, Required: {required_gb:.2f}GB"
        logger.error(f"⛔ {msg}")
        raise MemoryError(msg)
    
    # 2. Check danger zone usage
    if percent > MAX_RAM_PERCENT:
        msg = f"System memory critical! Usage: {percent}% > {MAX_RAM_PERCENT}%"
        logger.warning(f"⚠️ {msg}")
        # We might not raise here if the allocation is tiny, but for indices we should.
        if required_gb > 0.1:
            raise MemoryError(msg)
            
    return True
