from backend.config.models import EMBEDDING_MODEL_PATH
from backend.embedder.embedder_bge import BGEEmbedder

class EmbedderSingleton:
    _instance = None

    @classmethod
    def get(cls):
        """Thread-safe singleton getter for BGEEmbedder."""
        if cls._instance is None:
            cls._instance = BGEEmbedder(EMBEDDING_MODEL_PATH)
        return cls._instance

def get_embedder():
    return EmbedderSingleton.get()
