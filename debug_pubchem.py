import asyncio
import httpx
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.pubchem_client import PubChemClient

async def debug_pubchem():
    logging.basicConfig(level=logging.DEBUG)
    client = PubChemClient()
    print("Testing PubChem health check...")
    try:
        # Increase timeout for debugging
        url = f"{client.BASE_URL}/compound/cid/962/JSON"
        print(f"Requesting: {url}")
        
        async with httpx.AsyncClient() as debug_client:
            response = await debug_client.get(url, timeout=5.0)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text[:100]}...")
            
        is_healthy = await client.health_check()
        print(f"Internal health_check result: {is_healthy}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_pubchem())
