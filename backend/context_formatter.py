#!/usr/bin/env python3
"""
Context Formatter - Formats retrieved results into LLM-friendly context.
Manages token budgets and structures data for Qwen3:8B reasoning.
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ContextFormatter:
    """
    Formats retrieved search results into structured context
    for Qwen3:8B with token budget management.
    """
    
    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens
        # Rough estimate: 1 token ≈ 4 characters
        self.max_chars = max_tokens * 4
    
    def format_for_llm(self, search_results: Dict[str, List[Dict[str, Any]]], query: str) -> str:
        """
        Convert search results into formatted context string.
        
        Args:
            search_results: Dict from UnifiedFoodRetriever.search_all_sources()
            query: Original user query
            
        Returns:
            Formatted context string ready for LLM
        """
        context_parts = []
        context_parts.append(f"# RETRIEVED KNOWLEDGE FOR: {query}\n")
        
        # Format recipes
        if 'recipes' in search_results and search_results['recipes']:
            context_parts.append("\n## 📖 RELEVANT RECIPES:")
            for result in search_results['recipes'][:3]:
                context_parts.append(f"\n### Recipe {result['rank']} (Relevance: {result['score']:.2f})")
                context_parts.append(self._format_recipe(result))
        
        # Format nutrition data
        if 'nutrition' in search_results and search_results['nutrition']:
            context_parts.append("\n## 🥗 NUTRITIONAL DATA:")
            for result in search_results['nutrition'][:3]:
                context_parts.append(self._format_nutrition(result))
        
        # Format ingredients
        if 'ingredients' in search_results and search_results['ingredients']:
            context_parts.append("\n## 🧪 INGREDIENT INFORMATION:")
            for result in search_results['ingredients'][:3]:
                context_parts.append(self._format_ingredient(result))
        
        # Format research
        if 'research' in search_results and search_results['research']:
            context_parts.append("\n## 📚 SCIENTIFIC RESEARCH:")
            for result in search_results['research'][:2]:
                context_parts.append(self._format_research(result))
        
        # Format chemicals (DSSTox)
        if 'chemicals' in search_results and search_results['chemicals']:
            context_parts.append("\n## ⚗️ CHEMICAL DATA:")
            for result in search_results['chemicals'][:2]:
                context_parts.append(self._format_chemical(result))
        
        full_context = "\n".join(context_parts)
        
        # Truncate if needed
        if len(full_context) > self.max_chars:
            full_context = full_context[:self.max_chars] + "\n\n[Context truncated due to length...]"
            logger.warning(f"Context truncated from {len(full_context)} to {self.max_chars} chars")
        
        return full_context
    
    def _format_recipe(self, result: Dict[str, Any]) -> str:
        """Format recipe result"""
        meta = result.get('metadata', {})
        parts = []
        
        # Extract common recipe fields
        name = meta.get('name', meta.get('title', meta.get('source', 'Unknown Recipe')))
        parts.append(f"**Name:** {name}")
        
        if 'ingredients' in meta:
            parts.append(f"**Ingredients:** {str(meta['ingredients'])[:300]}")
        
        if 'instructions' in meta:
            parts.append(f"**Instructions:** {str(meta['instructions'])[:200]}...")
        
        if 'source_path' in meta:
            parts.append(f"**Source:** {meta['source_path']}")
        
        return "\n".join(parts) if parts else str(meta)[:200]
    
    def _format_nutrition(self, result: Dict[str, Any]) -> str:
        """Format nutrition result"""
        meta = result.get('metadata', {})
        
        # Try to extract key fields
        name = meta.get('name', meta.get('description', meta.get('source', 'Unknown Food')))
        source = result.get('source', 'nutrition')
        
        formatted = f"\n- **{name}** (Source: {source}, Score: {result['score']:.2f})"
        
        # Add any available nutrient data
        nutrient_keys = ['protein', 'carbohydrates', 'fat', 'fiber', 'calories', 'energy']
        nutrients_found = []
        for key in nutrient_keys:
            if key in meta:
                nutrients_found.append(f"{key.title()}: {meta[key]}")
        
        if nutrients_found:
            formatted += f"\n  {' | '.join(nutrients_found)}"
        
        return formatted
    
    def _format_ingredient(self, result: Dict[str, Any]) -> str:
        """Format ingredient/compound result"""
        meta = result.get('metadata', {})
        
        name = meta.get('name', meta.get('compound_name', 'Unknown Compound'))
        content = meta.get('content', str(meta))[:200]
        
        return f"\n- **{name}**: {content}..."
    
    def _format_research(self, result: Dict[str, Any]) -> str:
        """Format research/PDF result"""
        meta = result.get('metadata', {})
        
        source = meta.get('source_path', meta.get('source', 'Research Document'))
        page = meta.get('page', '')
        content = meta.get('content', str(meta))[:250]
        
        page_info = f" (Page {page})" if page else ""
        return f"\n- **{source}{page_info}**: {content}..."
    
    def _format_chemical(self, result: Dict[str, Any]) -> str:
        """Format chemical/DSSTox result"""
        meta = result.get('metadata', {})
        
        name = meta.get('name', meta.get('chemical_name', meta.get('casrn', 'Unknown Chemical')))
        
        return f"\n- **{name}** (Score: {result['score']:.2f})"
    
    def format_minimal(self, search_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create a minimal context string for tight token budgets.
        Just the essentials.
        """
        parts = ["# KEY RETRIEVED DATA:\n"]
        
        for source, items in search_results.items():
            if items:
                parts.append(f"\n## {source.upper()}:")
                for item in items[:2]:
                    meta = item.get('metadata', {})
                    summary = str(meta)[:100]
                    parts.append(f"- {summary}...")
        
        return "\n".join(parts)
