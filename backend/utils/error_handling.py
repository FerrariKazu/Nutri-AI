import time
import logging
import functools

logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """Decorator for retrying a function with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Failed after {retries} retries: {e}")
                        raise
                    
                    sleep = (backoff_in_seconds * (2 ** x))
                    logger.warning(f"Retrying in {sleep}s due to error: {e}")
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator

class ErrorMessageFormatter:
    """Format error messages for user-friendly display."""
    @staticmethod
    def format(error):
        return f"Nutri-AI encountered an issue: {str(error)}. Please try again."
