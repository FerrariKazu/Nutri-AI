# Initialize Conda in PowerShell and run setup

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Nutri RAG - Conda Setup (PowerShell)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Conda installation path
$condaPath = "C:\ProgramData\miniconda3"

if (-not (Test-Path "$condaPath\Scripts\conda.exe")) {
    Write-Host "ERROR: Conda not found at $condaPath" -ForegroundColor Red
    Write-Host "Please adjust the path in this script" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found conda at: $condaPath" -ForegroundColor Green
Write-Host ""

# Initialize conda for this session
Write-Host "Initializing conda for PowerShell..." -ForegroundColor Yellow
& "$condaPath\shell\condabin\conda-hook.ps1"
conda activate

Write-Host ""
Write-Host "Step 1: Removing old nutri-rag environment..." -ForegroundColor Yellow
conda env remove -n nutri-rag -y 2>$null

Write-Host ""
Write-Host "Step 2: Creating environment from environment.yml..." -ForegroundColor Yellow
Write-Host "(This will take 5-10 minutes)" -ForegroundColor Cyan
conda env create -f environment.yml

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to create environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Step 3: Activating and testing..." -ForegroundColor Yellow
conda activate nutri-rag

Write-Host ""
Write-Host "Testing imports:" -ForegroundColor Yellow
python -c "import numpy; print(f'✅ numpy {numpy.__version__}')"
python -c "import pandas; print(f'✅ pandas {pandas.__version__}')"
python -c "import torch; print(f'✅ torch {torch.__version__}')"
python -c "import faiss; print('✅ faiss OK')"
python -c "import sentence_transformers; print('✅ sentence-transformers OK')"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "SUCCESS! Environment created" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To activate in future PowerShell sessions:" -ForegroundColor Cyan
Write-Host "  & C:\ProgramData\miniconda3\shell\condabin\conda-hook.ps1" -ForegroundColor White
Write-Host "  conda activate nutri-rag" -ForegroundColor White
Write-Host ""
Write-Host "Next: Run reindexing" -ForegroundColor Cyan
Write-Host "  python scripts\reindex.py" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
