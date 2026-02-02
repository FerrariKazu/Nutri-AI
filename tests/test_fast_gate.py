import pytest
import re
from backend.simple_chat import is_fast_conversation

# Test Data
# (Input Message, Expected Result: True=Chat, False=Orchestrator)
TEST_CASES = [
    # GREETINGS (Should be True)
    ("hi", True),
    ("hello", True),
    ("hey!!", True),
    ("sup", True),
    ("yo", True),
    ("hi there", True),
    ("hello Nutri", False), # > 2 tokens, no regex match -> False (Safe fallback)
    
    # META QUESTIONS (Should be True)
    ("Who are you?", True),
    ("What are you?", True),
    ("How are you doing?", True),
    ("Are you real?", True),
    
    # FOOD REQUESTS (Should be False)
    ("Make me a pizza", False),
    ("recipe for cake", False),
    ("cook an egg", False),
    ("what is the nutrition of an apple", False),
    ("I want to eat dinner", False),
    ("give me a diet plan", False),
    ("how many calories in bread", False),
    
    # AMBIGUOUS / MIXED (Should be False due to Guardrails)
    ("Hey make me dinner", False), # Contains "make", "dinner"
    ("Hi give me a recipe", False), # Contains "recipe"
    ("Hello what are the ingredients", False), # Contains "ingredients"
]

@pytest.mark.parametrize("msg, expected", TEST_CASES)
def test_fast_gate_logic(msg, expected):
    """
    Verifies that the is_fast_conversation heuristic correctly identifies
    greetings vs task intents.
    """
    assert is_fast_conversation(msg) == expected

def test_normalization():
    """Ensure punctuation is ignored"""
    assert is_fast_conversation("Hello!!!") is True
    assert is_fast_conversation("   hi   ") is True
    assert is_fast_conversation("wHO aRe yOu??") is True
