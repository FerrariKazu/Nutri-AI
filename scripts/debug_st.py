"""
Diagnostic script for Sentence Transformers import.
"""
import os
import sys
import time

# Disable tokenizers parallelism which can cause deadlocks on Windows
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("DEBUG: Starting ST diagnostic...", flush=True)

def test_import(module_name):
    print(f"DEBUG: Importing {module_name}...", end=" ", flush=True)
    start = time.time()
    try:
        __import__(module_name)
        print(f"✅ Done ({time.time() - start:.2f}s)", flush=True)
    except Exception as e:
        print(f"❌ Failed: {e}", flush=True)

# Test dependencies in order
test_import("numpy")
test_import("torch")
test_import("tqdm")
test_import("transformers")
test_import("tokenizers")
test_import("huggingface_hub")

print("DEBUG: Importing sentence_transformers...", flush=True)
try:
    from sentence_transformers import SentenceTransformer
    print("✅ SentenceTransformer imported successfully!", flush=True)
except Exception as e:
    print(f"❌ Failed to import SentenceTransformer: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("DEBUG: Diagnostic complete.", flush=True)
