"""
Nutri Memory Guard
Protects the system from Out-Of-Memory (OOM) crashes by enforcing strict RAM and GPU VRAM limits.
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

# Max GPU VRAM usage ratio (0-1) before blocking new allocations
MAX_GPU_VRAM_RATIO = 0.85


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


import os

def estimate_index_memory(index_path=None, index_obj=None) -> float:
    """
    Estimate memory required for an index.
    Supports file path (pre-load) or loaded index object.
    """
    # Case 1: File path available
    if index_path is not None:
        if not isinstance(index_path, (str, os.PathLike)):
            logger.warning(f"[MEMORY_GUARD] index_path is {type(index_path).__name__}, expected str. Skipping getsize.")
        elif os.path.exists(index_path):
            return float(os.path.getsize(index_path))

    # Case 2: Index already loaded
    if index_obj is not None:
        try:
            # Traditional calculation for FAISS
            ntotal = getattr(index_obj, "ntotal", 0)
            d = getattr(index_obj, "d", 0)
            return float(ntotal * d * 4)
        except Exception:
            pass

    return 0.0


def check_gpu_safety(max_ratio: float = MAX_GPU_VRAM_RATIO) -> bool:
    """
    Check GPU VRAM usage. Raises MemoryError if usage exceeds max_ratio.
    Safely skips if CUDA is not available (CPU-only environments).
    """
    try:
        import torch
    except ImportError:
        logger.debug("torch not installed — skipping GPU VRAM check.")
        return True

    if not torch.cuda.is_available():
        logger.debug("CUDA not available — skipping GPU VRAM check.")
        return True

    try:
        props = torch.cuda.get_device_properties(0)
        total = props.total_memory
    except Exception as e:
        logger.warning(f"Failed to get GPU properties: {e}")
        return True

    reserved = torch.cuda.memory_reserved()
    ratio = reserved / total if total > 0 else 0.0

    logger.debug(f"GPU VRAM Check: reserved={reserved / 1e9:.2f}GB, total={total / 1e9:.2f}GB, ratio={ratio:.2%}")

    if ratio > max_ratio:
        msg = f"GPU VRAM limit exceeded! Usage: {ratio:.1%} > {max_ratio:.0%} ({reserved / 1e9:.2f}/{total / 1e9:.2f} GB)"
        logger.error(f"⛔ {msg}")
        raise MemoryError(msg)

    return True


def check_memory_safety(index_path: Optional[str] = None, headroom_multiplier: float = 1.3) -> bool:
    """
    Check if it is safe to load an index.
    Ensures available RAM > index_size * headroom_multiplier.
    Also checks GPU VRAM if CUDA is available.
    Raises MemoryError if unsafe.
    """
    stats = get_system_memory_status()
    available = stats["available_gb"]
    percent = stats["percent"]

    required_bytes = estimate_index_memory(index_path=index_path) if index_path else 0.5 * 1e9
    required_gb = required_bytes / 1e9
    threshold_gb = required_gb * headroom_multiplier
    
    logger.debug(f"Memory Check: Available={available:.2f}GB, Required={required_gb:.2f}GB, Threshold={threshold_gb:.2f}GB")

    # 1. Check available RAM with headroom
    if available < threshold_gb:
        msg = f"Insufficient memory guard! Available: {available:.2f}GB, Threshold (req*{headroom_multiplier}): {threshold_gb:.2f}GB"
        logger.error(f"⛔ {msg}")
        raise MemoryError(msg)

    # 2. Check danger zone usage
    if percent > MAX_RAM_PERCENT:
        msg = f"System memory critical! Usage: {percent}% > {MAX_RAM_PERCENT}%"
        logger.warning(f"⚠️ {msg}")
        if required_gb > 0.1:
            raise MemoryError(msg)

    # 3. Check GPU VRAM
    check_gpu_safety()

    return True
