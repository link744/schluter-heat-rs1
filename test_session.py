import asyncio
import json
import sys
from aiohttp import ClientSession

BASE_URL = "https://schluterditraheat.com/api/"

async def main():
    token = sys.argv[1]
    
    async with ClientSession() as session:
        print("--- Testing Locations with Token as Session-Id ---")
        headers = {"Session-Id": token}
        async with session.get(f"{BASE_URL}location", headers=headers) as resp:
            text = await resp.text()
            if len(text) > 200:
                print("Success! Got large response.")
            else:
                print(text)

asyncio.run(main())
