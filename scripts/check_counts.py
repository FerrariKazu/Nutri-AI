import sqlite3
from pathlib import Path

base_dir = Path('vector_store')
datasets = ['recipes', 'science', 'usda_foundation', 'open_nutrition', 'chemistry', 'usda_branded']

print(f"{'Dataset':<20} | {'Status':<15} | {'Item Count':<15}")
print('-'*56)

for ds in datasets:
    db_path = base_dir / ds / 'index.meta.sqlite'
    count = 0
    status = 'Pending'
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT count(*) FROM metadata')
            res = cursor.fetchone()
            if res:
                count = res[0]
            conn.close()
            if count > 0:
                status = 'In Progress'
        except Exception as e:
            status = f'Error: {e}'
            
    if ds in ['recipes', 'science', 'usda_foundation', 'open_nutrition'] and count > 0:
        status = '✅ Complete'
    elif ds == 'chemistry' and count > 0:
        status = '🔄 Paused'
    elif ds == 'usda_branded' and count == 0:
        status = '⏸️ Queued'
        
    print(f"{ds:<20} | {status:<15} | {count:<15,}")
