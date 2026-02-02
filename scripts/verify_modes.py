
import asyncio
import httpx
import time
import json
import sys

API_URL = "http://localhost:8000/api/chat/stream"
PROMPT = "Why does sourdough taste sour?"
MODES = ["simple", "standard", "chemistry"]

async def test_mode(mode):
    print(f"\n--- Testing Mode: {mode.upper()} ---")
    start_time = time.time()
    ttft = 0
    token_count = 0
    content = ""
    
    params = {
        "message": PROMPT,
        "session_id": f"test_mode_{mode}_{int(time.time())}",
        "verbosity": mode,
        "execution_mode": None  # As sent by App.jsx
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", API_URL, params=params) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            # Skip simple status strings if any (SSE format in server.py sends JSON usually or plain text? 
                            # server.py format_sse_event sends JSON if content is dict, otherwise string?
                            # Let's check format_sse_event logic. It usually sends `data: content`
                            # Wait, API yields events.
                            pass
                        except:
                            pass
                        
                        # In Nutri backend:
                        # event: token -> data: <token_string>
                        # event: status -> data: {"phase":...}
                        pass

                # Re-reading verify logic directly from stream is hard without parsing events.
                # Let's use a simpler parser logic.
                pass

    except Exception as e:
        print(f"Error: {e}")
        return None

# Rethinking the script to properly parse SSE
async def run_verification():
    results = {}
    
    for mode in MODES:
        print(f"\n🧪 Testing Mode: {mode}...")
        results[mode] = {"ttft": None, "tokens": 0, "length": 0, "sample": ""}
        
        session_id = f"test_{mode}_{int(time.time())}"
        url = f"{API_URL}?message={PROMPT.replace(' ', '+')}&session_id={session_id}&verbosity={mode}"
        
        start_t = time.time()
        first_token_t = None
        full_content = []
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    
                    if line.startswith("event: token"):
                        # Next line is data
                        pass
                    elif line.startswith("data: "):
                        # This could be token data if previous event was token
                        # But server.py sends `event: token\ndata: actual_token\n\n`
                        # Actually standard SSE.
                        
                        payload = line[6:]
                        
                        # If it's a JSON object (status), skip for token count
                        # But format_sse_event: 
                        # if event == 'token', data is the token string directly?
                        # Let's check server.py: `yield format_sse_event(event_type, content)`
                        # `format_sse_event` takes content.
                        # If content is string -> `data: <string>`
                        
                        if payload.strip() == "{}": continue # DONE event data?
                        
                        # Heuristic: If it looks like JSON, it's likely status or done.
                        if payload.strip().startswith("{"):
                            continue
                            
                        # It is likely a token
                        if first_token_t is None:
                            first_token_t = time.time()
                            
                        full_content.append(payload)
                        
        end_t = time.time()
        
        results[mode]["ttft"] = (first_token_t - start_t) if first_token_t else 0
        results[mode]["duration"] = end_t - start_t
        results[mode]["length"] = len("".join(full_content))
        results[mode]["sample"] = "".join(full_content)[:100].replace("\n", " ") + "..."
        
        print(f"   ✅ TTFT: {results[mode]['ttft']:.2f}s | Len: {results[mode]['length']} chars")

    print("\n" + "="*60)
    print(f"{'MODE':<12} | {'TTFT':<8} | {'LEN':<8} | {'SAMPLE'}")
    print("-" * 60)
    for mode, data in results.items():
        print(f"{mode:<12} | {data['ttft']:.2f}s   | {data['length']:<8} | {data['sample']}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_verification())
