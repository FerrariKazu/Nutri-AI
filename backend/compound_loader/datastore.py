"""
Persistent cache for PubChem data using SQLite + JSON backup.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from uuid import uuid4
from datetime import datetime

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DB_PATH = "backend/compound_loader/pubchem_cache.sqlite"
DEFAULT_JSON_PATH = "backend/compound_loader/pubchem_cache.json"


class CompoundDatastore:
    """SQLite-backed compound cache with JSON mirror."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH, json_path: str = DEFAULT_JSON_PATH):
        """
        Initialize datastore.
        
        Args:
            db_path: Path to SQLite database
            json_path: Path to JSON backup file
        """
        self.db_path = Path(db_path)
        self.json_path = Path(json_path)
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.init_db()
    
    def init_db(self) -> None:
        """Create database and tables if they don't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pubchem_cache (
                uuid TEXT PRIMARY KEY,
                name TEXT,
                cid INTEGER,
                json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON pubchem_cache(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cid ON pubchem_cache(cid)")
        
        self.conn.commit()
        logger.info(f"Initialized compound datastore at {self.db_path}")
    
    def get_by_name(self, name: str) -> Optional[Dict]:
        """
        Retrieve compound by name.
        
        Args:
            name: Compound name (case-insensitive)
            
        Returns:
            Compound dict or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM pubchem_cache WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (name,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'uuid': row['uuid'],
                'name': row['name'],
                'cid': row['cid'],
                'data': json.loads(row['json']),
                'created_at': row['created_at']
            }
        return None
    
    def get_by_cid(self, cid: int) -> Optional[Dict]:
        """
        Retrieve compound by PubChem CID.
        
        Args:
            cid: PubChem Compound ID
            
        Returns:
            Compound dict or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM pubchem_cache WHERE cid = ? LIMIT 1",
            (cid,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'uuid': row['uuid'],
                'name': row['name'],
                'cid': row['cid'],
                'data': json.loads(row['json']),
                'created_at': row['created_at']
            }
        return None
    
    def save_compound(self, name: str, cid: int, data: Dict) -> str:
        """
        Save compound to cache.
        
        Args:
            name: Compound name
            cid: PubChem CID
            data: Compound data dictionary
            
        Returns:
            UUID of saved record
        """
        compound_uuid = str(uuid4())
        json_str = json.dumps(data, ensure_ascii=False)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO pubchem_cache (uuid, name, cid, json)
               VALUES (?, ?, ?, ?)""",
            (compound_uuid, name, cid, json_str)
        )
        self.conn.commit()
        
        # Update JSON backup
        self._update_json_backup()
        
        logger.info(f"Saved compound '{name}' (CID: {cid}) with UUID {compound_uuid}")
        return compound_uuid
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        List all cached compounds with pagination.
        
        Args:
            limit: Max results
            offset: Offset for pagination
            
        Returns:
            List of compound dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM pubchem_cache ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'uuid': row['uuid'],
                'name': row['name'],
                'cid': row['cid'],
                'data': json.loads(row['json']),
                'created_at': row['created_at']
            })
        
        return results
    
    def count(self) -> int:
        """Get total count of cached compounds."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pubchem_cache")
        return cursor.fetchone()[0]
    
    def _update_json_backup(self) -> None:
        """Mirror SQLite to JSON file for portability."""
        try:
            all_compounds = self.list_all(limit=10000)  # Limit to avoid huge files
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(all_compounds, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to update JSON backup: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed compound datastore")


# Global instance
_datastore: Optional[CompoundDatastore] = None


def get_datastore() -> CompoundDatastore:
    """Get or create global datastore instance."""
    global _datastore
    if _datastore is None:
        _datastore = CompoundDatastore()
    return _datastore
