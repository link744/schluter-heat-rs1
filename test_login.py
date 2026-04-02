import asyncio
import logging
import json
from aiohttp import ClientSession
import sys

AUTH_BASE_URL = "https://mobile-api.neviweb.com/api/"

async def main():
    username = sys.argv[1]
    password = sys.argv[2]
    
    async with ClientSession() as session:
        # Try neviweb interface
        payload_neviweb = {
            "email": username,
            "password": password,
            "interface": "neviweb",
            "stayConnected": 1
        }
        print("Testing interface: neviweb")
        async with session.post(f"{AUTH_BASE_URL}login", json=payload_neviweb) as response:
            print(await response.text())

        # Try schluter interface
        payload_schluter = {
            "email": username,
            "password": password,
            "interface": "schluter",
            "stayConnected": 1
        }
        print("\nTesting interface: schluter")
        async with session.post(f"{AUTH_BASE_URL}login", json=payload_schluter) as response:
             print(await response.text())

asyncio.run(main())
