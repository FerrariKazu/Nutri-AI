"""
Test RAG System End-to-End

Quick test to verify the complete RAG pipeline works.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from rag import FAISSRetriever, ScienceAgent

def test_retrieval():
    """Test retrieval component."""
    print("Testing Retrieval...")
    print("-" * 60)
    
    retriever = FAISSRetriever()
    
    query = "What is the Maillard reaction?"
    results = retriever.retrieve(query, top_k=3)
    
    print(f"Query: {query}")
    print(f"Retrieved: {len(results)} chunks")
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['source']} (score: {result['score']:.3f})")
        print(f"   {result['text'][:150]}...")
    
    return results

def test_agent(chunks):
    """Test agent synthesis."""
    print("\n" + "="*60)
    print("Testing Agent Synthesis...")
    print("-" * 60)
    
    agent = ScienceAgent()
    
    question = "What causes food to brown when cooked?"
    response = agent.synthesize(question, chunks, use_llm=False)
    
    print(f"Question: {question}")
    print(f"\nMethod: {response['method']}")
    print(f"Confidence: {response['confidence']}")
    print(f"Sources: {len(response['sources'])}")
    
    for i, source in enumerate(response['sources'], 1):
        print(f"  {i}. {source['source']} (score: {source['max_score']:.3f})")
    
    print(f"\nAnswer preview:")
    print(response['answer'][:500] + "...\n")
    
    return response

def main():
    print("="*60)
    print("RAG SYSTEM END-TO-END TEST")
    print("="*60)
    print()
    
    try:
        # Test retrieval
        chunks = test_retrieval()
        
        # Test agent
        response = test_agent(chunks)
        
        print("="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print(f"Retrieved {len(chunks)} chunks")
        print(f"Synthesized response with {len(response['sources'])} sources")
        print("\nRAG system is fully operational!")
        
    except Exception as e:
        print("="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
