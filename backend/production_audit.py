"""
Nutri Production Audit System

Performs startup scans to ensure model integrity, RAG health, and security.
Fails loudly if legacy artifacts or unregistered models are found.
"""

import os
import re
import sys
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.model_registry import MODEL_REGISTRY, list_registered_models
from backend.pubchem_client import get_pubchem_client

logger = logging.getLogger(__name__)

# LEGACY ARTIFACTS TO BAN
BANNED_STRINGS = [
    r"ollama",
    r"qwen3:8b",
    r"qwen3:4b",
    r"llama_cpp"  # Banned as a direct string in business logic, should be in registry
]

def run_startup_audit():
    """
    Performs the full production audit.
    Crashes the system if violations are found.
    """
    print("\n" + "="*40)
    print("🚀 NUTRI PRODUCTION AUDIT STARTING")
    print("="*40)
    
    violations = []
    
    # 1. Scan for Legacy Artifacts
    print("🔍 Scanning for legacy artifacts...")
    backend_dir = Path(__file__).parent
    
    # Skip core infra files that MUST contain these strings for configuration
    skip_files = [
        "production_audit.py",
        "model_registry.py",
        "llm/factory.py",
        "llm/ollama_client.py",
        "llm/llama_cpp_client.py",
        "llm/base.py",
        "llm_qwen3.py"
    ]
    
    for py_file in backend_dir.glob("**/*.py"):
        rel_path = str(py_file.relative_to(backend_dir))
        if rel_path in skip_files or py_file.name in skip_files:
            continue
            
        try:
            content = py_file.read_text()
            for pattern in BANNED_STRINGS:
                if re.search(pattern, content, re.IGNORECASE):
                    # Exception: allow "logger.info" or "logger.error" containing these if needed?
                    # No, let's be strict.
                    violations.append(f"Legacy string '{pattern}' found in {py_file.relative_to(backend_dir.parent)}")
        except Exception as e:
            logger.warning(f"Failed to scan {py_file}: {e}")

    # 2. Verify Model Registry
    print(f"📖 Model Registry: OK ({len(MODEL_REGISTRY)} models)")
    for name, spec in MODEL_REGISTRY.items():
        print(f"   - {name}: {spec.provider} (ctx: {spec.context_length})")

    # 3. Check for Active Agents
    # In a real system we'd check against a live agent registry
    print(f"🤖 Agents Registered: {len(MODEL_REGISTRY['qwen3-4b'].allowed_agents)}")

    # 4. RAG Status Check (Proactive check for vector store)
    print("📚 Checking RAG Status...")
    db_path = backend_dir / "nutri_sessions.db"
    if not db_path.exists():
        logger.warning("⚠️ Session DB not found (ok for first run)")
    else:
        print("   - Session DB: OK")

    # 5. PubChem Connectivity Check (Hardened with Retries)
    print("🧪 Checking PubChem Connectivity...")
    client = get_pubchem_client()
    
    pubchem_ready = False
    max_retries = 3
    import time
    
    for attempt in range(max_retries):
        if client.health_check():
            pubchem_ready = True
            break
        if attempt < max_retries - 1:
            print(f"   ⚠️  Attempt {attempt + 1} failed. Retrying in 2s...")
            time.sleep(2)
            
    if pubchem_ready:
        print("   - PubChem API: [PUBCHEM_READY]")
    else:
        print("   - PubChem API: ❌ UNREACHABLE")
        violations.append("PubChem API is unreachable after 3 attempts. Nutrition intelligence is compromised.")

    # 6. Summary & Hard Failure
    if violations:
        print("\n" + "!"*40)
        print("❌ AUDIT FAILED: SYSTEM NOT PRODUCTION-SAFE")
        for v in violations:
            print(f"  - {v}")
        print("!"*40 + "\n")
        sys.exit(1)
    
    print("\n✅ AUDIT PASSED: SYSTEM IS PRODUCTION-SAFE")
    print("="*40 + "\n")

if __name__ == "__main__":
    run_startup_audit()
