
import os
import sys
from llm import stream

def test_stream():
    messages = [
        {"role": "system", "content": "You are a helpful assistant. ALWAYS start your response with 'Final Answer:'"},
        {"role": "user", "content": "how can i make bread?"}
    ]
    print("--- Starting Stream ---")
    for chunk in stream(messages):
        print(chunk, end="", flush=True)
    print("\n--- Stream Complete ---")

if __name__ == "__main__":
    test_stream()
