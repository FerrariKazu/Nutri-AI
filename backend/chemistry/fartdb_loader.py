
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FartLoader:
    def __init__(self, parquet_path: str = "data/raw/FartDB.parquet"):
        self.parquet_path = Path(parquet_path)
        self.data = None

    def load(self) -> List[Dict[str, Any]]:
        """Load FartDB data from parquet."""
        if not self.parquet_path.exists():
            logger.error(f"FartDB file not found: {self.parquet_path}")
            return []

        try:
            logger.info(f"Loading FartDB from {self.parquet_path}...")
            df = pd.read_parquet(self.parquet_path)
            
            # Simple cleaning if needed
            df = df.fillna("")
            
            # Convert to list of dicts
            records = df.to_dict('records')
            self.data = records
            logger.info(f"✅ Loaded {len(records)} FartDB records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to load FartDB: {e}")
            return []

    def get_document_text(self, record: Dict[str, Any]) -> str:
        """Convert a record to a searchable document string."""
        # Adjust fields based on actual column names. 
        # Assuming columns: Compound, Food, Odor, Intensity, etc. based on typical FartDB structure or generic fallback.
        
        # Heuristic to find relevant columns if unknown
        compound = record.get('Simple Name', record.get('Compound', 'Unknown Compound'))
        food = record.get('Food', record.get('Source', 'Unknown Source'))
        
        # Build document
        doc = f"Compound: {compound}\n"
        doc += f"Food Source: {food}\n"
        
        # Add other fields dynamically
        for k, v in record.items():
            if k not in ['Simple Name', 'Compound', 'Food', 'Source'] and v:
                doc += f"{k}: {v}\n"
                
        return doc.strip()
