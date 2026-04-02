import asyncio
import logging
import argparse
import sys
import getpass
from aiohttp import ClientSession
import os

# Ensure the schluter_heat directory is in the path to import api.py directly 
# and bypass __init__.py which requires the homeassistant module
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "schluter_heat"))
from api import SchluterAPI, SchluterAuthenticationError

logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")

async def main():
    parser = argparse.ArgumentParser(description="Test Schluter Heat API directly from terminal using a Refresh Token")
    parser.add_argument("--token", "-t", type=str, help="Refresh Token", required=False)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    token = args.token
    if not token:
        try:
            token = input("Refresh Token: ")
        except EOFError:
            print("Error reading input. Please specify via --token <token>")
            return

    async with ClientSession() as session:
        api = SchluterAPI(session)
        print("\n--- Authenticating with Token ---")
        try:
            await api.login(token)
            print("Login successful!")
        except Exception as e:
            print(f"Login failed: {e}")
            return
            
        print("\n--- Connecting ---")
        try:
            await api.connect()
            print("Session established.")
        except Exception as e:
            print(f"Connection failed: {e}")
            return
            
        print("\n--- Fetching Locations ---")
        try:
            locations = await api.get_locations()
            if not locations:
                print("No locations found.")
                return
            for loc in locations:
                print(f"Location ID: {loc.get('id')}, Name: {loc.get('name')}")
        except Exception as e:
            print(f"Failed to get locations: {e}")
            return
            
        print("\n--- Fetching Devices ---")
        try:
            for loc in locations:
                loc_id = loc.get("id")
                print(f"\nDevices in Location {loc.get('name')} ({loc_id}):")
                devices = await api.get_devices(loc_id)
                if not devices:
                    print("  No devices found.")
                    continue
                    
                for dev in devices:
                    dev_id = dev.get("id")
                    dev_name = dev.get("name")
                    print(f"  Device ID: {dev_id}, Name: {dev_name}")
                    
                    print("    Fetching device status...")
                    try:
                        status = await api.get_thermostat_status(dev_id)
                        print(f"      Current Temp: {status.current_temp}°C")
                        print(f"      Target Temp:  {status.target_temp}°C")
                        print(f"      Min/Max Temp: {status.min_temp}°C / {status.max_temp}°C")
                        print(f"      Heating:      {'Yes' if status.heating else 'No'} ({status.heating_percent}%)")
                        print(f"      Mode:         {status.setpoint_mode}")
                        print(f"      Occupancy:    {status.occupancy_mode}")
                        print(f"      Floor Mode:   {status.air_floor_mode}")
                        print(f"      GFCI Status:  {status.gfci_status}")
                    except Exception as e:
                        print(f"      Failed to get status: {e}")
        except Exception as e:
            print(f"Failed to get devices: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
