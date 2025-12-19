@echo off
REM Emergency Environment Fix Script
REM Reinstalls all RAG dependencies with compatible versions

echo ============================================
echo RAG System Environment Fix
echo ============================================
echo.

REM Activate venv
call venv\Scripts\activate.bat

echo Step 1: Uninstalling conflicting packages...
pip uninstall -y torch torchvision torchaudio sentence-transformers transformers huggingface-hub faiss-cpu numpy pandas scipy

echo.
echo Step 2: Installing compatible RAG stack...
pip install -r requirements-rag.txt

echo.
echo Step 3: Verification...
python -c "import torch; import pandas; import sentence_transformers; import faiss; print('SUCCESS: All core libraries imported!')"

echo.
echo ============================================
echo Environment fix complete!
echo ============================================
echo.
echo Next: Run scripts\reindex_all.bat
pause
