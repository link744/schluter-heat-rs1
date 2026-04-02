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
    
    urls = [
        "https://schluterditraheat.com/api/devices",
        "https://schluterditraheat.com/api/locations",
        "https://schluterditraheat.com/api/location",
        "https://mobile-api.neviweb.com/api/locations",
        "https://mobile-api.neviweb.com/api/location"
    ]
    
    async with ClientSession() as session:
        for url in urls:
            try:
                print(f"Testing URL: {url}")
                async with session.get(url, headers=headers) as resp:
                    print(await resp.text())
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(main())
