import asyncio
import logging

logger = logging.getLogger(__name__)

class EmbeddingThrottle:
    """
    Manages concurrency for CPU-intensive embedding operations.
    Prevents thread starvation by using a semaphore.
    """
    
    # Limit to 2 concurrent embedding operations to keep CPU responsive
    _semaphore = asyncio.Semaphore(2)
    _queue_depth = 0
    _wait_ms_total = 0.0
    _wait_count = 0
    
    @classmethod
    async def run_throttled(cls, func, *args, **kwargs):
        """
        Runs an embedding function behind a semaphore.
        Logs [EMBEDDING_BACKPRESSURE] if it has to wait.
        """
        import time
        start_wait = time.perf_counter()
        
        cls._queue_depth += 1
        try:
            if cls._semaphore.locked():
                logger.warning(f"[EMBEDDING_BACKPRESSURE] Throttling embedding request... (Depth: {cls._queue_depth})")
                
            async with cls._semaphore:
                wait_duration = (time.perf_counter() - start_wait) * 1000
                cls._wait_ms_total += wait_duration
                cls._wait_count += 1
                avg_wait = cls._wait_ms_total / cls._wait_count
                
                if wait_duration > 50:
                    logger.info(f"[EMBEDDING_TELEMETRY] Queue Depth: {cls._queue_depth}, Wait: {wait_duration:.1f}ms, Avg: {avg_wait:.1f}ms")
                
                return await func(*args, **kwargs)
        finally:
            cls._queue_depth -= 1

    @classmethod
    def get_stats(cls):
        avg_wait = cls._wait_ms_total / cls._wait_count if cls._wait_count > 0 else 0
        return {
            "embedding_queue_depth": cls._queue_depth,
            "embedding_wait_ms_avg": avg_wait
        }


# Singleton/Convenience access
async def run_throttled_embedding(func, *args, **kwargs):
    return await EmbeddingThrottle.run_throttled(func, *args, **kwargs)
