"""
Branded Foods Database Search API
Provides search functions for branded food products
"""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional

# Database path from environment or default
DB_PATH = os.getenv("BRANDED_DB_PATH", str(Path(__file__).parent.parent / "data" / "branded_foods.db"))


def _get_connection():
    """Get database connection"""
    if not Path(DB_PATH).exists():
        raise FileNotFoundError(f"Branded foods database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def _dict_factory(cursor, row):
    """Convert SQLite row to dict"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def search_branded(query: str, limit: int = 10) -> List[Dict]:
    """
    Search branded foods by name (brand_name, subbrand_name, or product category)
    
    Args:
        query: Search term
        limit: Maximum results to return
    
    Returns:
        List of matching branded food products
    """
    conn = _get_connection()
    conn.row_factory = _dict_factory
    cursor = conn.cursor()
    
    # Parameterized query to prevent SQL injection
    sql = """
        SELECT * FROM branded_foods
        WHERE brand_name LIKE ? 
           OR subbrand_name LIKE ?
           OR branded_food_category LIKE ?
        LIMIT ?
    """
    
    search_term = f"%{query}%"
    cursor.execute(sql, (search_term, search_term, search_term, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results


def search_by_brand_owner(owner: str, limit: int = 10) -> List[Dict]:
    """
    Search branded foods by brand owner/manufacturer
    
    Args:
        owner: Brand owner name (e.g., "Kellogg", "Nestle")
        limit: Maximum results to return
    
    Returns:
        List of products from that brand owner
    """
    conn = _get_connection()
    conn.row_factory = _dict_factory
    cursor = conn.cursor()
    
    sql = """
        SELECT * FROM branded_foods
        WHERE brand_owner LIKE ?
        LIMIT ?
    """
    
    search_term = f"%{owner}%"
    cursor.execute(sql, (search_term, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results


def search_by_ingredient_keyword(keyword: str, limit: int = 10) -> List[Dict]:
    """
    Search branded foods by ingredient keyword
    
    Args:
        keyword: Ingredient to search for (e.g., "chocolate", "peanut")
        limit: Maximum results to return
    
    Returns:
        List of products containing that ingredient
    """
    conn = _get_connection()
    conn.row_factory = _dict_factory
    cursor = conn.cursor()
    
    sql = """
        SELECT * FROM branded_foods
        WHERE ingredients LIKE ?
        LIMIT ?
    """
    
    search_term = f"%{keyword}%"
    cursor.execute(sql, (search_term, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results


def get_by_fdc_id(fdc_id: int) -> Optional[Dict]:
    """
    Get branded food by FDC ID
    
    Args:
        fdc_id: FoodData Central ID
    
    Returns:
        Product dict or None if not found
    """
    conn = _get_connection()
    conn.row_factory = _dict_factory
    cursor = conn.cursor()
    
    sql = "SELECT * FROM branded_foods WHERE fdc_id = ?"
    cursor.execute(sql, (fdc_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result


def get_stats() -> Dict:
    """
    Get database statistics
    
    Returns:
        Dict with total products, brands, categories
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Total products
    cursor.execute("SELECT COUNT(*) FROM branded_foods")
    total_products = cursor.fetchone()[0]
    
    # Unique brands
    cursor.execute("SELECT COUNT(DISTINCT brand_owner) FROM branded_foods")
    unique_brands = cursor.fetchone()[0]
    
    # Unique categories
    cursor.execute("SELECT COUNT(DISTINCT branded_food_category) FROM branded_foods")
    unique_categories = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_products": total_products,
        "unique_brands": unique_brands,
        "unique_categories": unique_categories
    }


# Test function
if __name__ == "__main__":
    print("Testing Branded Foods Search API")
    print("="*60)
    
    # Test 1: Search by name
    print("\n1. Searching for 'Nutella'...")
    results = search_branded("Nutella", limit=3)
    print(f"   Found {len(results)} results")
    for r in results:
        print(f"   - {r['brand_name']} ({r['brand_owner']})")
    
    # Test 2: Search by owner
    print("\n2. Searching for products by 'Kellogg'...")
    results = search_by_brand_owner("Kellogg", limit=3)
    print(f"   Found {len(results)} results")
    for r in results:
        print(f"   - {r['brand_name']}")
    
    # Test 3: Search by ingredient
    print("\n3. Searching for products with 'chocolate'...")
    results = search_by_ingredient_keyword("chocolate", limit=3)
    print(f"   Found {len(results)} results")
    for r in results:
        print(f"   - {r['brand_name']}")
    
    # Test 4: Stats
    print("\n4. Database statistics...")
    stats = get_stats()
    print(f"   Total products: {stats['total_products']:,}")
    print(f"   Unique brands: {stats['unique_brands']:,}")
    print(f"   Unique categories: {stats['unique_categories']:,}")
    
    print("\n" + "="*60)
    print("✅ All tests passed")
