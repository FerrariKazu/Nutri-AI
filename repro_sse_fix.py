
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from backend.sse_utils import format_sse_event

def test_sse_fix():
    print("Testing SSE formatting with stream_id...")
    
    # 1. Test 'done' event with stream_id (The previous failure point)
    try:
        event = "done"
        data = {"status": "success", "stream_id": "test_stream_123"}
        result = format_sse_event(event, data)
        print(f"✅ 'done' event with stream_id passed.")
        print(f"Result: {result.strip()}")
    except AssertionError as e:
        print(f"❌ 'done' event with stream_id FAILED: {e}")
        return False

    # 2. Test 'token' event with stream_id
    try:
        event = "token"
        data = {"content": "Hello", "stream_id": "test_stream_456"}
        result = format_sse_event(event, data)
        print(f"✅ 'token' event with stream_id passed.")
    except AssertionError as e:
        print(f"❌ 'token' event with stream_id FAILED: {e}")
        return False

    # 3. Test 'ping' event (should still work without stream_id)
    try:
        result = format_sse_event("ping", {})
        print(f"✅ 'ping' event passed.")
    except Exception as e:
        print(f"❌ 'ping' event FAILED: {e}")
        return False

    print("\nAll SSE formatting tests PASSED!")
    return True

if __name__ == "__main__":
    if test_sse_fix():
        sys.exit(0)
    else:
        sys.exit(1)
