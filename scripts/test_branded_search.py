"""
Test script for branded foods search functionality
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.nutrition_loader.branded_db import (
    search_branded,
    search_by_brand_owner,
    search_by_ingredient_keyword,
    get_stats
)


def test_search_nutella():
    """Test: Searching 'Nutella' returns at least 1 result"""
    print("\n1️⃣ Test: Search for 'Nutella'")
    results = search_branded("Nutella", limit=5)
    
    assert len(results) >= 1, "Expected at least 1 result for 'Nutella'"
    print(f"   ✅ Found {len(results)} results")
    
    for r in results[:3]:
        print(f"      - {r['brand_name']} ({r['brand_owner']})")
    
    return True


def test_search_nonexistent():
    """Test: Searching 'NotARealBrand' returns 0 results"""
    print("\n2️⃣ Test: Search for 'NotARealBrand'")
    results = search_branded("NotARealBrand", limit=5)
    
    assert len(results) == 0, "Expected 0 results for fake brand"
    print(f"   ✅ Found {len(results)} results (as expected)")
    
    return True


def test_partial_search():
    """Test: Searching 'Kell' returns ≥1 result (partial match)"""
    print("\n3️⃣ Test: Partial search for 'Kell'")
    results = search_branded("Kell", limit=5)
    
    assert len(results) >= 1, "Expected at least 1 result for 'Kell' (Kellogg's)"
    print(f"   ✅ Found {len(results)} results")
    
    for r in results[:3]:
        print(f"      - {r['brand_name']} ({r['brand_owner']})")
    
    return True


def test_search_by_owner():
    """Test: Search by brand owner"""
    print("\n4️⃣ Test: Search by owner 'Nestle'")
    results = search_by_brand_owner("Nestle", limit=5)
    
    assert len(results) >= 1, "Expected at least 1 Nestle product"
    print(f"   ✅ Found {len(results)} results")
    
    for r in results[:3]:
        print(f"      - {r['brand_name']}")
    
    return True


def test_search_by_ingredient():
    """Test: Search by ingredient"""
    print("\n5️⃣ Test: Search by ingredient 'chocolate'")
    results = search_by_ingredient_keyword("chocolate", limit=5)
    
    assert len(results) >= 1, "Expected at least 1 product with chocolate"
    print(f"   ✅ Found {len(results)} results")
    
    for r in results[:3]:
        print(f"      - {r['brand_name']}")
    
    return True


def test_database_stats():
    """Test: Get database statistics"""
    print("\n6️⃣ Test: Database statistics")
    stats = get_stats()
    
    assert stats['total_products'] > 0, "Expected products in database"
    print(f"   ✅ Total products: {stats['total_products']:,}")
    print(f"   ✅ Unique brands: {stats['unique_brands']:,}")
    print(f"   ✅ Unique categories: {stats['unique_categories']:,}")
    
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("Branded Foods Search Tests")
    print("="*60)
    
    tests = [
        test_search_nutella,
        test_search_nonexistent,
        test_partial_search,
        test_search_by_owner,
        test_search_by_ingredient,
        test_database_stats
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
