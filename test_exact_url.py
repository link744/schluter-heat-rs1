import asyncio
import json
import sys
from aiohttp import ClientSession

async def main():
    token = "7cdba9c65eaacd50bcd9200b48c9c3836e4d6dc3c1d1823c"
    headers = {
        "Session-Id": token,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    url = "https://schluterditraheat.com/api/device/669645/attribute?attributes=setpointMode"
    
    async with ClientSession() as session:
        print(f"Testing Exact User URL: {url}")
        try:
            async with session.get(url, headers=headers) as resp:
                print("Status code:", resp.status)
                print(await resp.text())
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
