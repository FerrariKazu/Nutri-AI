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
    @staticmethod
    def format_fast_output(text: str) -> str:
        """
        Specialized formatter for FAST profile output.
        Ensures strict markdown adherence, clean spacing, and zero internal data.
        """
        if not text:
            return ""
            
        # 1. Basic cleanup (strips thoughts, agent-leaks, etc.)
        text = ResponseFormatter.format_response(text)
        
        # 2. Block Headers: Ensure double newline after # Title
        text = re.sub(r'^(#+ .*)$', r'\1\n', text, flags=re.MULTILINE)
        
        # 3. List Starts: Ensure blank line before a list block
        # Match a non-list line followed by a list line, avoiding variable-width look-behind
        text = re.sub(r'^([^-\*•\s\d].*)\n([-*•] |\d+\. )', r'\1\n\n\2', text, flags=re.MULTILINE)
        
        # 4. Bolded "Subheaders": Ensure blank line before and after **Bold** lines
        text = re.sub(r'(?<!\n\n)\n(\*\*.*?\*\*)', r'\n\n\1', text)
        text = re.sub(r'^(\*\*.*?\*\*)$', r'\1\n', text, flags=re.MULTILINE)
        
        # 5. Paragraphs: Ensure blank lines between sentences on separate lines
        text = re.sub(r'([.!?:])\n([A-Z])', r'\1\n\n\2', text)
        
        # 6. Final Spacing Normalization
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 7. Zero-tolerance check for JSON leakage
        if "{" in text and "}" in text:
             patterns = [
                 r'\{.*?"final_answer".*?\}',
                 r'\{.*?"status".*?\}',
                 r'\{.*?"user_output".*?\}'
             ]
             for p in patterns:
                 text = re.sub(p, '', text, flags=re.DOTALL)
        
        return text.strip()
