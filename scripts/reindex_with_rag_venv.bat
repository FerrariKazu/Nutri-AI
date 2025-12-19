@echo off
REM Reindexing script using the RAG-specific venv

echo ==============================================
echo Nutri RAG System - Reindexing
echo ==============================================

REM Check if venv-rag exists
if not exist venv-rag\Scripts\activate.bat (
    echo ERROR: venv-rag not found!
    echo Please run: scripts\create_rag_venv.bat first
    pause
    exit /b 1
)

REM Activate RAG venv
call venv-rag\Scripts\activate.bat

echo Python version:
python --version
echo.

REM Run reindex script
python scripts\reindex.py

echo.
echo ==============================================
echo Reindexing complete!
echo ==============================================
echo.
echo Next step: uvicorn api:app --reload
pause
