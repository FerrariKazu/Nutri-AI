import os
import sys
import time
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(os.getcwd())
sys.path.insert(0, str(PROJECT_ROOT))

# Mock the pieces we need from the original script
DATA_SOURCES_DIR = PROJECT_ROOT / "data_sources"

def profile_chemistry():
    chem_dir = DATA_SOURCES_DIR / "chemistry"
    
    start_time = time.time()
    idx = 0
    limit = 10000
    
    print(f"Profiling Chemistry generator for {limit} items...")
    
    fooddb_dir = chem_dir / "FoodDB"
    if fooddb_dir.exists():
        for csv_path in fooddb_dir.glob("*.csv"):
            if csv_path.name != "Content.csv": continue # Focus on the big one
            print(f"  Streaming FoodDB: {csv_path.name}")
            try:
                for chunk in pd.read_csv(csv_path, chunksize=5000, low_memory=False):
                    for _, row in chunk.iterrows():
                        # The original slow logic
                        text = f"Chemistry: {csv_path.stem} | Info: " + " | ".join([f"{k}: {v}" for k, v in row.to_dict().items() if pd.notna(v)])
                        idx += 1
                        if idx >= limit:
                            break
                    if idx >= limit:
                        break
            except Exception as e:
                print(f"Error: {e}")
            if idx >= limit:
                break

    end_time = time.time()
    duration = end_time - start_time
    print(f"Total time for {limit} items: {duration:.2f}s ({limit/duration:.2f} items/s)")

if __name__ == "__main__":
    profile_chemistry()
