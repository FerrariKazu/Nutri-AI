@echo off
REM Reindex all nutrition datasets and build FAISS indices
REM Windows version

echo ==============================================
echo Nutri RAG System - Reindexing
echo ==============================================

REM Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check Python
python --version

REM Run reindexing script
python scripts/reindex.py

echo.
echo ==============================================
echo Reindexing complete!
echo ==============================================
echo.
echo Next step: uvicorn api:app --reload
pause
echo ==============================================
echo.
echo Next step: uvicorn api:app --reload
pause
