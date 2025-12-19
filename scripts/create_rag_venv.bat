@echo off
REM Create a NEW virtual environment specifically for RAG
REM Uses venv-rag instead of venv to avoid conflicts

echo ================================================
echo Creating RAG-Only Virtual Environment
echo ================================================
echo.

REM Step 1: Create fresh venv with new name
echo Step 1: Creating virtual environment as 'venv-rag'...
if exist venv-rag (
    echo Removing old venv-rag...
    rmdir /s /q venv-rag
)

python -m venv venv-rag
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

REM Step 2: Upgrade pip
echo.
echo Step 2: Upgrading pip...
venv-rag\Scripts\python.exe -m pip install --upgrade pip

REM Step 3: Install RAG requirements
echo.
echo Step 3: Installing RAG requirements (this will take a few minutes)...
venv-rag\Scripts\python.exe -m pip install -r requirements-rag.txt

REM Step 4: Verify installations
echo.
echo Step 4: Testing library imports...
venv-rag\Scripts\python.exe -c "import numpy; print(f'✅ numpy {numpy.__version__}')"
venv-rag\Scripts\python.exe -c "import pandas; print(f'✅ pandas {pandas.__version__}')"
venv-rag\Scripts\python.exe -c "import torch; print(f'✅ torch {torch.__version__}')"
venv-rag\Scripts\python.exe -c "import faiss; print('✅ faiss OK')"
venv-rag\Scripts\python.exe -c "import sentence_transformers; print('✅ sentence-transformers OK')"

echo.
echo ================================================
echo SUCCESS! RAG environment created
echo ================================================
echo.
echo To use it, activate with:
echo   venv-rag\Scripts\activate
echo.
echo Or use the updated reindex script
pause
