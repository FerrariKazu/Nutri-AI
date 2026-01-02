import ollama
import json

client = ollama.Client(host="http://localhost:11434", timeout=60.0)
messages = [{"role": "user", "content": "Respond with a JSON object: {\"status\": \"ok\"}"}]

print("Testing with format='json'...")
try:
    response = client.chat(model="qwen3:8b", messages=messages, format="json", stream=False)
    print(f"Response: '{response.get('message', {}).get('content')}'")
except Exception as e:
    print(f"Error: {e}")

print("\nTesting WITHOUT format='json'...")
try:
    response = client.chat(model="qwen3:8b", messages=messages, stream=False)
    print(f"Response: '{response.get('message', {}).get('content')}'")
except Exception as e:
    print(f"Error: {e}")
