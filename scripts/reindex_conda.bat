@echo off
REM Reindexing script using Conda environment

echo ==============================================
echo Nutri RAG System - Reindexing (Conda)
echo ==============================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: conda not found
    echo Please run this from Anaconda Prompt (Miniconda3)
    pause
    exit /b 1
)

REM Activate nutri-rag environment
echo Activating nutri-rag environment...
call conda activate nutri-rag

if %errorlevel% neq 0 (
    echo ERROR: Failed to activate nutri-rag environment
    echo Please run scripts\setup_conda_env.bat first
    pause
    exit /b 1
)

echo.
echo Python version:
python --version

echo.
echo Running reindex script...
python scripts\reindex.py

echo.
echo ==============================================
echo Reindexing complete!
echo ==============================================
echo.
echo Next: Start the API server
echo   conda activate nutri-rag
echo   uvicorn api:app --reload
pause
