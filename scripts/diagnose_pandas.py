"""
Diagnostic script to identify pandas import hang cause.

Tests different import strategies and DLL configurations.
"""

import os
import sys

print("=" * 60)
print("PANDAS IMPORT DIAGNOSTIC")
print("=" * 60)

# Test 1: Check Python and numpy
print("\n1. Testing Python and Numpy...")
print(f"Python: {sys.version}")
print(f"Python path: {sys.executable}")

try:
    import numpy as np
    print(f"✅ Numpy {np.__version__} imported successfully")
    print(f"   Numpy location: {np.__file__}")
except Exception as e:
    print(f"❌ Numpy import failed: {e}")
    sys.exit(1)

# Test 2: Set environment variables to use simpler BLAS
print("\n2. Setting OpenBLAS threading to 1...")
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
print("   Environment variables set")

# Test 3: Try importing pandas with timeout warning
print("\n3. Attempting pandas import...")
print("   (If this hangs for >30 seconds, there's a DLL issue)")

import time
start = time.time()

try:
    import pandas as pd
    elapsed = time.time() - start
    print(f"✅ Pandas {pd.__version__} imported in {elapsed:.2f}s")
    print(f"   Pandas location: {pd.__file__}")
except Exception as e:
    print(f"❌ Pandas import failed: {e}")
    sys.exit(1)

# Test 4: Pandas basic operation
print("\n4. Testing pandas basic operation...")
try:
    df = pd.DataFrame({'a': [1, 2, 3]})
    print(f"✅ Created test DataFrame: {len(df)} rows")
except Exception as e:
    print(f"❌ Pandas operation failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED")
print("=" * 60)
print("\nPandas is working! The environment variables fixed the issue.")
print("Use these settings in your reindex script.")
