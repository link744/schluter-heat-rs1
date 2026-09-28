"""Offline verification of the session-expiry recovery fix for schluter_heat.

Stubs the homeassistant package (not installed in this env), drives the
real SchluterDataUpdateCoordinator + real SchluterAPI against a fake
aiohttp session, and asserts:

1. Happy path: login + normal polls return parsed device data.
2. Session expiry (USRSESSEXP, HTTP 200 + error body): coordinator re-logs
   in exactly once and the retry succeeds -> no UpdateFailed.
3. Dead refresh token: relogin raises SchluterAuthenticationError ->
   UpdateFailed, reauth flow initiated exactly once, no recursion.
4. Transport/API error during device discovery -> UpdateFailed.
5. api._request classifies: USRSESSEXP body -> SchluterSessionExpired;
   ACCSESSEXC body -> SchluterSessionExpired (account session expired,
   also recovered by re-login); UNKNOWNERR body -> SchluterAPIError;
   401 -> SchluterSessionExpired when a refresh token exists.
"""
import asyncio
import json
import logging
import sys
import types
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------- stub HA
def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

ha = _mod("homeassistant")
ha_config_entries = _mod("homeassistant.config_entries")
ha_config_entries.ConfigEntry = MagicMock(name="ConfigEntry")
ha_const = _mod("homeassistant.const")
class Platform:
    CLIMATE = "climate"
    SENSOR = "sensor"
ha_const.Platform = Platform
ha_core = _mod("homeassistant.core")
ha_core.HomeAssistant = MagicMock(name="HomeAssistant")
_mod("homeassistant.helpers")
ha_aiohttp = _mod("homeassistant.helpers.aiohttp_client")
ha_aiohttp.async_get_clientsession = MagicMock()
ha_update = _mod("homeassistant.helpers.update_coordinator")

class DataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass

class UpdateFailed(Exception):
    pass

ha_update.DataUpdateCoordinator = DataUpdateCoordinator
ha_update.UpdateFailed = UpdateFailed

# ---------------------------------------------------------------- fake aiohttp
class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload or {})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """Route list: (url_substring, FakeResponse) or (url_substring, Exception)."""

    def __init__(self):
        self.routes = []
        self.calls = []

    def add(self, substr, response_or_exc):
        self.routes.append((substr, response_or_exc))

    def _match(self, url):
        for substr, r in self.routes:
            if substr in url:
                return r
        return FakeResponse(200, {"ok": True})

    def request(self, method, url, **kwargs):
        # Mirrors aiohttp: a regular call that yields an async context manager.
        self.calls.append((method, url))
        r = self._match(url)
        return _cm(r)

def _cm(value_or_exc):
    class _Ctx:
        async def __aenter__(self):
            if isinstance(value_or_exc, Exception):
                raise value_or_exc
            return value_or_exc
        async def __aexit__(self, *a):
            return False
    return _Ctx()

def _route(payload, status=200):
    """Return a stand-in for session.request that yields a FakeResponse."""
    def request(method, url, **kwargs):
        return _cm(FakeResponse(status, payload))
    return request

# ---------------------------------------------------------------- import target
sys.path.insert(0, "/home/link744/.hermes/kanban/workspaces/t_50ae073f/schluter-heat-rs1")
from schluter_heat.api import (  # noqa: E402
    SchluterAPI,
    SchluterAPIError,
    SchluterAuthenticationError,
    SchluterSessionExpired,
    SchluterThermostat,
)
from schluter_heat import SchluterDataUpdateCoordinator  # noqa: E402

LOCATION = 12345
DEVICE_ID = 987654
REFRESH = "good-refresh-token"

def make_entry():
    entry = MagicMock(name="ConfigEntry")
    entry.data = {"refresh_token": REFRESH, "location_id": LOCATION}
    entry.entry_id = "test-entry"
    return entry

def make_coordinator(entry):
    api = SchluterAPI(FakeSession())
    coord = SchluterDataUpdateCoordinator(
        MagicMock(name="hass"), api=api, location_id=LOCATION, entry=entry
    )
    coord.hass = MagicMock(name="hass")
    return coord

OK_STATUS = {
    "roomTemperatureDisplay": {"value": 21.5, "status": "ok"},
    "roomSetpoint": 22.0,
    "roomSetpointMin": 5.0,
    "roomSetpointMax": 33.0,
    "setpointMode": "manual",
    "occupancyMode": "home",
    "outputPercentDisplay": {"percent": 35},
    "gfciStatus": "ok",
    "airFloorMode": "floor",
    "floorSetpointPwm": 55,
}

async def test_happy_path():
    coord = make_coordinator(make_entry())
    api = coord.api
    api._refresh_token = REFRESH
    api._session_id = "sess-1"
    async def devices(location_id):
        return [{"id": DEVICE_ID, "name": "Bathroom", "locationId": LOCATION}]
    api.get_devices = devices
    async def status(device_id):
        st = SchluterThermostat(device_id=DEVICE_ID, name="Bathroom")
        st.current_temp = OK_STATUS["roomTemperatureDisplay"]["value"]
        st.target_temp = OK_STATUS["roomSetpoint"]
        st.heating_percent = OK_STATUS["outputPercentDisplay"]["percent"]
        st.setpoint_mode = "manual"
        return st
    api.get_thermostat_status = status

    data = await coord._async_update_data()
    assert DEVICE_ID in data and data[DEVICE_ID].current_temp == 21.5
    assert data[DEVICE_ID].heating_percent == 35
    print("PASS test_happy_path")

async def test_expiry_recovers():
    """USRSESSEXP on poll -> exactly one relogin -> retry succeeds."""
    coord = make_coordinator(make_entry())
    api = coord.api
    api._refresh_token = REFRESH
    api._session_id = "sess-1"
    async def devices(location_id):
        return [{"id": DEVICE_ID, "name": "Bathroom"}]
    api.get_devices = devices

    attempts = {"n": 0}
    async def flaky_status(device_id):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise SchluterSessionExpired("expired (code USRSESSEXP)")
        st = SchluterThermostat(device_id=DEVICE_ID, name="Bathroom")
        st.current_temp = 21.5
        return st
    api.get_thermostat_status = flaky_status

    relogins = {"n": 0}
    original_relogin = coord._relogin
    async def counting_relogin():
        relogins["n"] += 1
        await original_relogin()
    coord._relogin = counting_relogin

    data = await coord._async_update_data()
    assert DEVICE_ID in data and data[DEVICE_ID].current_temp == 21.5
    assert relogins["n"] == 1
    print("PASS test_expiry_recovers relogin=%d" % relogins["n"])

async def test_dead_token_reauth_once():
    """Dead refresh token -> UpdateFailed, reauth flow fired exactly once."""
    entry = make_entry()
    coord = make_coordinator(entry)
    reauth = {"n": 0}
    tasks = []
    async def fake_init(domain, context=None, data=None):
        reauth["n"] += 1
    entry_hass = MagicMock(name="hass")
    entry_hass.config_entries.flow.async_init = fake_init
    entry_hass.async_create_task = tasks.append
    coord.hass = entry_hass
    coord.devices = {DEVICE_ID: {"id": DEVICE_ID, "name": "Bathroom"}}

    async def dead_status(device_id):
        raise SchluterSessionExpired("expired (code USRSESSEXP)")
    coord.api.get_thermostat_status = dead_status
    async def dead_login(token):
        raise SchluterAuthenticationError("refresh token rejected")
    coord.api.login = dead_login

    try:
        await coord._async_update_data()
        raise AssertionError("expected UpdateFailed")
    except UpdateFailed:
        pass
    for t in tasks:
        await t
    assert reauth["n"] == 1, "reauth should fire exactly once, got %d" % reauth["n"]
    print("PASS test_dead_token_reauth_once reauth=%d" % reauth["n"])

async def test_relogin_failure_routes_to_reauth():
    """Session expired, and the re-login ALSO fails (refresh token dead)
    -> UpdateFailed + reauth fired exactly once."""
    entry = make_entry()
    coord = make_coordinator(entry)
    reauth = {"n": 0}
    tasks = []
    async def fake_init(domain, context=None, data=None):
        reauth["n"] += 1
    hass_mock = MagicMock(name="hass")
    hass_mock.config_entries.flow.async_init = fake_init
    hass_mock.async_create_task = tasks.append
    coord.hass = hass_mock
    coord.devices = {DEVICE_ID: {"id": DEVICE_ID, "name": "Bathroom"}}

    async def expired_status(device_id):
        raise SchluterSessionExpired("expired (code USRSESSEXP)")
    coord.api.get_thermostat_status = expired_status

    async def dead_login(token):
        raise SchluterAuthenticationError("refresh token rejected (USRSESSEXP)")
    coord.api.login = dead_login

    try:
        await coord._async_update_data()
        raise AssertionError("expected UpdateFailed")
    except UpdateFailed:
        pass
    for t in tasks:
        await t
    assert reauth["n"] == 1, "reauth should fire exactly once, got %d" % reauth["n"]
    print("PASS test_relogin_failure_routes_to_reauth reauth=%d" % reauth["n"])

async def test_discovery_error_updatefailed():
    coord = make_coordinator(make_entry())
    async def boom(location_id):
        raise SchluterAPIError("connection reset")
    coord.api.get_devices = boom
    try:
        await coord._async_update_data()
        raise AssertionError("expected UpdateFailed")
    except UpdateFailed:
        pass
    print("PASS test_discovery_error_updatefailed")

async def test_request_classification():
    """_request must classify the HTTP-200 error-body cases correctly."""
    # 1. USRSESSEXP body -> SchluterSessionExpired
    api = SchluterAPI(FakeSession())
    api._refresh_token = "rt"
    api._session.request = _route({"error": {"code": "USRSESSEXP"}})
    try:
        await api._request("GET", "https://schluterditraheat.com/api/locations")
        raise AssertionError("expected SchluterSessionExpired")
    except SchluterSessionExpired:
        pass

    # 2. ACCSESSEXC body ("account session expired") is ALSO session-recoverable
    #    (its code contains SESS, so re-login applies) -> SchluterSessionExpired
    api2 = SchluterAPI(FakeSession())
    api2._refresh_token = "rt"
    api2._session.request = _route({"error": {"code": "ACCSESSEXC"}})
    try:
        await api2._request("GET", "https://schluterditraheat.com/api/locations")
        raise AssertionError("expected SchluterSessionExpired")
    except SchluterSessionExpired:
        pass

    # 3. Generic non-session API error code -> SchluterAPIError, not session-expired
    api3 = SchluterAPI(FakeSession())
    api3._refresh_token = "rt"
    api3._session.request = _route({"error": {"code": "INVALARG"}})
    try:
        await api3._request("GET", "https://schluterditraheat.com/api/locations")
        raise AssertionError("expected SchluterAPIError")
    except SchluterSessionExpired:
        raise AssertionError("INVALARG must not be session-expired")
    except SchluterAPIError:
        pass

    # 3. HTTP 401 with a refresh token present -> SchluterSessionExpired
    api3 = SchluterAPI(FakeSession())
    api3._refresh_token = "rt"
    api3._session.request = _route(None, status=401)
    try:
        await api3._request("GET", "https://schluterditraheat.com/api/locations")
        raise AssertionError("expected SchluterSessionExpired")
    except SchluterSessionExpired:
        pass

    # 4. 401 with NO refresh token -> plain SchluterAuthenticationError
    api4 = SchluterAPI(FakeSession())
    api4._session.request = _route(None, status=401)
    try:
        await api4._request("GET", "https://schluterditraheat.com/api/locations")
        raise AssertionError("expected SchluterAuthenticationError")
    except SchluterSessionExpired:
        raise AssertionError("no refresh token => must not be session-expired")
    except SchluterAuthenticationError:
        pass
    print("PASS test_request_classification")

async def main():
    await test_happy_path()
    await test_expiry_recovers()
    await test_dead_token_reauth_once()
    await test_discovery_error_updatefailed()
    await test_request_classification()
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(main())
