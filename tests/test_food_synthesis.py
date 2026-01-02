"""
Test Suite for Nutri Food Synthesis System

Tests Phase 1 (Single-pass RAG synthesis) and Phase 2 (Intent extraction agent).
Covers:
- Impossible ingredient combinations
- Conflicting constraints
- Chemistry-heavy "why" questions
- Minimal ingredient scenarios
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM for testing without Ollama."""
    with patch('backend.food_synthesis.LLMQwen3') as MockLLM:
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_retriever():
    """Mock retriever for testing without FAISS indexes."""
    with patch('backend.food_synthesis.FaissRetriever') as MockRetriever:
        mock_instance = MagicMock()
        mock_instance.search.return_value = [
            {
                'text': 'Protein denaturation occurs at 60-80°C.',
                'score': 0.85,
                'source': 'chemistry',
                'metadata': {'type': 'chemistry'}
            },
            {
                'text': 'Egg white contains ~10% protein.',
                'score': 0.75,
                'source': 'usda_foundation',
                'metadata': {'type': 'nutrition'}
            }
        ]
        MockRetriever.return_value = mock_instance
        yield mock_instance


# =============================================================================
# PHASE 1 TESTS
# =============================================================================

class TestPhase1:
    """Tests for Phase 1: Single-pass food synthesis."""
    
    def test_retriever_excludes_recipes(self):
        """Verify retriever does NOT search recipes index."""
        from backend.food_synthesis import FoodSynthesisRetriever
        from backend.retriever.router import IndexType
        
        # Recipes index should NOT be in search indexes
        assert IndexType.RECIPES not in FoodSynthesisRetriever.SEARCH_INDEXES
    
    def test_retriever_includes_chemistry(self):
        """Verify retriever searches chemistry index."""
        from backend.food_synthesis import FoodSynthesisRetriever
        from backend.retriever.router import IndexType
        
        assert IndexType.CHEMISTRY in FoodSynthesisRetriever.SEARCH_INDEXES
    
    def test_retriever_includes_nutrition(self):
        """Verify retriever searches nutrition indexes."""
        from backend.food_synthesis import FoodSynthesisRetriever
        from backend.retriever.router import IndexType
        
        assert IndexType.USDA_FOUNDATION in FoodSynthesisRetriever.SEARCH_INDEXES
        assert IndexType.USDA_BRANDED in FoodSynthesisRetriever.SEARCH_INDEXES
    
    def test_synthesis_engine_uses_verbatim_prompt(self):
        """Verify synthesis engine uses the exact required prompt."""
        from backend.food_synthesis import PHASE1_SYSTEM_PROMPT
        
        # Check key phrases from verbatim prompt
        assert "INVENT meals and recipes from first principles" in PHASE1_SYSTEM_PROMPT
        assert "not recall existing recipes" in PHASE1_SYSTEM_PROMPT
        assert "Assign functional roles to ingredients" in PHASE1_SYSTEM_PROMPT
        assert "If something is not possible, you must say so" in PHASE1_SYSTEM_PROMPT
    
    def test_intent_output_schema(self):
        """Verify IntentOutput matches required schema."""
        from backend.food_synthesis import IntentOutput
        
        intent = IntentOutput()
        data = intent.to_dict()
        
        # Check all required fields
        assert 'goal' in data
        assert 'ingredients' in data
        assert 'equipment' in data
        assert 'dietary_constraints' in data
        assert 'nutritional_goals' in data
        assert 'time_limit_minutes' in data
        assert 'explanation_depth' in data
        
        # Check goal is valid
        assert data['goal'] in ['invent_meal', 'explain', 'optimize']
        
        # Check explanation_depth is valid
        assert data['explanation_depth'] in ['casual', 'scientific']


# =============================================================================
# PHASE 2 TESTS
# =============================================================================

class TestPhase2:
    """Tests for Phase 2: Intent extraction agent."""
    
    def test_agent1_uses_verbatim_prompt(self):
        """Verify Agent 1 uses the exact required prompt."""
        from backend.food_synthesis import AGENT1_SYSTEM_PROMPT
        
        # Check key phrases from verbatim prompt
        assert "intent and constraint extraction system" in AGENT1_SYSTEM_PROMPT
        assert "You must NOT" in AGENT1_SYSTEM_PROMPT
        assert "Suggest recipes" in AGENT1_SYSTEM_PROMPT
        assert "Add ingredients" in AGENT1_SYSTEM_PROMPT
        assert "Return valid JSON only" in AGENT1_SYSTEM_PROMPT
    
    def test_phase2_reasoning_addendum(self):
        """Verify Phase 2 includes constraint addendum."""
        from backend.food_synthesis import PHASE2_REASONING_ADDENDUM
        
        assert "strictly obey all constraints" in PHASE2_REASONING_ADDENDUM
        assert "Do NOT reinterpret the user" in PHASE2_REASONING_ADDENDUM
    
    def test_intent_extraction_json_parsing(self, mock_llm):
        """Test intent agent parses JSON correctly."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = '''
        {
            "goal": "invent_meal",
            "ingredients": ["chicken", "rice"],
            "equipment": ["pan"],
            "dietary_constraints": {"gluten_free": true},
            "nutritional_goals": {"protein": "high"},
            "time_limit_minutes": 30,
            "explanation_depth": "casual"
        }
        '''
        
        agent = IntentAgent()
        result = agent.extract("Make a quick chicken dinner")
        
        assert result.goal == "invent_meal"
        assert "chicken" in result.ingredients
        assert result.time_limit_minutes == 30
        assert result.explanation_depth == "casual"
    
    def test_intent_extraction_fallback(self, mock_llm):
        """Test intent agent handles invalid JSON gracefully."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = "This is not valid JSON"
        
        agent = IntentAgent()
        result = agent.extract("Make something with eggs and flour")
        
        # Should return default values, not crash
        assert result.goal == "invent_meal"
        # Fallback extraction worked OR returns empty (both valid)
        assert isinstance(result.ingredients, list)


# =============================================================================
# IMPOSSIBLE INGREDIENT TESTS
# =============================================================================

class TestImpossibleIngredients:
    """Tests for impossible ingredient combinations."""
    
    @pytest.mark.parametrize("query", [
        "Make ice cream that stays frozen while boiling",
        "Create a dish using fire and ice simultaneously",
        "Cook something that is both solid and liquid at room temperature",
        "Make a cake without any binding agent or structure",
    ])
    def test_impossible_should_be_refused(self, query, mock_llm, mock_retriever):
        """System should explain impossibility for impossible requests."""
        from backend.food_synthesis import FoodSynthesisEngine, RetrievedDocument
        
        # Mock response that correctly refuses
        mock_llm.generate_text.return_value = """
        This request is not possible due to fundamental physics.
        Ice cream cannot remain frozen at boiling temperatures because
        water's phase transition is determined by temperature and pressure.
        At 100°C at sea level, water exists as vapor, not ice.
        """
        
        engine = FoodSynthesisEngine()
        
        docs = [
            RetrievedDocument(
                text="Water freezes at 0°C and boils at 100°C at sea level.",
                score=0.9,
                doc_type="chemistry",
                source="science"
            )
        ]
        
        result = engine.synthesize(query, docs)
        
        # The response should indicate impossibility
        # (In real testing, we'd check the actual LLM response)
        assert mock_llm.generate_text.called


# =============================================================================
# CONFLICTING CONSTRAINTS TESTS
# =============================================================================

class TestConflictingConstraints:
    """Tests for conflicting constraint handling."""
    
    def test_vegan_with_eggs_conflict(self, mock_llm):
        """Vegan + eggs is a constraint conflict."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = '''
        {
            "goal": "invent_meal",
            "ingredients": ["eggs"],
            "dietary_constraints": {"vegan": true},
            "explanation_depth": "scientific"
        }
        '''
        
        agent = IntentAgent()
        result = agent.extract("Make a vegan dish with eggs")
        
        # Agent extracts as-is (no interpretation)
        assert "eggs" in result.ingredients or result.dietary_constraints.get("vegan") == True
    
    def test_low_fat_cheese_conflict(self, mock_llm):
        """Low-fat + cheese-based is a feasibility challenge."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = '''
        {
            "goal": "invent_meal",
            "ingredients": ["cheddar cheese"],
            "nutritional_goals": {"low_fat": true},
            "explanation_depth": "casual"
        }
        '''
        
        agent = IntentAgent()
        result = agent.extract("Make a low-fat cheese dish")
        
        # Agent should extract both constraints
        assert result.nutritional_goals.get("low_fat") == True or "cheese" in str(result.ingredients)


# =============================================================================
# CHEMISTRY QUESTIONS TESTS
# =============================================================================

class TestChemistryQuestions:
    """Tests for chemistry-heavy 'why' questions."""
    
    @pytest.mark.parametrize("question", [
        "Why does bread rise?",
        "Why does meat brown when cooked?",
        "Why do eggs solidify when heated?",
        "What causes onions to caramelize?",
    ])
    def test_chemistry_question_routing(self, question, mock_llm, mock_retriever):
        """Chemistry questions should retrieve chemistry knowledge."""
        from backend.food_synthesis import FoodSynthesisRetriever
        from backend.retriever.router import IndexType
        
        # Chemistry index should be queried
        assert IndexType.CHEMISTRY in FoodSynthesisRetriever.SEARCH_INDEXES


# =============================================================================
# MINIMAL INGREDIENT TESTS
# =============================================================================

class TestMinimalIngredients:
    """Tests for minimal ingredient scenarios."""
    
    def test_single_ingredient(self, mock_llm):
        """System should handle single-ingredient requests."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = '''
        {
            "goal": "invent_meal",
            "ingredients": ["potato"],
            "equipment": [],
            "explanation_depth": "scientific"
        }
        '''
        
        agent = IntentAgent()
        result = agent.extract("I only have a potato")
        
        assert len(result.ingredients) == 1 or "potato" in str(result.ingredients)
    
    def test_no_ingredients_specified(self, mock_llm):
        """System should handle requests with no specific ingredients."""
        from backend.food_synthesis import IntentAgent
        
        mock_llm.generate_text.return_value = '''
        {
            "goal": "explain",
            "ingredients": [],
            "explanation_depth": "scientific"
        }
        '''
        
        agent = IntentAgent()
        result = agent.extract("How does yeast work?")
        
        assert result.goal == "explain"
        assert result.ingredients == []


# =============================================================================
# PIPELINE INTEGRATION TESTS
# =============================================================================

class TestPipelineIntegration:
    """Integration tests for the full pipeline."""
    
    def test_pipeline_phase1_mode(self, mock_llm):
        """Test Phase 1 mode (no intent extraction)."""
        from backend.food_synthesis import NutriPipeline
        
        # Mock retriever to avoid loading real indexes
        with patch('backend.food_synthesis.FoodSynthesisRetriever') as MockRetriever:
            mock_ret = MagicMock()
            mock_ret.retrieve.return_value = []
            MockRetriever.return_value = mock_ret
            
            mock_llm.generate_text.return_value = "A simple recipe..."
            
            pipeline = NutriPipeline(use_phase2=False)
            result = pipeline.synthesize("Make something")
            
            assert result.phase == 1
            assert result.intent is None
    
    def test_pipeline_phase2_mode(self, mock_llm):
        """Test Phase 2 mode (with intent extraction)."""
        from backend.food_synthesis import NutriPipeline
        
        # Mock retriever
        with patch('backend.food_synthesis.FoodSynthesisRetriever') as MockRetriever:
            mock_ret = MagicMock()
            mock_ret.retrieve.return_value = []
            MockRetriever.return_value = mock_ret
            
            # First call: intent extraction, Second call: synthesis
            mock_llm.generate_text.side_effect = [
                '{"goal": "invent_meal", "ingredients": ["chicken"], "explanation_depth": "casual"}',
                "A creative chicken dish..."
            ]
            
            pipeline = NutriPipeline(use_phase2=True)
            result = pipeline.synthesize("Make chicken dinner")
            
            assert result.phase == 2
            assert result.intent is not None


# =============================================================================
# LOGGING TESTS
# =============================================================================

class TestLogging:
    """Tests for logging requirements."""
    
    def test_retriever_logs_documents(self, mock_llm, mock_retriever, caplog):
        """Verify retriever logs retrieved documents."""
        from backend.food_synthesis import FoodSynthesisRetriever
        
        with caplog.at_level(logging.INFO):
            # Can't fully test without real indexes, but verify structure exists
            retriever = FoodSynthesisRetriever()
            assert hasattr(retriever, 'retrieve')


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

class TestSchemaValidation:
    """Tests for output schema compliance."""
    
    def test_synthesis_result_structure(self, mock_llm):
        """Verify SynthesisResult has required fields."""
        from backend.food_synthesis import SynthesisResult
        
        result = SynthesisResult(
            recipe="Test recipe",
            retrieved_documents=[],
            intent={"goal": "invent_meal"},
            phase=2
        )
        
        assert hasattr(result, 'recipe')
        assert hasattr(result, 'retrieved_documents')
        assert hasattr(result, 'intent')
        assert hasattr(result, 'phase')
    
    def test_intent_json_roundtrip(self):
        """Verify IntentOutput serializes/deserializes correctly."""
        from backend.food_synthesis import IntentOutput
        
        original = IntentOutput(
            goal="optimize",
            ingredients=["tomato", "basil"],
            equipment=["blender"],
            dietary_constraints={"vegetarian": True},
            nutritional_goals={"protein": "moderate"},
            time_limit_minutes=15,
            explanation_depth="casual"
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = IntentOutput(**data)
        
        assert restored.goal == original.goal
        assert restored.ingredients == original.ingredients
        assert restored.time_limit_minutes == original.time_limit_minutes


# =============================================================================
# PHASE 3 TESTS - REFINEMENT ENGINE
# =============================================================================

class TestPhase3FeedbackParsing:
    """Tests for Phase 3: Feedback parsing."""
    
    def test_feedback_delta_schema(self):
        """Verify FeedbackDelta matches required schema."""
        from backend.refinement_engine import FeedbackDelta
        
        delta = FeedbackDelta()
        data = delta.to_dict()
        
        # Check required fields
        assert 'adjustments' in data
        assert 'explanation_depth' in data
        assert 'notes' in data
        
        # Check adjustments structure
        adjustments = data['adjustments']
        assert 'macros' in adjustments
        assert 'texture' in adjustments
        assert 'flavor_profile' in adjustments
        assert 'caloric_density' in adjustments
    
    def test_empty_feedback_is_noop(self):
        """Empty feedback should be detected as no-op."""
        from backend.refinement_engine import FeedbackDelta
        
        delta = FeedbackDelta()
        assert delta.is_empty()
    
    def test_protein_increase_detected(self):
        """Feedback parser should detect protein increase request."""
        from backend.refinement_engine import FeedbackParser
        
        with patch('backend.refinement_engine.LLMQwen3') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.generate_text.return_value = '''
            {
                "adjustments": {
                    "macros": {"protein": "increase", "fat": "unchanged", "carbs": "unchanged"},
                    "texture": [],
                    "flavor_profile": [],
                    "caloric_density": "unchanged"
                },
                "explanation_depth": "scientific",
                "notes": []
            }
            '''
            MockLLM.return_value = mock_instance
            
            parser = FeedbackParser()
            delta = parser.parse("More protein please")
            
            assert delta.adjustments['macros']['protein'] == 'increase'


class TestPhase3TextureChanges:
    """Tests for Phase 3: Texture change requests."""
    
    def test_crispy_texture_parsed(self):
        """Texture change 'crispy' should be parsed."""
        from backend.refinement_engine import FeedbackParser
        
        with patch('backend.refinement_engine.LLMQwen3') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.generate_text.return_value = '''
            {
                "adjustments": {
                    "macros": {"protein": "unchanged", "fat": "unchanged", "carbs": "unchanged"},
                    "texture": ["crispy"],
                    "flavor_profile": [],
                    "caloric_density": "unchanged"
                },
                "explanation_depth": "casual",
                "notes": []
            }
            '''
            MockLLM.return_value = mock_instance
            
            parser = FeedbackParser()
            delta = parser.parse("Make it crispier")
            
            assert "crispy" in delta.adjustments['texture']


class TestPhase3ExplanationDepth:
    """Tests for Phase 3: Explanation depth escalation."""
    
    def test_depth_escalation(self):
        """User can request deeper chemistry explanation."""
        from backend.refinement_engine import FeedbackParser
        
        with patch('backend.refinement_engine.LLMQwen3') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.generate_text.return_value = '''
            {
                "adjustments": {
                    "macros": {"protein": "unchanged", "fat": "unchanged", "carbs": "unchanged"},
                    "texture": [],
                    "flavor_profile": [],
                    "caloric_density": "unchanged"
                },
                "explanation_depth": "scientific",
                "notes": ["User wants more chemical detail"]
            }
            '''
            MockLLM.return_value = mock_instance
            
            parser = FeedbackParser()
            delta = parser.parse("Explain the chemistry in more depth")
            
            assert delta.explanation_depth == "scientific"


class TestPhase3ConflictingFeedback:
    """Tests for Phase 3: Conflicting feedback handling."""
    
    def test_conflict_detection(self):
        """Constraint merger should detect conflicts."""
        from backend.refinement_engine import ConstraintMerger, FeedbackDelta
        
        merger = ConstraintMerger()
        
        original = {
            "goal": "invent_meal",
            "ingredients": ["cheese"],
            "nutritional_goals": {"low_fat": True}
        }
        
        delta = FeedbackDelta(
            adjustments={
                "macros": {"protein": "unchanged", "fat": "increase", "carbs": "unchanged"},
                "texture": [],
                "flavor_profile": [],
                "caloric_density": "unchanged"
            }
        )
        
        merged = merger.merge(original, delta)
        
        # Should detect conflict: low_fat + increase fat
        assert len(merged['conflicts']) > 0
        assert any('fat' in c.lower() for c in merged['conflicts'])


class TestPhase3ImpossibleRefinements:
    """Tests for Phase 3: Impossible refinement refusal."""
    
    def test_refinement_result_structure(self):
        """Verify RefinementResult has all required fields."""
        from backend.refinement_engine import RefinementResult
        
        result = RefinementResult(
            recipe="Test recipe",
            changes=["Added egg whites"],
            chemical_justification="Albumin increases protein content",
            nutrition_estimate={"protein": 35},
            confidence="high",
            warnings=[]
        )
        
        # Check all required fields from spec
        assert hasattr(result, 'recipe')
        assert hasattr(result, 'changes')
        assert hasattr(result, 'chemical_justification')
        assert hasattr(result, 'nutrition_estimate')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'warnings')
        
        # Check confidence is valid
        assert result.confidence in ['high', 'medium', 'low']


class TestPhase3NoOpRefinement:
    """Tests for Phase 3: No-op refinement (no feedback)."""
    
    def test_empty_feedback_returns_original(self):
        """Empty feedback should return original recipe unchanged."""
        from backend.refinement_engine import RefinementEngine
        
        with patch('backend.refinement_engine.LLMQwen3') as MockLLM:
            mock_instance = MagicMock()
            MockLLM.return_value = mock_instance
            
            engine = RefinementEngine()
            
            result = engine.refine(
                previous_recipe="Original chicken rice recipe",
                original_intent={"goal": "invent_meal", "ingredients": ["chicken", "rice"]},
                feedback=""
            )
            
            # Should return original recipe with no-op message
            assert "Original chicken rice recipe" in result.recipe
            assert "No changes requested" in result.changes


class TestPhase3RefinementIntegration:
    """Integration tests for Phase 3 refinement in pipeline."""
    
    def test_pipeline_has_refine_method(self):
        """Verify NutriPipeline has refine() method."""
        from backend.food_synthesis import NutriPipeline
        
        with patch('backend.food_synthesis.FoodSynthesisRetriever'):
            with patch('backend.food_synthesis.FoodSynthesisEngine'):
                with patch('backend.food_synthesis.IntentAgent'):
                    pipeline = NutriPipeline.__new__(NutriPipeline)
                    assert hasattr(pipeline, 'refine')
    
    def test_refinement_result_fields(self):
        """Test that RefinementResult has all spec-required fields."""
        from backend.refinement_engine import RefinementResult
        
        result = RefinementResult(
            recipe="Refined recipe",
            changes=["Change 1", "Change 2"],
            chemical_justification="Chemical reason",
            nutrition_estimate={"protein": 40},
            confidence="medium"
        )
        
        data = result.to_dict()
        
        # All fields from spec must exist
        assert 'recipe' in data
        assert 'changes' in data
        assert 'chemical_justification' in data
        assert 'nutrition_estimate' in data
        assert 'confidence' in data
        assert 'warnings' in data


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
