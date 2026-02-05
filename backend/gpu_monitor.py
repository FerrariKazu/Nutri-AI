import torch
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GPUMonitor:
    """
    Monitoring utility to detect VRAM leaks and track GPU health.
    """
    
    def __init__(self):
        self.last_vram: Optional[float] = None
        self.leak_threshold_mb = 100.0 # Notify on >100MB growth per request
        self.consecutive_leaks = 0
        self.degraded_mode = False
        
    def sample_before(self):
        """Take a pre-request VRAM sample."""
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            self.last_vram = torch.cuda.memory_allocated() / (1024**2) # MB
            
    def sample_after(self):
        """Take a post-request VRAM sample and check for suspected leaks."""
        if torch.cuda.is_available() and self.last_vram is not None:
            torch.cuda.synchronize()
            current_vram = torch.cuda.memory_allocated() / (1024**2) # MB
            delta = current_vram - self.last_vram
            
            if delta > self.leak_threshold_mb:
                self.consecutive_leaks += 1
                logger.warning(f"[GPU_LEAK_SUSPECTED] VRAM grew by {delta:.2f}MB during request (Streak: {self.consecutive_leaks}). "
                               f"Current: {current_vram:.2f}MB")
                
                if self.consecutive_leaks >= 3:
                     if not self.degraded_mode:
                         logger.error("[GPU_DEGRADED_MODE] Leak threshold exceeded 3x. Forcing self-healing.")
                         self.degraded_mode = True
                     torch.cuda.empty_cache()
                
                # Selective cleanup
                if current_vram > 6000: # High usage threshold
                     logger.info("[GPU_MONITOR] High VRAM usage detected. Invoking torch.cuda.empty_cache()")
                     torch.cuda.empty_cache()
            else:
                if self.consecutive_leaks > 0:
                    logger.info(f"[GPU_MONITOR] Stability recovered. Resetting leak streak (Was: {self.consecutive_leaks})")
                    self.consecutive_leaks = 0
                    self.degraded_mode = False
            
            self.last_vram = current_vram

# Global monitor instance
gpu_monitor = GPUMonitor()
