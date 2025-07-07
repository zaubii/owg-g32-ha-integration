"""API client for Otto Wilde G32 Grill."""
import asyncio
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List

from aiohttp import ClientSession, ClientError

from homeassistant.core import HomeAssistant

from .const import (
    GRILLS_ENDPOINT, LOGIN_ENDPOINT, TCP_HOST, TCP_PORT, HEARTBEAT_TIMEOUT_SECONDS,
    RAPID_RETRY_ATTEMPTS, RAPID_RETRY_DELAY_SECONDS, INITIAL_RETRY_DELAY_SECONDS,
    MAX_RETRY_DELAY_SECONDS, OVERALL_TIMEOUT_MINUTES
)

_LOGGER = logging.getLogger(__name__)

PACKET_HEADER = b'\xa3\x3a'
PACKET_SIZE = 51

class OttoWildeG32ApiClient:
    """Handles all communication with the Otto Wilde API and TCP sockets."""

    def __init__(self, email: str, password: str, session: ClientSession, hass: HomeAssistant):
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._session = session
        self._hass = hass  # Store hass instance to access states
        self._tokens: dict[str, Any] = {}
        self.grills: list[dict[str, Any]] = []
        self.user_info: dict[str, Any] | None = None

        self._tcp_connections: dict[str, dict] = {}
        self._update_callbacks: dict[str, list[Callable]] = {}
        self._state_update_callbacks: dict[str, list[Callable]] = {}
        self._diagnostics_callbacks: dict[str, list[Callable]] = {}
        self._enabled_grills: dict[str, bool] = {}
        
        self._device_trackers: dict[str, str | None] = {}
        self._state_listeners: List[Callable] = []

        self._counters = {
            "api_login_calls": 0,
            "api_grills_calls": 0,
            "tcp_connection_attempts": {},
            "tcp_reconnect_counter": {},
        }
        
        self._synced_global_counters = set()
        self._backoff_start_times: dict[str, datetime | None] = {}
        self._diag_next_connection_attempt: dict[str, datetime | None] = {}

    def register_device_tracker(self, serial_number: str, entity_id: str | None):
        """Register a device_tracker for a grill."""
        self._device_trackers[serial_number] = entity_id

    def add_state_listener_unsubscribe(self, unsubscribe_callback: Callable):
        """Store the unsubscribe callback for a state listener."""
        self._state_listeners.append(unsubscribe_callback)

    def clear_state_listeners(self):
        """Unsubscribe from all state listeners."""
        for unsubscribe in self._state_listeners:
            unsubscribe()
        self._state_listeners.clear()

    def _is_device_tracker_home(self, serial_number: str) -> bool:
        """Check if the grill's assigned device_tracker is 'home'."""
        entity_id = self._device_trackers.get(serial_number)
        if not entity_id:
            return True  # No tracker assigned, always allow connection attempts

        state = self._hass.states.get(entity_id)
        if state and state.state == "home":
            _LOGGER.debug("Device tracker %s for grill %s is 'home'.", entity_id, serial_number)
            return True
        
        _LOGGER.debug("Device tracker %s for grill %s is NOT 'home' (state: %s).", entity_id, serial_number, state.state if state else "unknown")
        return False

    async def connect_if_needed(self, serial_number: str):
        """Start a connection for a grill if it's not already connected."""
        if self.is_grill_enabled(serial_number):
            _LOGGER.debug("Connection for grill %s is already enabled/running.", serial_number)
            return
        
        _LOGGER.info("Triggering new connection for grill %s.", serial_number)
        await self.enable_grill(serial_number, True)

    def sync_counter(self, counter_id: str, restored_value: int, serial_number: str | None = None):
        """Syncs the counter with a restored value from Home Assistant."""
        _LOGGER.debug("Sync request for counter '%s' with restored value: %d", counter_id, restored_value)
        if serial_number:
            current_session_value = self._counters[counter_id].get(serial_number, 0)
            self._counters[counter_id][serial_number] = restored_value + current_session_value
        else:
            if counter_id in self._synced_global_counters:
                _LOGGER.debug("Global counter '%s' already synced. Skipping.", counter_id)
                return
            
            current_session_value = self._counters.get(counter_id, 0)
            self._counters[counter_id] = restored_value + current_session_value
            self._synced_global_counters.add(counter_id)
            _LOGGER.debug("Global counter '%s' synced for the first time this session.", counter_id)
        
        _LOGGER.debug("Sync complete for '%s'. New value: %s", counter_id, self._counters[counter_id])

    async def async_get_grill_details(self) -> bool:
        """Fetch all grill details from the API."""
        max_retries = 2
        for attempt in range(max_retries):
            if "access_token" not in self._tokens:
                if not await self.async_login():
                    return False

            _LOGGER.info("Fetching grill details (Attempt %d/%d)", attempt + 1, max_retries)
            self._counters["api_grills_calls"] += 1
            headers = {"Authorization": self._tokens["access_token"]}
            
            try:
                response = await self._session.get(GRILLS_ENDPOINT, headers=headers)
                if response.status in (401, 403):
                    _LOGGER.warning("Token invalid, will attempt to re-login.")
                    self._tokens.clear()
                    if attempt < max_retries - 1:
                        continue 
                    else:
                        _LOGGER.error("Failed to get grill details after re-login attempt.")
                response.raise_for_status()
                self.grills = (await response.json()).get("data", [])
                for grill in self.grills:
                    if serial := grill.get("serialNumber"):
                        self._enabled_grills.setdefault(serial, True)
                        self._counters["tcp_connection_attempts"].setdefault(serial, 0)
                        self._counters["tcp_reconnect_counter"].setdefault(serial, 0)
                self._dispatch_global_diagnostics_update()
                _LOGGER.info("Successfully fetched %d grills", len(self.grills))
                return True 
            except (ClientError, json.JSONDecodeError) as e:
                _LOGGER.error("Failed to get/parse grill details: %s", e)
                break 
        return False

    def _dispatch_data(self, sn: str, data: dict):
        """Dispatches data updates to all registered callbacks for a grill."""
        data["last_data_received"] = datetime.now(timezone.utc)
        for cb in self._update_callbacks.get(sn, []): cb(data)

    async def _tcp_listener_loop(self, grill_info: dict):
        serial_number, pop_key, nickname = grill_info["serialNumber"], grill_info["popKey"], grill_info.get("nickname", grill_info["serialNumber"])
        rapid_retry_count = 0

        while self.is_grill_enabled(serial_number):
            # Check tracker status before any connection attempt
            if not self._is_device_tracker_home(serial_number):
                _LOGGER.info("Device tracker for grill %s is not home. Pausing connection attempts.", nickname)
                await self.enable_grill(serial_number, False)
                break

            self._counters["tcp_connection_attempts"][serial_number] += 1
            self._dispatch_diagnostics_update(serial_number)
            writer, connection_succeeded = None, False
            try:
                _LOGGER.info("Connecting to TCP socket for %s", nickname)
                reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
                payload = json.dumps({"channel": "LISTEN_TO_GRILL", "data": {"grillSerialNumber": serial_number, "pop": pop_key}}) + "\n"
                writer.write(payload.encode("utf-8")); await writer.drain()

                _LOGGER.debug("Waiting for heartbeat from %s", nickname)
                first_packet = await asyncio.wait_for(reader.read(1024), timeout=HEARTBEAT_TIMEOUT_SECONDS)
                
                if not first_packet: _LOGGER.warning("Connection closed by server before first packet for %s.", nickname)
                else:
                    _LOGGER.info("Successfully connected and received first packet from: %s", nickname)
                    connection_succeeded, rapid_retry_count = True, 0
                    self._counters["tcp_reconnect_counter"][serial_number] = 0
                    self._backoff_start_times.pop(serial_number, None); self._diag_next_connection_attempt.pop(serial_number, None)
                    self._dispatch_diagnostics_update(serial_number)
                    
                    buffer = first_packet
                    while self.is_grill_enabled(serial_number):
                        start_index = buffer.find(PACKET_HEADER)
                        if start_index != -1 and len(buffer) >= start_index + PACKET_SIZE:
                            packet = buffer[start_index : start_index + PACKET_SIZE]; buffer = buffer[start_index + PACKET_SIZE:]
                            if parsed_data := self._parse_binary_data(packet): self._dispatch_data(serial_number, parsed_data)
                        else:
                            new_data = await reader.read(1024)
                            if not new_data: _LOGGER.warning("TCP connection closed during operation for: %s", nickname); connection_succeeded = False; break
                            buffer += new_data
            except (ConnectionError, OSError, asyncio.TimeoutError, asyncio.CancelledError) as e:
                if isinstance(e, asyncio.CancelledError): _LOGGER.info("Listener task for %s cancelled.", nickname); break
                _LOGGER.warning("TCP connection failed for %s: %s", nickname, type(e).__name__)
            finally:
                if writer: writer.close(); await writer.wait_closed()

            if connection_succeeded or not self.is_grill_enabled(serial_number):
                if not self.is_grill_enabled(serial_number): break
                continue

            rapid_retry_count += 1
            if rapid_retry_count < RAPID_RETRY_ATTEMPTS:
                _LOGGER.info("Rapid retry %d/%d for %s in %d seconds.", rapid_retry_count, RAPID_RETRY_ATTEMPTS, nickname, RAPID_RETRY_DELAY_SECONDS)
                await asyncio.sleep(RAPID_RETRY_DELAY_SECONDS)
                continue

            if self._backoff_start_times.get(serial_number) is None:
                _LOGGER.warning("Starting long-term backoff for %s.", nickname)
                self._backoff_start_times[serial_number] = datetime.now(timezone.utc)
                self._counters["tcp_reconnect_counter"][serial_number] = 0

            elapsed = datetime.now(timezone.utc) - self._backoff_start_times[serial_number]
            if elapsed > timedelta(minutes=OVERALL_TIMEOUT_MINUTES):
                _LOGGER.error("Grill %s offline for over %d minutes. Disabling connection.", nickname, OVERALL_TIMEOUT_MINUTES)
                self._diag_next_connection_attempt[serial_number] = None
                await self.enable_grill(serial_number, False)
                break

            attempt = self._counters["tcp_reconnect_counter"].get(serial_number, 0)
            delay = min(MAX_RETRY_DELAY_SECONDS, INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt))
            self._diag_next_connection_attempt[serial_number] = datetime.now(timezone.utc) + timedelta(seconds=delay)
            self._counters["tcp_reconnect_counter"][serial_number] = attempt + 1
            
            _LOGGER.info("Backoff attempt %d for %s. Retrying in %.2f seconds.", attempt + 1, nickname, delay)
            self._dispatch_diagnostics_update(serial_number)
            await asyncio.sleep(delay)

    # --- Methods from previous versions, unchanged ---
    async def async_login(self) -> bool:
        _LOGGER.info("Attempting to login to Otto Wilde API")
        self._counters["api_login_calls"] += 1
        self._dispatch_global_diagnostics_update()
        login_payload = {"email": self._email, "password": self._password}
        try:
            response = await self._session.post(LOGIN_ENDPOINT, json=login_payload)
            response.raise_for_status()
            response_data = await response.json()
            data_payload = response_data.get("data", {})
            self._tokens = {"access_token": data_payload.get("accessToken")}
            self.user_info = data_payload.get("user", {})
            _LOGGER.info("Login successful for user: %s", self.user_info.get("nickname"))
            return True
        except ClientError as e:
            _LOGGER.error("API login failed: %s", e)
            return False

    def _parse_binary_data(self, data: bytes) -> dict[str, Any] | None:
        hex_data = data.hex()
        try:
            return {
                "raw_hex_dump": hex_data, "zone_1": self._parse_temp_value(hex_data[12:16]),
                "zone_2": self._parse_temp_value(hex_data[16:20]), "zone_3": self._parse_temp_value(hex_data[20:24]),
                "zone_4": self._parse_temp_value(hex_data[24:28]), "probe_1": self._parse_temp_value(hex_data[28:32]),
                "probe_2": self._parse_temp_value(hex_data[32:36]), "probe_3": self._parse_temp_value(hex_data[36:40]),
                "probe_4": self._parse_temp_value(hex_data[40:44]), "gas_weight": int(hex_data[44:48], 16),
                "lid_open": hex_data[48:50] == "01", "light_on": hex_data[50:52] == "01",
                "gas_level": int(hex_data[62:64], 16), "gas_low": int(hex_data[44:48], 16) < 2200,
            }
        except (ValueError, IndexError): return None

    def _parse_temp_value(self, h: str) -> float | None:
        """Parse temperature value from hex string, handling special invalid values."""
        if not h or len(h) != 4:
            return None
            
        # Normalize to lowercase for consistent comparison
        h_lower = h.lower()
        
        # Check for known invalid/special temperature values
        invalid_patterns = {
            "9600",  # Known invalid pattern from original code
            "ffff",  # Max value, typically indicates sensor disconnected
            "0000",  # Zero value, may indicate sensor error in some contexts
            "ffef",  # Another common invalid pattern
            "feff",  # Byte-swapped invalid pattern
        }
        
        if h_lower in invalid_patterns:
            return None
        
        try:
            # Parse the temperature value: first byte * 10 + second byte / 10
            temp_whole = int(h[:2], 16)
            temp_decimal = int(h[2:], 16)
            
            # Sanity check: temperature should be within reasonable range
            # G32 grill typically operates in range -50°C to 500°C
            calculated_temp = (temp_whole * 10) + (temp_decimal / 10.0)
            
            if calculated_temp < -50 or calculated_temp > 600:
                _LOGGER.debug("Temperature value %s (%.1f°C) outside reasonable range, treating as invalid", h, calculated_temp)
                return None
                
            return calculated_temp
            
        except (ValueError, TypeError) as e:
            _LOGGER.debug("Failed to parse temperature value %s: %s", h, e)
            return None

    def register_update_callback(self, sn: str, cb: Callable) -> Callable:
        self._update_callbacks.setdefault(sn, []).append(cb)
        def unregister(): self._update_callbacks[sn].remove(cb)
        return unregister

    def register_state_callback(self, sn: str, cb: Callable) -> Callable:
        self._state_update_callbacks.setdefault(sn, []).append(cb)
        def unregister(): self._state_update_callbacks[sn].remove(cb)
        return unregister

    def _dispatch_state_update(self, sn: str):
        for cb in self._state_update_callbacks.get(sn, []): cb()

    def register_diagnostics_callback(self, sn: str, cb: Callable) -> Callable:
        self._diagnostics_callbacks.setdefault(sn, []).append(cb)
        def unregister(): self._diagnostics_callbacks[sn].remove(cb)
        return unregister

    def _dispatch_diagnostics_update(self, sn: str):
        data = self.get_diagnostics_data(sn)
        for cb in self._diagnostics_callbacks.get(sn, []): cb(data)

    def _dispatch_global_diagnostics_update(self):
        if not self.grills: return
        for grill in self.grills: self._dispatch_diagnostics_update(grill["serialNumber"])

    def is_grill_enabled(self, sn: str) -> bool: return self._enabled_grills.get(sn, False)

    async def enable_grill(self, sn: str, enable: bool):
        self._enabled_grills[sn] = enable
        if enable:
            self._counters["tcp_reconnect_counter"][sn] = 0
            self._backoff_start_times.pop(sn, None)
            self._diag_next_connection_attempt.pop(sn, None)
            await self._start_listener_for_grill(sn)
        else:
            await self._stop_listener_for_grill(sn)
        self._dispatch_state_update(sn)
        self._dispatch_diagnostics_update(sn)

    async def async_start_listeners(self):
        for grill in self.grills:
            if serial := grill.get("serialNumber"):
                if self.is_grill_enabled(serial):
                    await self._start_listener_for_grill(serial)

    async def _start_listener_for_grill(self, sn: str):
        if sn in self._tcp_connections and not self._tcp_connections[sn]["task"].done(): return
        grill_info = next((g for g in self.grills if g["serialNumber"] == sn), None)
        if not grill_info: return
        task = asyncio.create_task(self._tcp_listener_loop(grill_info))
        self._tcp_connections[sn] = {"task": task}

    async def _stop_listener_for_grill(self, sn: str):
        conn = self._tcp_connections.pop(sn, None)
        if conn and "task" in conn and not conn["task"].done():
            conn["task"].cancel()
            try: await conn["task"]
            except asyncio.CancelledError: pass

    async def async_stop_listeners(self):
        self.clear_state_listeners()
        for serial in list(self._tcp_connections.keys()): await self._stop_listener_for_grill(serial)

    def get_diagnostics_data(self, serial_number: str) -> dict[str, Any]:
        return {
            "api_login_calls": self._counters["api_login_calls"],
            "api_grills_calls": self._counters["api_grills_calls"],
            "tcp_connection_attempts": self._counters["tcp_connection_attempts"].get(serial_number, 0),
            "tcp_reconnect_counter": self._counters["tcp_reconnect_counter"].get(serial_number, 0),
            "next_connection_attempt": self._diag_next_connection_attempt.get(serial_number),
        }
