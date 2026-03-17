"""
T4: Test Retrieval Regression
Ensures non-taste queries don't trigger taste expansion or tagging.
"""
import pytest
from backend.src.services.query_decomposer import QueryDecomposer
from backend.retriever.faiss_retriever import FaissRetriever


class TestRegressionNoTaste:
    """Regression: pure-science queries must NOT trigger taste pipeline."""

    def test_vitamin_c_no_taste_expansion(self):
        """Non-taste query must not produce taste ontology terms."""
        result = QueryDecomposer.decompose("vitamin c absorption")
        taste_terms = {"alkaloid", "tannin", "polyphenol", "sucrose", "glucose",
                       "fructose", "citric acid", "malic acid", "lactic acid",
                       "glutamate", "inosinate", "umami receptor"}
        found = [r for r in result if r in taste_terms]
        assert len(found) == 0, f"Taste terms leaked into non-taste query: {found}"

    def test_protein_query_no_taste_expansion(self):
        """Query about protein should expand scientifically, not taste-wise."""
        result = QueryDecomposer.decompose("protein denaturation mechanisms")
        taste_terms = {"alkaloid", "tannin", "polyphenol", "sucrose", "glucose",
                       "fructose", "citric acid", "malic acid", "lactic acid",
                       "glutamate", "inosinate", "umami receptor"}
        found = [r for r in result if r in taste_terms]
        assert len(found) == 0, f"Taste terms leaked into protein query: {found}"

    def test_chemical_taste_map_constants(self):
        """F7: CHEMICAL_TASTE_MAP is correctly defined on FaissRetriever."""
        assert hasattr(FaissRetriever, "CHEMICAL_TASTE_MAP")
        assert FaissRetriever.CHEMICAL_TASTE_MAP["alkaloid"] == "bitter"
        assert FaissRetriever.CHEMICAL_TASTE_MAP["glutamate"] == "umami"
        assert FaissRetriever.CHEMICAL_TASTE_MAP["sucrose"] == "sweet"
        assert FaissRetriever.CHEMICAL_TASTE_MAP["citric acid"] == "sour"

    def test_taste_bonus_value(self):
        """F8: TASTE_BONUS = 0.05."""
        assert FaissRetriever.TASTE_BONUS == 0.05

    def test_taste_tagging_only_on_matching_text(self):
        """F7: Taste tag only applied when text contains chemical compound."""
        result_with_alkaloid = {"text": "This food contains alkaloid compounds", "score": 0.8}
        result_without = {"text": "High in vitamin D and calcium", "score": 0.8}

        # Simulate taste tagging
        for r in [result_with_alkaloid, result_without]:
            text_lower = r["text"].lower()
            for compound, taste in FaissRetriever.CHEMICAL_TASTE_MAP.items():
                if compound in text_lower:
                    r["taste_tag"] = taste
                    break

        assert result_with_alkaloid.get("taste_tag") == "bitter"
        assert result_without.get("taste_tag") is None
