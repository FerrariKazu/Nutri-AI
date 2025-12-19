"""
Build SQLite database from Branded Foods CSV
Processes ~400,000 branded food products in chunks
"""

import sqlite3
import csv
import time
import os
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "FoodData_Central_branded_food_csv_2024-10-31" / "branded_food.csv"
DB_PATH = DATA_DIR / "branded_foods.db"

# Configuration
CHUNK_SIZE = 10000  # Process 10k rows at a time


def create_database():
    """Create SQLite database with schema"""
    print("Creating database schema...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS branded_foods (
            fdc_id INTEGER PRIMARY KEY,
            brand_owner TEXT,
            brand_name TEXT,
            subbrand_name TEXT,
            gtin_upc TEXT,
            ingredients TEXT,
            serving_size REAL,
            serving_size_unit TEXT,
            household_serving_fulltext TEXT,
            branded_food_category TEXT,
            data_source TEXT,
            modified_date TEXT,
            available_date TEXT,
            market_country TEXT
        )
    """)
    
    # Create indices for fast search
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_name ON branded_foods(brand_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_owner ON branded_foods(brand_owner)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subbrand ON branded_foods(subbrand_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON branded_foods(branded_food_category)")
    
    conn.commit()
    conn.close()
    
    print("✅ Database schema created")


def import_csv_data():
    """Import CSV data in chunks"""
    
    if not CSV_PATH.exists():
        print(f"❌ CSV file not found: {CSV_PATH}")
        return 0
    
    print(f"Importing data from: {CSV_PATH}")
    print(f"Chunk size: {CHUNK_SIZE} rows")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_rows = 0
    chunk = []
    
    start_time = time.time()
    
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            # Prepare row data
            chunk.append((
                int(row.get('fdc_id', 0)),
                row.get('brand_owner', ''),
                row.get('brand_name', ''),
                row.get('subbrand_name', ''),
                row.get('gtin_upc', ''),
                row.get('ingredients', ''),
                float(row.get('serving_size', 0) or 0),
                row.get('serving_size_unit', ''),
                row.get('household_serving_fulltext', ''),
                row.get('branded_food_category', ''),
                row.get('data_source', ''),
                row.get('modified_date', ''),
                row.get('available_date', ''),
                row.get('market_country', '')
            ))
            
            # Insert chunk when full
            if len(chunk) >= CHUNK_SIZE:
                cursor.executemany("""
                    INSERT OR REPLACE INTO branded_foods VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, chunk)
                conn.commit()
                
                total_rows += len(chunk)
                print(f"  Imported {total_rows:,} rows...")
                chunk = []
        
        # Insert remaining rows
        if chunk:
            cursor.executemany("""
                INSERT OR REPLACE INTO branded_foods VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, chunk)
            conn.commit()
            total_rows += len(chunk)
    
    conn.close()
    
    elapsed = time.time() - start_time
    
    return total_rows, elapsed


def get_db_size():
    """Get database file size in MB"""
    if DB_PATH.exists():
        size_bytes = DB_PATH.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    return 0


def print_summary(total_rows, elapsed):
    """Print import summary"""
    db_size = get_db_size()
    
    print("\n" + "="*60)
    print("Branded Foods Database Build Complete")
    print("="*60)
    print(f"✅ Total rows imported: {total_rows:,}")
    print(f"✅ Database size: {db_size:.2f} MB")
    print(f"✅ Time taken: {elapsed:.2f} seconds")
    print(f"✅ Database path: {DB_PATH}")
    print("="*60)


def main():
    """Main build process"""
    print("="*60)
    print("Building Branded Foods SQLite Database")
    print("="*60)
    print()
    
    # Create database
    create_database()
    
    # Import data
    total_rows, elapsed = import_csv_data()
    
    # Print summary
    print_summary(total_rows, elapsed)


if __name__ == "__main__":
    main()
