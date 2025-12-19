"""
Science Agent for RAG System

Synthesizes retrieved knowledge into coherent, cited answers.
"""

from typing import List, Dict, Optional


class ScienceAgent:
    """Agentic layer for synthesizing RAG responses."""
    
    def __init__(self, llm_config: Optional[Dict] = None):
        """
        Initialize Science Agent.
        
        Args:
            llm_config: Optional LLM configuration (API keys, model name, etc.)
        """
        self.llm_config = llm_config or {}
    
    def compress_context(
        self,
        chunks: List[Dict],
        max_tokens: int = 3000
    ) -> List[Dict]:
        """
        Compress context if needed.
        
        For now, simple truncation by score.
        TODO: Implement smart summarization if needed.
        """
        # Estimate ~4 chars per token
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        compressed = []
        current_chars = 0
        
        for chunk in chunks:
            chunk_chars = chunk['char_count']
            if current_chars + chunk_chars > max_chars:
                break
            compressed.append(chunk)
            current_chars += chunk_chars
        
        return compressed
    
    def build_prompt(self, question: str, chunks: List[Dict]) -> str:
        """
        Build prompt for LLM with sources and question.
        
        Args:
            question: User question
            chunks: Retrieved knowledge chunks
        
        Returns:
            Formatted prompt string
        """
        # Build sources section
        sources_text = []
        for i, chunk in enumerate(chunks, 1):
            source_name = chunk['source'].replace('.txt', '').replace('_', ' ')
            sources_text.append(
                f"[Source {i}: {source_name}]\n{chunk['text']}\n"
            )
        
        # Complete prompt
        prompt = f"""You are a food science expert. Answer the question using ONLY the provided sources below.

Sources:
{chr(10).join(sources_text)}

Question: {question}

Instructions:
- Combine information from multiple sources when relevant
- Explain scientific mechanisms clearly
- Cite sources explicitly using format: "According to [Source 1], ..."
- Only use information from the provided sources
- If sources don't contain enough information, state this clearly
- Avoid speculation beyond what the sources say

Answer:"""
        
        return prompt
    
    def extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """
        Extract source citations from chunks.
        
        Args:
            chunks: Retrieved chunks
        
        Returns:
            List of source dicts with filename and relevance score
        """
        # Group by source
        source_map = {}
        for chunk in chunks:
            source = chunk['source']
            if source not in source_map:
                source_map[source] = {
                    'source': source.replace('.txt', '').replace('_', ' '),
                    'filename': source,
                    'max_score': chunk['score'],
                    'chunk_count': 0
                }
            source_map[source]['chunk_count'] += 1
            source_map[source]['max_score'] = max(
                source_map[source]['max_score'],
                chunk['score']
            )
        
        # Convert to sorted list
        sources = list(source_map.values())
        sources.sort(key=lambda x: x['max_score'], reverse=True)
        
        return sources
    
    def synthesize(
        self,
        question: str,
        chunks: List[Dict],
        use_llm: bool = True
    ) -> Dict:
        """
        Synthesize answer from retrieved chunks.
        
        Args:
            question: User question
            chunks: Retrieved knowledge chunks
            use_llm: Whether to use LLM (default) or return formatted chunks
        
        Returns:
            Response dict with answer, sources, confidence
        """
        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the knowledge base to answer this question.",
                "sources": [],
                "confidence": "none",
                "method": "fallback"
            }
        
        # Compress context if needed
        compressed_chunks = self.compress_context(chunks)
        
        # Extract sources
        sources = self.extract_sources(compressed_chunks)
        
        if use_llm and self.llm_config:
            # TODO: Implement actual LLM call
            # For now, return structured prompt
            prompt = self.build_prompt(question, compressed_chunks)
            
            answer = f"""[LLM integration not yet implemented]

To integrate an LLM, pass your API configuration to ScienceAgent(llm_config={{...}})
and implement the LLM call in this method.

For now, here are the top {len(compressed_chunks)} relevant chunks:

{chr(10).join(f"{i}. {c['text'][:200]}..." for i, c in enumerate(compressed_chunks[:3], 1))}

Prompt template prepared with {len(compressed_chunks)} sources."""
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": "medium",
                "method": "prompt_only",
                "prompt": prompt  # Include for debugging
            }
        else:
            # Fallback: Return formatted chunks
            answer_parts = []
            for i, chunk in enumerate(compressed_chunks[:5], 1):
                source_name = chunk['source'].replace('.txt', '').replace('_', ' ')
                answer_parts.append(
                    f"**From {source_name}** (relevance: {chunk['score']:.3f}):\n{chunk['text'][:400]}...\n"
                )
            
            return {
                "answer": "\n\n".join(answer_parts),
                "sources": sources,
                "confidence": "high",
                "method": "chunk_aggregation"
            }


def main():
    """Test agent."""
    # Mock chunks
    mock_chunks = [
        {
            "chunk_id": "test_001",
            "source": "The_Science_of_Cooking.txt",
            "text": "The Maillard reaction is a chemical reaction between amino acids and reducing sugars that gives browned food its distinctive flavor.",
            "score": 0.92,
            "char_count": 132
        },
        {
            "chunk_id": "test_002",
            "source": "Food_Chemistry.txt",
            "text": "Maillard browning occurs optimally between 140-165°C (280-330°F). This temperature range allows the complex cascade of reactions to proceed efficiently.",
            "score": 0.88,
            "char_count": 158
        }
    ]
    
    agent = ScienceAgent()
    response = agent.synthesize(
        question="What is the Maillard reaction?",
        chunks=mock_chunks,
        use_llm=False
    )
    
    print("Answer:")
    print(response["answer"])
    print(f"\nSources: {len(response['sources'])}")
    print(f"Method: {response['method']}")


if __name__ == "__main__":
    main()
