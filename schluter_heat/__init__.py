"""The Schluter DITRA-HEAT integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SchluterAPI,
    SchluterAPIError,
    SchluterAuthenticationError,
    SchluterSessionExpired,
    SchluterThermostat,
)
from .const import (
    CONF_LOCATION_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Schluter DITRA-HEAT from a config entry."""
    session = async_get_clientsession(hass)
    api = SchluterAPI(session)
    
    # Authenticate
    try:
        await api.login(entry.data[CONF_REFRESH_TOKEN])
    except (SchluterAuthenticationError, SchluterAPIError) as err:
        _LOGGER.error("Failed to authenticate with Schluter API: %s", err)
        return False

    # Create coordinator
    coordinator = SchluterDataUpdateCoordinator(
        hass,
        api=api,
        location_id=entry.data[CONF_LOCATION_ID],
        entry=entry,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SchluterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Schluter data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SchluterAPI,
        location_id: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.api = api
        self.location_id = location_id
        self.devices: dict[int, dict] = {}
        self.config_entry = entry
        self._reauth_in_progress = False
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        """Update data via library.

        Handles session expiry: the Neviweb API expires the session after
        a while, so a single refresh-token login at startup is not enough
        for multi-day operation. A dead session is transparently recovered
        by re-logging in with the stored refresh token (one retry); a dead
        refresh token raises the reauth flow instead.
        """
        try:
            data = await self._async_fetch_devices()
            return data
        except SchluterSessionExpired as err:
            # Session died; refresh token may still be good. Re-login and
            # retry exactly once (no recursion).
            _LOGGER.warning("Schluter session expired, re-logging in: %s", err)
            try:
                await self._relogin()
                data = await self._async_fetch_devices()
            except (SchluterSessionExpired, SchluterAuthenticationError) as retry_err:
                # The stored refresh token could not re-establish a session.
                self._async_schedule_reauth()
                raise UpdateFailed(
                    "Authentication failed. Please update your refresh token."
                ) from retry_err
            _LOGGER.info("Schluter session re-established and data refreshed")
            return data

        except SchluterAuthenticationError as err:
            # Refresh token itself is invalid/expired - trigger reauth flow
            self._async_schedule_reauth()
            raise UpdateFailed(
                "Authentication failed. Please update your refresh token."
            ) from err

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _async_schedule_reauth(self) -> None:
        """Start the reauth config flow once, so the user can paste a
        fresh refresh token."""
        if self._reauth_in_progress:
            return
        self._reauth_in_progress = True
        _LOGGER.error("Refresh token expired or invalid. Triggering reauth flow.")
        entry = self.config_entry
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth", "entry_id": entry.entry_id},
                data=entry.data,
            )
        )

    async def _async_fetch_devices(self) -> dict[int, SchluterThermostat]:
        """Fetch device list (if needed) and current status for all devices."""
        # Get list of devices (only on first call or if empty)
        if not self.devices:
            device_list = await self.api.get_devices(self.location_id)
            for device in device_list:
                self.devices[device["id"]] = device
            _LOGGER.debug("Discovered %d devices", len(self.devices))

        # Get status for all devices
        data: dict[int, SchluterThermostat] = {}
        for device_id in self.devices:
            try:
                status = await self.api.get_thermostat_status(device_id)
                # Update device name from initial discovery
                status.name = self.devices[device_id].get("name", f"Device {device_id}")
                data[device_id] = status
            except SchluterAPIError as err:
                _LOGGER.warning("Failed to update device %s: %s", device_id, err)
                continue

        return data

    async def _relogin(self) -> None:
        """Re-establish the API session using the stored refresh token."""
        refresh_token = self.config_entry.data[CONF_REFRESH_TOKEN]
        await self.api.login(refresh_token)
        _LOGGER.info("Schluter session re-established")
