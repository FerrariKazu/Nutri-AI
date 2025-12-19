#!/bin/bash
# Reindex all nutrition datasets and build FAISS indices
# Linux/Mac version

set -e  # Exit on error

echo "=============================================="
echo "Nutri RAG System - Reindexing"
echo "=============================================="

# Activate venv if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check Python
python --version

# Run reindexing script
python scripts/reindex.py

echo ""
echo "=============================================="
echo "✅ Reindexing complete!"
echo "=============================================="
echo ""
echo "Next step: uvicorn api:app --reload"
echo "=============================================="
echo ""
echo "Next step: uvicorn api:app --reload"
