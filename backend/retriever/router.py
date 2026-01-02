"""
Retrieval Router

Routes queries to the appropriate FAISS index based on query type.
Supports multi-index search and result merging.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

from .faiss_retriever import FaissRetriever

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Available isolated index types."""
    USDA_BRANDED = "usda_branded"
    USDA_FOUNDATION = "usda_foundation"
    FNDDS = "fndds"
    OPEN_NUTRITION = "open_nutrition"
    RECIPES = "recipes"
    CHEMISTRY = "chemistry"
    SCIENCE = "science"


# Default index paths (relative to project root in vector_store/)
DEFAULT_INDEX_PATHS = {
    IndexType.USDA_BRANDED: "vector_store/usda_branded/index.faiss",
    IndexType.USDA_FOUNDATION: "vector_store/usda_foundation/index.faiss",
    IndexType.FNDDS: "vector_store/fndds/index.faiss",
    IndexType.OPEN_NUTRITION: "vector_store/open_nutrition/index.faiss",
    IndexType.RECIPES: "vector_store/recipes/index.faiss",
    IndexType.CHEMISTRY: "vector_store/chemistry/index.faiss",
    IndexType.SCIENCE: "vector_store/science/index.faiss",
}


class RetrievalRouter:
    """
    Routes queries to appropriate indexes based on query analysis.
    
    Supports:
    - Single index search
    - Multi-index search with result merging
    - Query type detection for automatic routing
    """
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        index_paths: Optional[Dict[IndexType, str]] = None
    ):
        """
        Initialize router.
        
        Args:
            project_root: Project root directory (auto-detected if not provided)
            index_paths: Custom index paths (uses defaults if not provided)
        """
        if project_root is None:
            # Auto-detect project root
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        self.index_paths = index_paths or DEFAULT_INDEX_PATHS
        self.retrievers: Dict[IndexType, FaissRetriever] = {}
        
        logger.info(f"RetrievalRouter initialized at {self.project_root}")
    
    def load_index(self, index_type: IndexType) -> bool:
        """
        Load a specific index.
        
        Args:
            index_type: Type of index to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if index_type in self.retrievers:
            return True
        
        rel_path = self.index_paths.get(index_type)
        if not rel_path:
            logger.error(f"No path configured for index: {index_type}")
            return False
        
        index_path = self.project_root / rel_path
        
        if not index_path.exists():
            logger.warning(f"Index not found: {index_path}")
            return False
        
        try:
            retriever = FaissRetriever(index_path)
            retriever.load()
            self.retrievers[index_type] = retriever
            logger.info(f"Loaded index: {index_type.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to load index {index_type}: {e}")
            return False
    
    def load_all_indexes(self) -> Dict[IndexType, bool]:
        """
        Load all available indexes.
        
        Returns:
            Dict mapping index type to load success status
        """
        results = {}
        for index_type in IndexType:
            results[index_type] = self.load_index(index_type)
        return results
    
    def search(
        self,
        query: str,
        index_types: Optional[List[IndexType]] = None,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search one or more indexes.
        
        Args:
            query: Search query
            index_types: List of indexes to search (None = all loaded)
            top_k: Results per index
            min_score: Minimum score threshold
            
        Returns:
            Merged and sorted results from all queried indexes
        """
        if index_types is None:
            index_types = list(self.retrievers.keys())
        
        if not index_types:
            logger.warning("No indexes available for search")
            return []
        
        all_results = []
        
        for index_type in index_types:
            if index_type not in self.retrievers:
                if not self.load_index(index_type):
                    continue
            
            retriever = self.retrievers.get(index_type)
            if retriever is None:
                continue
            
            try:
                results = retriever.search(query, top_k=top_k, min_score=min_score)
                
                # Tag results with source index
                for r in results:
                    r['index_type'] = index_type.value
                
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search failed on {index_type}: {e}")
        
        # Sort by score descending and limit total results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return all_results[:top_k]
    
    def detect_index_type(self, query: str) -> List[IndexType]:
        """
        Detect which indexes are relevant for a query.
        
        Args:
            query: User query
            
        Returns:
            List of relevant IndexTypes
        """
        query_lower = query.lower()
        
        # Chemistry keywords
        chemistry_keywords = [
            'molecule', 'compound', 'chemical', 'reaction', 'enzyme',
            'molecular', 'formula', 'structure', 'oxidation', 'maillard',
            'flavor compound', 'volatile', 'amino acid'
        ]
        
        # Science/research keywords
        science_keywords = [
            'research', 'study', 'science', 'why does', 'how does',
            'temperature', 'cooking science', 'food science'
        ]
        
        # Nutrition keywords
        nutrition_keywords = [
            'nutrition', 'calorie', 'protein', 'vitamin', 'mineral',
            'macro', 'nutrient', 'healthy', 'diet'
        ]
        
        # Recipe keywords
        recipe_keywords = [
            'recipe', 'cook', 'make', 'prepare', 'ingredients',
            'dish', 'meal', 'dinner', 'lunch', 'breakfast'
        ]
        
        if any(kw in query_lower for kw in chemistry_keywords):
            relevant.append(IndexType.CHEMISTRY)
        
        if any(kw in query_lower for kw in science_keywords):
            relevant.append(IndexType.SCIENCE)
        
        if any(kw in query_lower for kw in nutrition_keywords):
            # For nutrition, we prioritize Branded but check Foundation if it's "raw"
            if 'raw' in query_lower or 'fresh' in query_lower:
                relevant.append(IndexType.USDA_FOUNDATION)
            else:
                relevant.append(IndexType.USDA_BRANDED)
            relevant.append(IndexType.OPEN_NUTRITION)
        
        if any(kw in query_lower for kw in recipe_keywords):
            relevant.append(IndexType.RECIPES)
        
        # LOGGING REQUIREMENT: The agent must explicitly decide which index(es) to query
        if relevant:
            logger.info(f"Explicitly routing query to: {[t.value for t in relevant]}")
        else:
            logger.warning(f"No specific index detected for query: {query}. Agent must decide.")
        
        return relevant
    
    def smart_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Automatically detect relevant indexes and search.
        
        Args:
            query: User query
            top_k: Number of results
            min_score: Minimum score threshold
            
        Returns:
            Merged results from detected indexes
        """
        index_types = self.detect_index_type(query)
        logger.info(f"Smart search detected indexes: {[t.value for t in index_types]}")
        return self.search(query, index_types, top_k, min_score)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all indexes."""
        status = {}
        for index_type in IndexType:
            if index_type in self.retrievers:
                retriever = self.retrievers[index_type]
                status[index_type.value] = {
                    'loaded': True,
                    'size': retriever.get_metadata().get('index_size', 0)
                }
            else:
                index_path = self.project_root / self.index_paths.get(index_type, '')
                status[index_type.value] = {
                    'loaded': False,
                    'exists': index_path.exists()
                }
        return status
