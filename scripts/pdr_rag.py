import requests
import json
from .retrieve import retrieve

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"  # Matches your existing project settings

SYSTEM_PROMPT = """You are a factual herbal medicine assistant.
Use ONLY the provided context from the PDR.
If the answer does not exist in the context, say:
"I don't know based on the PDR."
"""

def query_pdr(user_query: str):
    """
    Full RAG pipeline: Retrieve context -> Build Prompt -> Query Ollama
    """
    # 1. Retrieve context
    try:
        chunks = retrieve(user_query, k=6)
    except Exception as e:
        return {
            "answer": "Error retrieving documents. Please ensure the RAG index is built.",
            "error": str(e),
            "sources": []
        }
    
    if not chunks:
        return {
            "answer": "I don't know based on the PDR (No relevant documents found).",
            "sources": []
        }

    # 2. Build Context String
    context_text = ""
    sources = []
    for c in chunks:
        context_text += f"[Page {c['page']}]\n{c['text']}\n\n"
        sources.append({"page": c['page'], "preview": c['text'][:50] + "..."})

    # 3. Construct Messages for LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {user_query}"}
    ]

    # 4. Call Ollama
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False,
                "temperature": 0.3  # Lower temperature for factual QA
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("message", {}).get("content", "")
        
        return {
            "answer": answer,
            "sources": sources,
            "context_used": context_text
        }
        
    except Exception as e:
        return {
            "answer": "Error communicating with AI model.",
            "error": str(e),
            "sources": sources
        }
