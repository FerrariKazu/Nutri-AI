@echo off
REM Setup Conda Environment for Nutri RAG System
REM Requires: Miniconda or Anaconda installed

echo ================================================
echo Nutri RAG System - Conda Environment Setup
echo ================================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: conda not found in PATH
    echo.
    echo Please ensure Miniconda/Anaconda is installed and:
    echo 1. Open Anaconda Prompt (Miniconda3)
    echo 2. Navigate to this project directory
    echo 3. Run this script again
    pause
    exit /b 1
)

echo Step 1: Removing old nutri-rag environment (if exists)...
call conda env remove -n nutri-rag -y

echo.
echo Step 2: Creating nutri-rag environment from environment.yml...
echo This will take 5-10 minutes...
call conda env create -f environment.yml

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to create conda environment
    pause
    exit /b 1
)

echo.
echo Step 3: Activating environment and testing imports...
call conda activate nutri-rag

echo.
echo Testing core libraries:
python -c "import numpy; print(f'✅ numpy {numpy.__version__}')" || goto :error
python -c "import pandas; print(f'✅ pandas {pandas.__version__}')" || goto :error
python -c "import torch; print(f'✅ torch {torch.__version__} (CUDA: {torch.cuda.is_available()})')" || goto :error
python -c "import faiss; print('✅ faiss OK')" || goto :error
python -c "import sentence_transformers; print('✅ sentence-transformers OK')" || goto :error

echo.
echo ================================================
echo SUCCESS! Conda environment 'nutri-rag' created
echo ================================================
echo.
echo To use this environment:
echo   conda activate nutri-rag
echo.
echo Next step: Run the reindexing script
echo   scripts\reindex_conda.bat
echo.
pause
exit /b 0

:error
echo.
echo ================================================
echo ERROR: Import test failed
echo ================================================
echo Please check the error messages above
pause
exit /b 1
