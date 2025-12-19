@echo off
REM Fresh Virtual Environment Setup for RAG System
REM This creates a CLEAN environment WITHOUT Rasa/TensorFlow

echo ================================================
echo Creating Fresh RAG Virtual Environment
echo ================================================
echo.

REM Step 1: Rename old venv
echo Step 1: Backing up old venv...
if exist venv_old rmdir /s /q venv_old
if exist venv (
    echo Renaming venv to venv_old...
    move venv venv_old
) else (
    echo No existing venv found
)

REM Step 2: Create fresh venv
echo.
echo Step 2: Creating fresh virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

REM Step 3: Upgrade pip
echo.
echo Step 3: Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip

REM Step 4: Install RAG requirements
echo.
echo Step 4: Installing RAG system requirements...
venv\Scripts\python.exe -m pip install -r requirements-rag.txt

REM Step 5: Verify installations
echo.
echo Step 5: Verifying installations...
venv\Scripts\python.exe -c "import torch; print(f'✅ torch {torch.__version__}')"
venv\Scripts\python.exe -c "import numpy; print(f'✅ numpy {numpy.__version__}')"
venv\Scripts\python.exe -c "import pandas; print(f'✅ pandas {pandas.__version__}')"
venv\Scripts\python.exe -c "import sentence_transformers; print('✅ sentence-transformers OK')"
venv\Scripts\python.exe -c "import faiss; print('✅ faiss OK')"

echo.
echo ================================================
echo SUCCESS! Fresh environment created
echo ================================================
echo.
echo Your old venv is backed up as venv_old
echo You can delete it later if everything works
echo.
echo Next step: scripts\reindex_all.bat
pause
