"""
Prompt templates and builder for Agentic RAG.
Provides specialized few-shot examples and system prompt generation.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

FEW_SHOT_RECIPE = """
Example Recipe Inquiry:
User: "Make me something healthy with chickpeas."
Thought: The user wants a healthy recipe using chickpeas. I should search for chickpea-based recipes.
Action: search_recipes(query="healthy chickpea recipes", k=3)
Observation: Found 3 recipes: "Healthy Chickpea Salad", "Roasted Chickpea Wraps", "Chickpea Brownies".
Thought: "Chickpea Brownies" are unique and healthy. I will provide this recipe with a chemical explanation of how chickpeas provide structure without flour.
Final Answer: 
Here is a recipe for Flourless Chickpea Brownies... (Detailed recipe follows)
"""

FEW_SHOT_CHEMISTRY = """
Example Chemistry Inquiry:
User: "What happens when you heat turmeric?"
Thought: The user is asking about the chemical behavior of turmeric (curcumin) under heat. I should check curcumin's chemical properties and reactions.
Action: get_food_chemistry(compound="curcumin")
Observation: Curcumin (CID 969516). Molecular formula C21H20O6. Solubility increases in oil. Degrades at high temperatures into ferulic acid and vanillin, but bioavailability increases in the presence of piperine (black pepper) and heat.
Thought: Heating turmeric in oil (tempering) is a common culinary technique called "tadka" that increases curcumin absorption. I will explain the degradation and the bioavailability boost.
Final Answer: 
When you heat turmeric, the primary active compound, **curcumin**, undergoes several changes... (Detailed scientific explanation)
"""

class PromptBuilder:
    """Class to manage and build system prompts for the RAG agent."""
    
    def __init__(self):
        self.recipe_keywords = ['create', 'recipe', 'make', 'cook', 'design', 'meal', 'dish', 'prepare']
        self.chemistry_keywords = ['chemical', 'molecule', 'compound', 'reaction', 'substance', 'science', 'what is', 'how does']

    def detect_query_type(self, query: str) -> str:
        """Classify user query into 'recipe', 'chemistry', or 'general'."""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in self.recipe_keywords):
            return 'recipe'
        if any(kw in query_lower for kw in self.chemistry_keywords):
            return 'chemistry'
            
        return 'general'

    def build_prompt(self, query_type: str, tools_description: str, max_iterations: int) -> str:
        """Construct the system prompt for the current iteration."""
        
        base_prompt = f"""
You are Nutri-AI, a world-class food scientist and nutritionist.
Your goal is to provide scientifically accurate, chemically-grounded answers to food questions.

{tools_description}

You use a ReAct framework:
Thought: Describe your reasoning about the user's question.
Action: Choose a tool from the list above and specify parameters.
Observation: The output from that tool.
(Repeat Thought/Action/Observation if needed)
Final Answer: Provide the final comprehensive answer to the user.

Maximum iterations: {max_iterations}
Current iteration: {{iteration}}

"""
        if query_type == 'recipe':
            base_prompt += f"\nSpecial Instruction: Focus on creating balanced, healthy recipes.\n{FEW_SHOT_RECIPE}"
        elif query_type == 'chemistry':
            base_prompt += f"\nSpecial Instruction: Provide deep molecular-level reasoning.\n{FEW_SHOT_CHEMISTRY}"
            
        return base_prompt
