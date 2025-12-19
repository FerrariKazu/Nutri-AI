from __future__ import annotations
import re

class ResponseFormatter:
    """Utility class to format and clean LLM responses for the frontend."""
    
    @staticmethod
    def format_response(text: str) -> str:
        if not text:
            return ""
            
        # 1. Strip whitespace
        text = text.strip()
        
        # 2. Handle common system prompt leaks (thought blocks, action tags)
        # (This logic is often also in extract_final_answer, but we wrap it here)
        patterns_to_remove = [
            r"<thought>.*?</thought>",
            r"<action>.*?</action>",
            r"<observation>.*?</observation>",
            r"Final Answer:",
            r"Answer:",
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.DOTALL)
            
        # 3. Clean up extra newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
