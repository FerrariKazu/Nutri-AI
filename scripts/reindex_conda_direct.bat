@echo off
REM Reindex using conda environment directly

setlocal

set "CONDA_ROOT=C:\ProgramData\miniconda3"
set "PYTHON_EXE=%CONDA_ROOT%\envs\nutri-rag\python.exe"

if not exist "%PYTHON_EXE%" (
    echo ERROR: nutri-rag environment not found
    echo Please run scripts\setup_conda_direct.bat first
    pause
    exit /b 1
)

echo ==============================================
echo Nutri RAG System - Reindexing
echo ==============================================
echo.

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

echo Running reindex script...
"%PYTHON_EXE%" scripts\reindex.py

echo.
echo ==============================================
echo Reindexing complete!
echo ==============================================
pause
