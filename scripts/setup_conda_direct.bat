@echo off
REM Direct conda setup without PowerShell hooks

setlocal EnableDelayedExpansion

echo ================================================
echo Nutri RAG - Conda Setup (Direct)
echo ================================================
echo.

set "CONDA_EXE=C:\ProgramData\miniconda3\Scripts\conda.exe"
set "CONDA_ROOT=C:\ProgramData\miniconda3"

if not exist "%CONDA_EXE%" (
    echo ERROR: Conda not found at %CONDA_EXE%
    pause
    exit /b 1
)

echo Found conda at: %CONDA_ROOT%
echo.

REM Step 1: Remove old environment
echo Step 1: Removing old nutri-rag environment (if exists)...
"%CONDA_EXE%" env remove -n nutri-rag -y 2>nul

REM Step 2: Create environment
echo.
echo Step 2: Creating environment from environment.yml...
echo This will take 5-10 minutes, please wait...
"%CONDA_EXE%" env create -f environment.yml

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create environment
    pause
    exit /b 1
)

REM Step 3: Test imports
echo.
echo Step 3: Testing library imports...
set "PYTHON_EXE=%CONDA_ROOT%\envs\nutri-rag\python.exe"

"%PYTHON_EXE%" -c "import numpy; print(f'✓ numpy {numpy.__version__}')" || goto :error
"%PYTHON_EXE%" -c "import pandas; print(f'✓ pandas {pandas.__version__}')" || goto :error
"%PYTHON_EXE%" -c "import torch; print(f'✓ torch {torch.__version__}')" || goto :error
"%PYTHON_EXE%" -c "import faiss; print('✓ faiss OK')" || goto :error
"%PYTHON_EXE%" -c "import sentence_transformers; print('✓ sentence-transformers OK')" || goto :error

echo.
echo ================================================
echo SUCCESS! Environment created
echo ================================================
echo.
echo Next step: Run reindexing
echo   scripts\reindex_conda_direct.bat
echo.
pause
exit /b 0

:error
echo.
echo ================================================
echo ERROR: Import test failed
echo ================================================
pause
exit /b 1
