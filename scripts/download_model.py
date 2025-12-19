"""
Pre-download model to avoid hangs during main execution.
"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("Downloading model...", flush=True)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model downloaded and cached successfully!", flush=True)
