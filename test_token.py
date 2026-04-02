import asyncio
import logging
import json
import sys
from aiohttp import ClientSession

AUTH_BASE_URL = "https://mobile-api.neviweb.com/api/"

async def main():
    token = sys.argv[1]
    
    async with ClientSession() as session:
        # Test token login
        print(f"Testing token login with token: {token[:10]}...")
        payload = {"refreshToken": token}
        async with session.post(f"{AUTH_BASE_URL}login", json=payload) as response:
            data = await response.json()
            print("Login Response:")
            print(json.dumps(data, indent=2))
        
        print("\nTesting connect...")
        headers = {"refreshToken": token}
        async with session.post(f"{AUTH_BASE_URL}connect", headers=headers) as response:
            try:
                data2 = await response.json()
                print("Connect Response:")
                print(json.dumps(data2, indent=2))
            except Exception as e:
                print("Connect failed parse:", await response.text())

asyncio.run(main())
