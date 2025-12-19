"""
BM25 Lexical Search for Keyword-Based Retrieval

Implements lightweight BM25 using rank_bm25 package.
Indexes recipes from processed/recipes_with_nutrition.json.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Search:
    """BM25 lexical search engine."""
    
    def __init__(self, recipes_path: str = "processed/recipes_with_nutrition.json"):
        self.recipes_path = Path(recipes_path)
        self.recipes = []
        self.bm25 = None
        self.tokenized_corpus = []
        
        if self.recipes_path.exists():
            self._load_and_index()
        else:
            logger.warning(f"Recipes file not found: {self.recipes_path}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase and split."""
        return text.lower().split()
    
    def _load_and_index(self):
        """Load recipes and build BM25 index."""
        logger.info(f"Loading recipes from {self.recipes_path}...")
        
        try:
            with open(self.recipes_path, 'r', encoding='utf-8') as f:
                self.recipes = json.load(f)
            
            logger.info(f"✓ Loaded {len(self.recipes)} recipes")
            
            # Tokenize corpus (title + ingredients + instructions)
            self.tokenized_corpus = []
            for recipe in self.recipes:
                # Combine searchable fields
                text = " ".join([
                    recipe.get('title', ''),
                    recipe.get('ingredients', ''),
                    recipe.get('instructions', ''),
                    " ".join(recipe.get('tags', []))
                ])
                tokens = self._tokenize(text)
                self.tokenized_corpus.append(tokens)
            
            # Build BM25 index
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"✓ BM25 index built for {len(self.tokenized_corpus)} documents")
        
        except Exception as e:
            logger.error(f"Failed to load/index recipes: {e}")
            self.recipes = []
            self.bm25 = None
    
    def lexical_search(self, query: str, k: int = 10) -> List[Dict]:
        """
        Perform BM25 lexical search.
        
        Args:
            query: Search query
            k: Number of results to return
        
        Returns:
            List of dicts with 'id', 'text', 'score', 'title'
        """
        if not self.bm25:
            logger.warning("BM25 index not available")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                recipe = self.recipes[idx]
                
                # Combine text for snippet extraction
                text = f"{recipe.get('title', '')}. "
                text += recipe.get('instructions', '')
                
                results.append({
                    'id': recipe.get('id', f"recipe_{idx}"),
                    'title': recipe.get('title', 'Untitled Recipe'),
                    'text': text,
                    'score': float(scores[idx]),
                    'source': 'lexical',
                    'recipe': recipe  # Include full recipe for later use
                })
        
        return results


# Global BM25 instance (lazy loaded)
_bm25_search: Optional[BM25Search] = None


def get_bm25_search() -> BM25Search:
    """Get or create global BM25 search instance."""
    global _bm25_search
    if _bm25_search is None:
        _bm25_search = BM25Search()
    return _bm25_search


def lexical_search(query: str, k: int = 10) -> List[Dict]:
    """
    Convenience function for BM25 search.
    
    Args:
        query: Search query
        k: Number of results to return
    
    Returns:
        List of search results
    """
    bm25 = get_bm25_search()
    return bm25.lexical_search(query, k)


if __name__ == "__main__":
    # Simple test
    test_query = "chicken pasta"
    results = lexical_search(test_query, k=5)
    
    print(f"BM25 Search Test: '{test_query}'")
    print(f"Found {len(results)} results:\n")
    
    for i, res in enumerate(results, 1):
        print(f"{i}. [Score: {res['score']:.2f}] {res['title']}")
        print(f"   {res['text'][:100]}...\n")
