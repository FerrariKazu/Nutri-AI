import asyncio
import httpx
import json
import uuid

async def verify_border_control_sync():
    print("Testing Border Control SSE Identity Synchronization...")
    
    # Generate a specific client-side run_id
    client_run_id = "client-sync-" + str(uuid.uuid4())[:8]
    print(f"Client Run ID: {client_run_id}")
    
    url = "http://localhost:8000/api/chat/stream"
    params = {
        "message": "Verify identity synchronization.",
        "session_id": "test_sync_" + str(uuid.uuid4())[:8],
        "x_user_id": "test_user",
        "run_id": client_run_id  # Send the sync ID
    }
    
    found_correct_sync = False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", url, params=params) as response:
                if response.status_code != 200:
                    print(f"FAILED: Backend returned {response.status_code}")
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line.replace("data: ", "").strip())
                            
                            # Check if backend echoed our run_id
                            run_id = data.get("run_id")
                            if run_id == client_run_id:
                                if not found_correct_sync:
                                    print(f"✅ SYNC SUCCESS: Backend echoed our run_id: {run_id}")
                                found_correct_sync = True
                            elif run_id:
                                print(f"❌ SYNC FAILURE: Backend used unexpected run_id: {run_id}")
                            
                            if data.get("type") == "execution_trace":
                                content = data.get("content", {})
                                claims = content.get("claims", [])
                                for c in claims[:1]:
                                    c_run = c.get("run_id")
                                    if c_run == client_run_id:
                                        print(f"✅ TRIGGER SUCCESS: Trace claim stamped with sync ID: {c_run}")
                                    else:
                                        print(f"❌ TRIGGER FAILURE: Claim mismatch: {c_run}")
                                break
                        except Exception as e:
                            pass
        
        if found_correct_sync:
            print("\n✨ VERIFICATION SUCCESS: End-to-end Identity Synchronization active.")
        else:
            print("\n❌ VERIFICATION FAILED: Synchronization not detected.")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(verify_border_control_sync())
