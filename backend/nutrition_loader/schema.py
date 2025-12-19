"""
Unified schema for food and compound data.

This module defines the Pydantic models used throughout the two-tier RAG system.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime


class UnifiedFood(BaseModel):
    """
    Unified food/compound record schema.
    
    This model is used for all data sources (FDC, FooDB, FartDB, DSSTox)
    to provide a consistent interface for indexing and retrieval.
    """
    
    uuid: UUID = Field(default_factory=uuid4, description="Stable universal identifier")
    native_id: Optional[str] = Field(None, description="Original dataset ID (e.g., FDC ID)")
    source: str = Field(..., description="Data source (FDC_Foundation, FooDB, etc.)")
    name: str = Field(..., description="Primary name/title")
    normalized_name: str = Field(..., description="Normalized version for matching")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    
    # Nutritional data (per 100g where applicable)
    nutrients: Dict[str, float] = Field(
        default_factory=dict,
        description="Nutrient values: calories, protein_g, fat_g, carbs_g, fiber_g, etc."
    )
    
    # Chemical/compound data
    compounds: Dict[str, Any] = Field(
        default_factory=dict,
        description="Linked chemical compounds with properties"
    )
    
    # Toxicity data (primarily from DSSTox)
    toxicity: Dict[str, Any] = Field(
        default_factory=dict,
        description="Toxicity metrics and safety information"
    )
    
    # Additional fields
    description: Optional[str] = Field(None, description="Text description or summary")
    category: Optional[str] = Field(None, description="Food category or type")
    serving_size: Optional[str] = Field(None, description="Typical serving size")
    
    # Raw data for debugging and completeness
    raw: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original raw data from source"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
        
    def to_search_text(self) -> str:
        """
        Generate searchable text representation for embedding.
        
        Returns:
            Combined text including name, synonyms, description, and key nutrients
        """
        parts = [
            self.name,
            self.normalized_name,
            " ".join(self.synonyms[:5]),  # Limit synonyms
        ]
        
        if self.description:
            # Truncate description to avoid too long text
            desc = self.description[:500]
            parts.append(desc)
        
        # Add category
        if self.category:
            parts.append(self.category)
        
        # Add key nutrients as context
        if self.nutrients:
            nutrient_str = " ".join([
                f"{k}:{v:.1f}" for k, v in list(self.nutrients.items())[:8]
            ])
            parts.append(nutrient_str)
        
        # Add compound names if present
        if self.compounds:
            compound_names = [
                str(v.get('name', '')) 
                for v in (self.compounds.values() if isinstance(self.compounds, dict) else [])
            ]
            parts.extend(compound_names[:3])
        
        return " ".join(filter(None, parts))
    
    def to_display_dict(self) -> Dict[str, Any]:
        """
        Generate dictionary for API responses.
        
        Returns:
            Serializable dict with key fields
        """
        return {
            "uuid": str(self.uuid),
            "native_id": self.native_id,
            "source": self.source,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "synonyms": self.synonyms[:10],
            "nutrients": self.nutrients,
            "compounds": self.compounds,
            "toxicity": self.toxicity,
            "description": self.description[:300] if self.description else None,
            "category": self.category,
        }


class CompoundRecord(BaseModel):
    """
    Compound/chemical record (subset of UnifiedFood or standalone).
    
    Used for PubChem entries and toxicity data.
    """
    
    uuid: UUID = Field(default_factory=uuid4)
    cid: Optional[int] = Field(None, description="PubChem Compound ID")
    name: str
    normalized_name: str
    synonyms: List[str] = Field(default_factory=list)
    
    # Chemical properties
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    
    # Computed properties
    xlogp3: Optional[float] = None
    h_bond_donors: Optional[int] = None
    h_bond_acceptors: Optional[int] = None
    rotatable_bonds: Optional[int] = None
    tpsa: Optional[float] = None
    
    # Safety/toxicity
    toxicity: Dict[str, Any] = Field(default_factory=dict)
    
    # Description
    description: Optional[str] = None
    
    # Metadata
    source: str = "Unknown"
    raw: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_search_text(self) -> str:
        """Generate searchable text for embedding."""
        parts = [
            self.name,
            self.normalized_name,
            " ".join(self.synonyms[:5]),
        ]
        
        if self.molecular_formula:
            parts.append(f"formula:{self.molecular_formula}")
        
        if self.description:
            parts.append(self.description[:400])
        
        # Add property info
        if self.xlogp3 is not None:
            parts.append(f"logP:{self.xlogp3:.2f}")
        
        if self.toxicity:
            tox_str = " ".join([f"{k}:{v}" for k, v in list(self.toxicity.items())[:3]])
            parts.append(tox_str)
        
        return " ".join(filter(None, parts))
