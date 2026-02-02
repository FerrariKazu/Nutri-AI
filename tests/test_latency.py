import time
import httpx
import json

# Llama.cpp server endpoint
URL = "http://localhost:8081/v1/chat/completions"

def test_latency(prompt: str, max_tokens: int = 100):
    payload = {
        "model": "qwen3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False
    }
    
    print(f"\nPrompt: {prompt}")
    print(f"Max tokens: {max_tokens}")
    print("-" * 30)
    
    try:
        start_time = time.time()
        response = httpx.post(URL, json=payload, timeout=600.0)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            
            total_time = end_time - start_time
            tokens_per_sec = completion_tokens / total_time if total_time > 0 else 0
            
            print(f"Content: {content[:200]}...")
            print("-" * 30)
            print(f"Total time: {total_time:.2f}s")
            print(f"Prompt tokens: {prompt_tokens}")
            print(f"Completion tokens: {completion_tokens}")
            print(f"Throughput: {tokens_per_sec:.2f} tokens/s")
            
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("Testing llama.cpp latency...")
    test_latency("Explain the benefits of Mediterranean diet in 3 sentences.", max_tokens=150)
