@echo off
REM Final reindex script using conda environment

setlocal

set "PYTHON_EXE=C:\Users\FerrariKazu\.conda\envs\nutri-rag\python.exe"

if not exist "%PYTHON_EXE%" (
    echo ERROR: nutri-rag environment not found
    echo Expected at: %PYTHON_EXE%
    pause
    exit /b 1
)

echo ==============================================
echo Nutri RAG System - Reindexing (Conda)
echo ==============================================
echo.

echo Using Python from conda environment:
"%PYTHON_EXE%" --version
echo.

echo Starting reindex process...
echo (This may take several minutes)
echo.

"%PYTHON_EXE%" scripts\reindex.py

if errorlevel 1 (
    echo.
    echo ==============================================
    echo ERROR: Reindexing failed
    echo ==============================================
    pause
    exit /b 1
)

echo.
echo ==============================================
echo SUCCESS! Reindexing complete
echo ==============================================
echo.
echo Next: Start the API server
pause
