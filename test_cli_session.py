import asyncio
import logging
import argparse
import sys
from aiohttp import ClientSession
import os

# Ensure the schluter_heat directory is in the path to import api.py directly 
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "schluter_heat"))
from api import SchluterAPI

logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")

async def main():
    parser = argparse.ArgumentParser(description="Test Schluter Heat API directly using a Session-Id")
    parser.add_argument("--session-id", "-s", type=str, help="Session ID from your browser", required=False)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    session_id = args.session_id
    if not session_id:
        try:
            session_id = input("Browser Session-Id: ")
        except EOFError:
            print("Error reading input. Please specify via --session-id <id>")
            return

    async with ClientSession() as session:
        api = SchluterAPI(session)
        
        # Manually inject the session ID into the API client, skipping login entirely!
        api._session_id = session_id
        
        print("\n--- Bypassing Login using Session-Id ---")
            
        print("\n--- Fetching Locations ---")
        try:
            locations = await api.get_locations()
            
            # Since Neviweb returns 200 OKs with internal JSON errors, check for an embedded error block
            if isinstance(locations, dict) and "error" in locations:
                print(f"Error fetching locations! Your Session-Id may be expired/invalid.\nDetails: {locations['error']}")
                return
                
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
