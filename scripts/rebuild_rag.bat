@echo off
REM Rebuild RAG Index - Complete Pipeline
REM Extracts PDFs → Chunks text → Builds FAISS index

setlocal

echo ============================================================
echo RAG System - Complete Rebuild
echo ===========================================================================================

REM Activate conda environment
if not exist "C:\Users\FerrariKazu\.conda\envs\nutri-rag\python.exe" (
    echo ERROR: nutri-rag environment not found
    echo Please run the conda environment setup first
    pause
    exit /b 1
)

set "PYTHON_EXE=C:\Users\FerrariKazu\.conda\envs\nutri-rag\python.exe"

echo.
echo Step 1/3: Extracting PDFs...
echo ----------------------------
"%PYTHON_EXE%" scripts\extract_pdfs.py
if errorlevel 1 (
    echo ERROR: PDF extraction failed
    pause
    exit /b 1
)

echo.
echo Step 2/3: Chunking text...
echo --------------------------
"%PYTHON_EXE%" scripts\chunk_text.py
if errorlevel 1 (
    echo ERROR: Text chunking failed
    pause
    exit /b 1
)

echo.
echo Step 3/3: Building FAISS index...
echo ----------------------------------
"%PYTHON_EXE%" scripts\build_faiss_index.py
if errorlevel 1 (
    echo ERROR: FAISS index build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo RAG REBUILD COMPLETE
echo ============================================================
echo.
echo To test the system:
echo   1. Start API: conda activate nutri-rag ^&^& uvicorn api:app --reload
echo   2. Open browser: http://localhost:8000/docs
echo   3. Try POST /api/ask_science endpoint
echo.
echo Index location: processed\faiss_index\
echo ============================================================
pause
