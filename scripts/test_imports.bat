@echo off
echo Testing library imports in venv...
echo.

call venv\Scripts\activate.bat

echo Testing numpy...
python -c "import numpy; print(f'numpy: {numpy.__version__}')" || goto :error

echo Testing pandas...
python -c "import pandas; print(f'pandas: {pandas.__version__}')" || goto :error

echo Testing torch...
python -c "import torch; print(f'torch: {torch.__version__}')" || goto :error

echo Testing faiss...
python -c "import faiss; print(f'faiss: OK')" || goto :error

echo.
echo ============================================
echo All libraries imported successfully!
echo ============================================
echo.
echo You can now run: scripts\reindex_all.bat
pause
exit /b 0

:error
echo.
echo ============================================
echo ERROR: Library import failed
echo ============================================
pause
exit /b 1
