"""
Test Suite: Scientific Ontology Query Decomposition
Validates decompose_query expands scientific terms correctly
and leaves non-scientific queries unchanged.
"""

import pytest
from backend.retriever.retrieval_utils import decompose_query, ION_ONTOLOGY


class TestDecomposeQuery:
    """Tests for ontology-based query expansion."""

    def test_sodium_expansion(self):
        """Sodium query should be expanded with all sodium ontology terms."""
        result = decompose_query("sodium channel function")

        assert result[0] == "sodium channel function"  # Original first
        assert "sodium ion transport" in result
        assert "Na+ transport" in result
        assert "sodium potassium ATPase" in result
        assert "renal sodium reabsorption" in result
        assert "intestinal sodium absorption" in result

    def test_calcium_expansion(self):
        """Calcium query should match calcium ontology terms."""
        result = decompose_query("calcium signaling pathway")

        assert result[0] == "calcium signaling pathway"
        assert "Ca2+ flux" in result
        assert "calbindin" in result
        assert "calcium-sensing receptor" in result

    def test_glucose_expansion(self):
        """Glucose query should expand to Maillard/glycemic terms."""
        result = decompose_query("glucose metabolism")

        assert result[0] == "glucose metabolism"
        assert "Maillard reaction" in result
        assert "blood glucose regulation" in result
        assert "glycemic index" in result

    def test_no_expansion_for_generic_query(self):
        """Non-scientific queries should return only the original query."""
        result = decompose_query("hello world")

        assert result == ["hello world"]

    def test_no_expansion_for_unmatched_term(self):
        """Queries without ontology keys should not be expanded."""
        result = decompose_query("protein folding mechanism")

        assert result == ["protein folding mechanism"]

    def test_deduplication(self):
        """Expansions should not contain duplicate terms."""
        # "oxidation" and "antioxidant" share terms in the ontology
        result = decompose_query("antioxidant oxidation defense")

        # Count all items
        assert len(result) == len(set(result)), f"Duplicates found: {result}"

    def test_multiple_keys_compound_query(self):
        """A query containing multiple ontology keys should expand all."""
        result = decompose_query("sodium and calcium interaction")

        # Should have original + sodium terms + calcium terms
        assert result[0] == "sodium and calcium interaction"
        assert "Na+ transport" in result
        assert "Ca2+ flux" in result
        assert len(result) > 5  # Original + both expansions

    def test_case_insensitive_matching(self):
        """Ontology matching should be case-insensitive."""
        result = decompose_query("SODIUM transport mechanism")

        assert len(result) > 1  # Should still match "sodium" key
        assert "sodium ion transport" in result

    def test_original_query_always_first(self):
        """The original query must always be the first element."""
        for query in ["sodium test", "calcium test", "hello world"]:
            result = decompose_query(query)
            assert result[0] == query

    def test_ontology_registry_coverage(self):
        """Every key in ION_ONTOLOGY should trigger expansion."""
        for key in ION_ONTOLOGY:
            result = decompose_query(f"test {key} query")
            assert len(result) > 1, f"Key '{key}' did not trigger expansion"
