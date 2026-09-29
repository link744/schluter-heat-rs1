"""
Schluter DITRA-HEAT Complete API Client
100% API Coverage - Ready for Home Assistant Integration

Based on:
- Decompiled Android APK
- HAR file capture from web interface
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from aiohttp import ClientSession, ClientTimeout
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

# Base URLs
BASE_URL = "https://schluterditraheat.com/api/"
AUTH_BASE_URL = "https://mobile-api.neviweb.com/api/"

# Timeouts
DEFAULT_TIMEOUT = ClientTimeout(total=30)


@dataclass
class SchluterThermostat:
    """Represents a Schluter thermostat/floor heating device"""
    device_id: int
    name: str
    
    # Temperature
    current_temp: Optional[float] = None
    target_temp: Optional[float] = None
    min_temp: float = 5.0
    max_temp: float = 33.0
    
    # Operating Mode
    setpoint_mode: Optional[str] = None  # "manual" or "schedule"
    occupancy_mode: Optional[str] = None  # "home" or "away"
    
    # Status
    heating: bool = False
    heating_percent: int = 0
    
    # Configuration
    air_floor_mode: Optional[str] = None  # "air" or "floor"
    gfci_status: Optional[str] = None  # "ok" or error
    
    # Advanced
    floor_setpoint_pwm: Optional[int] = None
    temp_display_status: Optional[str] = None


class SchluterAuthenticationError(Exception):
    """Authentication failed (bad credentials or invalid refresh token)."""

    # The stored refresh token is itself invalid/expired. This is NOT
    # recoverable without user action (a fresh token from the web app).
    REQUIRES_REAUTH = True


class SchluterSessionExpired(SchluterAuthenticationError):
    """The active session expired but the stored refresh token is still good.

    Recoverable: calling login() again re-establishes the session.
    The Neviweb API returns this as HTTP 200 with an error body
    (``{"error": {"code": "USRSESSEXP"}}``), so it never surfaces as a
    raise_for_status() failure - it must be detected explicitly.
    """

    REQUIRES_REAUTH = False


class SchluterAPIError(Exception):
    """General API error (network failure, bad status, malformed payload)."""



class SchluterAPI:
    """
    Complete Schluter DITRA-HEAT API Client
    
    Usage:
        async with ClientSession() as session:
            api = SchluterAPI(session)

            # Use the browser Session-Id directly (no login). This is what
            # the website does on every request and is the value the user
            # copies from the browser Network tab.
            api.set_session_id(session_id)

            # Get devices
            devices = await api.get_devices(location_id)
            
            # Get status
            status = await api.get_thermostat_status(device_id)
            
            # Set temperature
            await api.set_temperature(device_id, 22.0)
    """
    
    def __init__(self, session: ClientSession):
        """Initialize the API client"""
        self._session = session
        self._session_id: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._access_token: Optional[str] = None
        self._user_id: Optional[int] = None
        self._account_id: Optional[int] = None

    def set_session_id(self, session_id: str) -> None:
        """Use a browser Session-Id directly, without any login step.

        The schluterditraheat.com web app authenticates every API request
        with a ``Session-Id`` header (the value the user copies from the
        browser's Network tab). The integration mirrors that behaviour
        instead of calling the Neviweb ``login``/refresh-token endpoint,
        which is a *different* auth scheme and rejects a website Session-Id
        (surfacing to the user as ``invalid_auth``).
        """
        self._session_id = session_id

    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        if self._session_id:
            headers["session-id"] = self._session_id
        
        return headers
    
    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_required: bool = True,
    ) -> Dict[str, Any]:
        """Perform an HTTP request and classify Neviweb API errors.

        The Neviweb API signals most failures with HTTP 200 plus an
        ``error`` body, e.g.::

            {"error": {"code": "USRSESSEXP"}}   # session expired
            {"error": {"code": "ACCSESSEXC"}}   # too many active sessions

        Relying on ``raise_for_status()`` alone (the previous behaviour)
        misses every one of these, which is why sessions that expired
        mid-day were never detected.

        Raises:
            SchluterSessionExpired: session died, refresh token may be fine.
            SchluterAuthenticationError: refresh token itself is dead.
            SchluterAPIError: transport / status / parse failures.
        """
        req_headers = self._get_headers() if headers is None else headers

        try:
            async with self._session.request(
                method,
                url,
                params=params,
                json=json,
                headers=req_headers,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                data = await response.json()
        except Exception as e:
            raise SchluterAPIError(f"Request to {url} failed: {e}") from e

        # HTTP-level failures first (401/403/5xx...)
        if response.status in (401, 403):
            if auth_required and self._refresh_token:
                raise SchluterSessionExpired(
                    f"HTTP {response.status} from {url} - session rejected"
                )
            raise SchluterAuthenticationError(
                f"HTTP {response.status} from {url} - authentication failed"
            )
        if response.status >= 400:
            raise SchluterAPIError(
                f"HTTP {response.status} from {url}: {str(data)[:200]}"
            )

        # HTTP 200 but the body carries an error object
        if isinstance(data, dict) and "error" in data:
            error = data["error"]
            code = str(error.get("code") if isinstance(error, dict) else error).upper()
            _LOGGER.error(
                "Neviweb API error %s from %s (full body: %s)",
                code or "?", url, self._sanitize_response(data),
            )
            if "SESS" in code or "EXPIR" in code or "USRSESSEXP" in code:
                raise SchluterSessionExpired(
                    f"Session expired (code {code or 'unknown'}): {url}"
                )
            if "ACCSESSEXC" in code or "TOOMANY" in code or "ACTIVE" in code:
                raise SchluterAPIError(
                    f"Too many active sessions (code {code}): close other "
                    f"Schluter/Neviweb sessions (web, phone) and retry"
                )
            raise SchluterAPIError(f"Neviweb API error {code or 'unknown'}: {url}")

        return data
    
    async def login_with_credentials(
        self, username: str, password: str
    ) -> Dict[str, Any]:
        """
        Login with username and password to get refresh token
        
        Args:
            username: User's email address
            password: User's password
            
        Returns:
            Login response with refresh token and user info
            
        Raises:
            SchluterAuthenticationError: If login fails
        """
        # Try the Neviweb login endpoint (since Schluter uses Neviweb infrastructure)
        url = f"{AUTH_BASE_URL}login"
        
        payload = {
            "email": username,
            "password": password,
            "interface": "neviweb",
            "stayConnected": 1
        }
        
        try:
            data = await self._request(
                "POST", url, json=payload, auth_required=False
            )
        except SchluterAPIError as e:
            _LOGGER.error("Login with credentials failed: %s", e)
            raise SchluterAuthenticationError(f"Login failed: {e}") from e
        except SchluterSessionExpired as e:
            # Should not happen for a fresh credentials login, but treat
            # as an auth failure rather than a recoverable session issue.
            _LOGGER.error("Login with credentials rejected: %s", e)
            raise SchluterAuthenticationError(f"Login failed: {e}") from e
        
        # Log response structure for debugging
        _LOGGER.debug("Login response keys: %s", list(data.keys()))

        # Extract refresh token from response - try multiple possible keys
        refresh_token = None

        # Try different possible key names
        for key in ["refreshToken", "refresh_token", "RefreshToken", "REFRESH_TOKEN"]:
            if key in data:
                refresh_token = data[key]
                _LOGGER.debug("Found refresh token with key: %s", key)
                break

        # Try nested locations
        if not refresh_token and "session" in data:
            session_data = data["session"]
            for key in ["refreshToken", "refresh_token"]:
                if key in session_data:
                    refresh_token = session_data[key]
                    _LOGGER.debug("Found refresh token in session.%s", key)
                    break

        if not refresh_token:
            _LOGGER.error("No refresh token in response. Response keys: %s", list(data.keys()))
            _LOGGER.error("Full response (sanitized): %s", self._sanitize_response(data))
            raise SchluterAuthenticationError("No refresh token received")

        self._refresh_token = refresh_token
        self._access_token = (
            data.get("access_token")
            or data.get("accessToken")
            or data.get("session", {}).get("access_token")
        )

        if "user" in data:
            self._user_id = data["user"].get("id")
            self._account_id = data["user"].get("account$id") or data["user"].get("accountId")

        _LOGGER.info("Login successful. User ID: %s", self._user_id)
        return data
    
    def _sanitize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response for logging - remove sensitive data"""
        sanitized = {}
        for key, value in data.items():
            if key.lower() in ["password", "token", "refreshtoken", "accesstoken", "access_token", "refresh_token"]:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_response(value)
            elif isinstance(value, list):
                sanitized[key] = f"[{len(value)} items]"
            else:
                sanitized[key] = str(value)[:50]  # First 50 chars only
        return sanitized
    
    
    async def login(self, refresh_token: str) -> Dict[str, Any]:
        """
        Login with refresh token to get access token and user info
        
        Args:
            refresh_token: Refresh token from initial web login
            
        Returns:
            Login response with user and account info
            
        Raises:
            SchluterAuthenticationError: If login fails
        """
        url = f"{AUTH_BASE_URL}login"
        
        payload = {
            "refreshToken": refresh_token
        }
        
        try:
            data = await self._request(
                "POST",
                url,
                json=payload,
                auth_required=False,
            )
        except SchluterAPIError as e:
            _LOGGER.error("Login failed: %s", e)
            raise SchluterAuthenticationError(f"Login failed: {e}") from e
        
        # A dead/invalid refresh token surfaces either as an HTTP 401/403
        # (handled above) or as an API error body.
        self._refresh_token = refresh_token
        self._access_token = data.get("access_token")
        self._session_id = None
        self._user_id = None
        self._account_id = None
        
        # Extract session ID from login response
        if "session" in data:
            self._session_id = data["session"]
            _LOGGER.info("Session ID obtained from login: %s...", str(self._session_id)[:20])
        
        # Extract user info
        if "user" in data:
            self._user_id = data["user"].get("id")
            self._account_id = data["user"].get("account$id") or data.get("account", {}).get("id")
        
        _LOGGER.info("Login successful. User ID: %s, Account ID: %s", self._user_id, self._account_id)
        return data
    
    async def connect(self) -> str:
        """
        Get session ID using refresh token
        
        Returns:
            Session ID string
            
        Raises:
            SchluterAuthenticationError: If not logged in or connection fails
        """
        if not self._refresh_token:
            raise SchluterAuthenticationError("Must login first")
        
        url = f"{AUTH_BASE_URL}connect"
        headers = {"refreshToken": self._refresh_token}
        
        try:
            data = await self._request(
                "POST", url, headers=headers, auth_required=True
            )
        except SchluterAPIError as e:
            raise SchluterAuthenticationError(f"Connect failed: {e}") from e
        
        _LOGGER.debug("Connect response keys: %s", list(data.keys()))
        
        # Try different possible session key locations
        session_id = None
        if "session" in data:
            session_id = data["session"]
        elif "sessionId" in data:
            session_id = data["sessionId"]
        elif "session_id" in data:
            session_id = data["session_id"]
        
        if not session_id:
            _LOGGER.error("No session ID in connect response. Keys: %s", list(data.keys()))
            _LOGGER.error("Full response: %s", self._sanitize_response(data))
            raise SchluterAuthenticationError("No session ID in connect response")
        
        self._session_id = session_id
        _LOGGER.info("Connected. Session ID obtained: %s...", str(session_id)[:20])
        return session_id
    
    async def get_locations(self) -> List[Dict[str, Any]]:
        """
        Get all locations for the authenticated user
        
        Returns:
            List of locations with id, name, etc.
            Example: [{"id": 103355, "name": "Home", ...}, ...]
            
        Raises:
            SchluterAPIError: If request fails
        """
        if not self._session_id:
            raise SchluterAPIError("Must connect first")
        
        url = f"{BASE_URL}locations"
        
        headers = {
            "session-id": self._session_id,
        }
        
        data = await self._request("GET", url, headers=headers)
        
        # Response is a list of locations
        if isinstance(data, list):
            _LOGGER.info("Found %d location(s)", len(data))
            return data
        else:
            _LOGGER.warning("Unexpected locations response format: %s", type(data))
            return []
    
    async def get_devices(self, location_id: int) -> List[Dict[str, Any]]:
        """
        Get all devices for a location
        
        Args:
            location_id: Location ID (can be found from user profile)
            
        Returns:
            List of device dictionaries
        """
        if not self._session_id:
            raise SchluterAuthenticationError("Not connected. Call connect() first")
        
        url = f"{BASE_URL}devices"
        params = {
            "includedLocationChildren": "true",
            "location$id": location_id
        }
        
        data = await self._request("GET", url, params=params)
        
        if isinstance(data, list):
            return data
        return data.get("devices", [])
    
    async def get_thermostat_status(self, device_id: int) -> SchluterThermostat:
        """
        Get complete status of a thermostat
        
        Args:
            device_id: Device ID
            
        Returns:
            SchluterThermostat object with all current values
        """
        if not self._session_id:
            raise SchluterAuthenticationError("Not connected")
        
        url = f"{BASE_URL}device/{device_id}/attribute"
        
        # Request all available attributes
        attributes = [
            "setpointMode",
            "roomSetpoint",
            "roomSetpointMin",
            "roomSetpointMax",
            "roomTemperatureDisplay",
            "outputPercentDisplay",
            "occupancyMode",
            "gfciStatus",
            "airFloorMode",
            "floorSetpointPwm",
            "floorSetpointPwmMin",
            "floorSetpointPwmMax"
        ]
        
        params = {"attributes": ",".join(attributes)}
        
        data = await self._request("GET", url, params=params)
        
        # Parse response into SchluterThermostat object
        thermostat = SchluterThermostat(
            device_id=device_id,
            name=f"Device {device_id}",  # Will be updated from device list
            current_temp=data.get("roomTemperatureDisplay", {}).get("value"),
            target_temp=data.get("roomSetpoint"),
            min_temp=data.get("roomSetpointMin", 5.0),
            max_temp=data.get("roomSetpointMax", 33.0),
            setpoint_mode=data.get("setpointMode"),
            occupancy_mode=data.get("occupancyMode"),
            heating=(data.get("outputPercentDisplay", {}).get("percent", 0) > 0),
            heating_percent=data.get("outputPercentDisplay", {}).get("percent", 0),
            air_floor_mode=data.get("airFloorMode"),
            gfci_status=data.get("gfciStatus"),
            floor_setpoint_pwm=data.get("floorSetpointPwm"),
            temp_display_status=data.get("roomTemperatureDisplay", {}).get("status")
        )
        
        return thermostat
    
    async def set_temperature(self, device_id: int, temperature: float) -> bool:
        """
        Set target temperature for a device
        
        Args:
            device_id: Device ID
            temperature: Target temperature in Celsius
            
        Returns:
            True if successful
        """
        if not self._session_id:
            raise SchluterAuthenticationError("Not connected")
        
        url = f"{BASE_URL}device/{device_id}/attribute"
        
        payload = {
            "roomSetpoint": temperature
        }
        
        data = await self._request("PUT", url, json=payload)
        
        # Verify the temperature was set
        if data.get("roomSetpoint") == temperature:
            _LOGGER.info("Set temperature to %s°C for device %s", temperature, device_id)
            return True
        _LOGGER.warning(
            "Temperature mismatch. Requested: %s, Got: %s",
            temperature, data.get("roomSetpoint"),
        )
        return False
    
    async def set_mode(self, device_id: int, mode: str) -> bool:
        """
        Set operating mode for a device
        
        Args:
            device_id: Device ID
            mode: "manual" or "schedule"
            
        Returns:
            True if successful
        """
        if mode not in ["manual", "schedule"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'manual' or 'schedule'")
        
        if not self._session_id:
            raise SchluterAuthenticationError("Not connected")
        
        url = f"{BASE_URL}device/{device_id}/attribute"
        
        payload = {
            "setpointMode": mode
        }
        
        await self._request("PUT", url, json=payload)
        _LOGGER.info("Set mode to '%s' for device %s", mode, device_id)
        return True
    
    async def set_occupancy_mode(self, device_id: int, occupancy: str) -> bool:
        """
        Set occupancy mode (home/away) for a device
        
        Args:
            device_id: Device ID
            occupancy: "home" or "away"
            
        Returns:
            True if successful
        """
        if occupancy not in ["home", "away"]:
            raise ValueError(f"Invalid occupancy: {occupancy}. Must be 'home' or 'away'")
        
        if not self._session_id:
            raise SchluterAuthenticationError("Not connected")
        
        url = f"{BASE_URL}device/{device_id}/attribute"
        
        payload = {
            "occupancyMode": occupancy
        }
        
        await self._request("PUT", url, json=payload)
        _LOGGER.info("Set occupancy to '%s' for device %s", occupancy, device_id)
        return True
    
    async def logout(self) -> bool:
        """
        Logout and invalidate session
        
        Returns:
            True if successful
        """
        if not self._session_id:
            return True
        
        # Clear session locally
        self._session_id = None
        self._access_token = None
        _LOGGER.info("Logged out")
        return True



