import logging
import sys

def setup_logging(level=logging.INFO):
    """Simple logging configuration for the backend."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_logger(name):
    """Get a named logger."""
    return logging.getLogger(name)
