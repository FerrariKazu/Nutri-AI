"""
T1: Test Retrieval Expansion — Taste Ontology
Verifies that taste queries trigger correct ontology expansions.
"""
import pytest
from backend.src.services.query_decomposer import QueryDecomposer


class TestTasteExpansion:
    """Feature 1-3: Taste ontology + activation rule + decomposition."""

    def test_bitter_query_expands_to_alkaloid_tannin_polyphenol(self):
        """F1+F2: 'bitter' directly activates taste expansion."""
        result = QueryDecomposer.decompose("bitter foods")
        assert any("alkaloid" in r for r in result), f"Expected 'alkaloid' in {result}"
        assert any("tannin" in r for r in result), f"Expected 'tannin' in {result}"
        assert any("polyphenol" in r for r in result), f"Expected 'polyphenol' in {result}"

    def test_sour_query_with_flavor_keyword(self):
        """F2: 'flavor' activation word + 'sour' taste key."""
        result = QueryDecomposer.decompose("sour flavor profile")
        assert any("citric acid" in r for r in result), f"Expected 'citric acid' in {result}"

    def test_umami_query_expands(self):
        """F1: umami taste ontology terms."""
        result = QueryDecomposer.decompose("umami taste compounds")
        assert any("glutamate" in r for r in result), f"Expected 'glutamate' in {result}"

    def test_sweet_direct_activation(self):
        """F2: Direct taste-keyword activation (no 'taste' or 'flavor' word needed)."""
        result = QueryDecomposer.decompose("sweet compounds in fruit")
        assert any("sucrose" in r for r in result) or any("glucose" in r for r in result), \
            f"Expected sugar terms in {result}"

    def test_max_5_subqueries_enforced(self):
        """F3: Global 5-query limit even with many expansions."""
        result = QueryDecomposer.decompose("bitter and sour taste compounds with antioxidant")
        assert len(result) <= 5, f"Expected <=5 subqueries, got {len(result)}: {result}"

    def test_scientific_ontology_still_works(self):
        """Existing behavior: scientific keys like 'protein' still expand."""
        result = QueryDecomposer.decompose("protein denaturation")
        assert any("amino acid" in r for r in result) or any("denaturation" in r for r in result), \
            f"Expected scientific expansion in {result}"
