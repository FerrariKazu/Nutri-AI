"""
CUDA GPU Monitoring Utilities

Provides functions to check CUDA availability and monitor GPU usage
for llama.cpp integration.
"""

import logging
import subprocess
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def check_cuda_available() -> bool:
    """
    Check if CUDA/NVIDIA GPU is accessible via nvidia-smi.
    
    Returns:
        True if nvidia-smi succeeds, False otherwise
    """
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_vram_usage() -> Optional[Dict[str, int]]:
    """
    Get current VRAM usage in MB.
    
    Returns:
        Dict with 'used', 'total', 'free' in MB, or None if unavailable
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,memory.free",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            used, total, free = map(int, result.stdout.strip().split(","))
            return {"used": used, "total": total, "free": free}
        
        return None
    except Exception as e:
        logger.warning(f"Failed to query VRAM usage: {e}")
        return None


def get_gpu_utilization() -> Optional[int]:
    """
    Get current GPU utilization percentage.
    
    Returns:
        GPU utilization (0-100), or None if unavailable
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return int(result.stdout.strip())
        
        return None
    except Exception as e:
        logger.warning(f"Failed to query GPU utilization: {e}")
        return None


def log_gpu_status():
    """
    Log comprehensive GPU status including name, VRAM, and utilization.
    Useful for startup diagnostics.
    """
    try:
        # Get GPU name
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        gpu_name = result.stdout.strip() if result.returncode == 0 else "Unknown"
        
        # Get VRAM info
        vram = get_vram_usage()
        vram_str = f"{vram['used']}/{vram['total']} MB" if vram else "N/A"
        
        # Get utilization
        util = get_gpu_utilization()
        util_str = f"{util}%" if util is not None else "N/A"
        
        logger.info("=" * 60)
        logger.info("GPU Status:")
        logger.info(f"  GPU: {gpu_name}")
        logger.info(f"  VRAM: {vram_str}")
        logger.info(f"  Utilization: {util_str}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.warning(f"Could not log GPU status: {e}")
