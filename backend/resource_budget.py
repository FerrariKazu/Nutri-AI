import psutil
import torch
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResourceBudget:
    """
    Tracks GPU VRAM and CPU RAM usage to prevent system overload.
    Enforces strict limits for Low-VRAM environments (<=8GB).
    """
    
    # Defaults for 8GB VRAM system
    MAX_VRAM_PERCENT = 92.0
    MAX_RAM_PERCENT = 85.0
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Return current resource usage stats."""
        status = {
            "ram_percent": psutil.virtual_memory().percent,
            "gpu_vram": None,
            "gpu_vram_percent": None,
            "healthy": True
        }
        
        if torch.cuda.is_available():
            try:
                # Use nvidia-smi query if possible for accurate total vs used
                # Fallback to torch.cuda memory stats
                vram_used = torch.cuda.memory_allocated() / (1024**3) # GB
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3) # GB
                status["gpu_vram"] = vram_used
                status["gpu_vram_percent"] = (vram_used / vram_total) * 100
                
                if status["gpu_vram_percent"] > cls.MAX_VRAM_PERCENT:
                    status["healthy"] = False
            except Exception as e:
                logger.debug(f"Failed to get detailed GPU stats: {e}")
        
        if status["ram_percent"] > cls.MAX_RAM_PERCENT:
            status["healthy"] = False
            
        return status

    @classmethod
    def check_budget(cls, task_name: str, requires_gpu: bool = False):
        """
        Check if the budget allows for a new task.
        Raises RuntimeError if budget is exceeded.
        """
        status = cls.get_status()
        
        if not status["healthy"]:
            msg = f"[RESOURCE_BUDGET_EXCEEDED] Cannot schedule '{task_name}'. RAM={status['ram_percent']}%, VRAM={status.get('gpu_vram_percent', 'N/A')}%"
            logger.error(msg)
            raise RuntimeError(msg)
            
        if requires_gpu and status.get("gpu_vram_percent", 0) > 85.0:
            msg = f"[RESOURCE_BUDGET_EXCEEDED] GPU constrained. Rejection '{task_name}'."
            logger.warning(msg)
            raise RuntimeError(msg)
            
        logger.debug(f"[RESOURCE_BUDGET] Task '{task_name}' allowed. RAM={status['ram_percent']}%")
