"""API client for Otto Wilde G32 Grill."""
import asyncio
import json
import logging
from typing import Any, Callable
from datetime import datetime
from collections import deque

from aiohttp import ClientSession, ClientError

from .const import GRILLS_ENDPOINT, LOGIN_ENDPOINT, TCP_HOST, TCP_PORT

_LOGGER = logging.getLogger(__name__)

PACKET_HEADER = b'\xa3\x3a'
PACKET_SIZE = 51

class OttoWildeG32ApiClient:
    """Handles all communication with the Otto Wilde API and TCP sockets."""

    def __init__(self, email: str, password: str, session: ClientSession):
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._session = session
        self._tokens: dict[str, Any] = {}
        self.grills: list[dict[str, Any]] = []
        self.user_info: dict[str, Any] | None = None
        
        self._tcp_connections: dict[str, dict] = {}
        self._update_callbacks: dict[str, list[Callable]] = {}
        self._enabled_grills: dict[str, bool] = {}
        
        # NEW: Debugging infrastructure
        self._debug_enabled = False
        self._debug_log = deque(maxlen=50) # Store last 50 entries
        self._debug_callbacks: list[Callable] = []
        self.add_log("API Client Initialized.")

    def add_log(self, message: str):
        """Add a message to the debug log if debugging is enabled."""
        if not self._debug_enabled:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self._debug_log.appendleft(log_entry) # Prepend to show newest first
        self._dispatch_debug_update()

    def get_debug_log(self) -> str:
        """Get the formatted debug log."""
        if not self._debug_enabled:
            return "Debug Sensor ist ausgeschaltet."
        if not self._debug_log:
            return "Noch keine Debug-Nachrichten vorhanden."
        return "\n".join(self._debug_log)

    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode."""
        self._debug_enabled = enabled
        if not enabled:
            self._debug_log.clear()
        self.add_log(f"Debug-Modus wurde {'aktiviert' if enabled else 'deaktiviert'}.")
        self._dispatch_debug_update()

    def register_debug_callback(self, callback: Callable) -> Callable:
        """Register a callback for debug log updates."""
        self._debug_callbacks.append(callback)
        def unregister():
            self._debug_callbacks.remove(callback)
        return unregister

    def _dispatch_debug_update(self):
        """Dispatch a debug update to all registered callbacks."""
        for callback in self._debug_callbacks:
            callback()

    async def async_login(self) -> bool:
        """Login to the API and retrieve tokens and user info."""
        self.add_log(f"API Call: POST {LOGIN_ENDPOINT} (Grund: Login)")
        try:
            # ... (rest of the login logic) ...
            return True # on success
        except ClientError as e:
            self.add_log(f"ERROR: API-Login fehlgeschlagen: {e}")
            return False

    async def async_get_grill_details(self) -> bool:
        """Fetch all grill details from the API."""
        self.add_log(f"API Call: GET {GRILLS_ENDPOINT} (Grund: Grill-Details abrufen)")
        try:
            # ... (rest of the get_grill_details logic) ...
            return True # on success
        except (ClientError, json.JSONDecodeError) as e:
            self.add_log(f"ERROR: Grill-Details konnten nicht abgerufen werden: {e}")
            return False

    async def _tcp_listener_loop(self, grill_info: dict):
        """The main loop that connects and listens for data for one grill."""
        serial_number = grill_info.get("serialNumber")
        nickname = grill_info.get("nickname", serial_number)

        while self.is_grill_enabled(serial_number):
            # ...
            try:
                self.add_log(f"TCP: Verbindungsaufbau zu {nickname} ({serial_number})")
                reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
                self.add_log(f"TCP: Verbindung zu {nickname} erfolgreich hergestellt.")
                # ...
                while self.is_grill_enabled(serial_number):
                    new_data = await reader.read(1024)
                    if not new_data:
                        self.add_log(f"TCP: Verbindung zu {nickname} geschlossen (Server-Seite).")
                        break
                    # ...
            except (ConnectionError, OSError, asyncio.CancelledError, asyncio.TimeoutError) as e:
                if isinstance(e, asyncio.CancelledError):
                    self.add_log(f"TCP: Listener-Task für {nickname} abgebrochen.")
                    break 
                self.add_log(f"ERROR: TCP-Verbindungsfehler für {nickname}: {e}")
            except Exception as e:
                self.add_log(f"ERROR: Unerwarteter Fehler im TCP-Loop für {nickname}: {e}")
            
            # ...
# NOTE: This is a partial file showing only the new/changed parts for brevity.
# The full implementation from the previous step is assumed.

