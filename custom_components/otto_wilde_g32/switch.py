"""Switch platform for the Otto Wilde G32 Grill."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch entities for all grills."""
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for grill in api_client.grills:
        entities.append(G32EnableSwitch(api_client, grill))

    async_add_entities(entities)

class G32EnableSwitch(SwitchEntity):
    """Represents the master enable/disable switch for a grill's connection."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_should_poll = False
    _attr_name = "Connection Enabled"
    _attr_icon = "mdi:lan-connect"

    def __init__(self, api_client: OttoWildeG32ApiClient, grill_info: dict):
        """Initialize the switch."""
        self._api_client = api_client
        self._serial_number = grill_info["serialNumber"]
        devicenickname = grill_info.get("nickname", f"G32 {self._serial_number[:6]}")

        self._attr_unique_id = f"{self._serial_number}_connection_enabled"
        sanitized_nickname = devicenickname.lower().replace(' ', '_').replace('-', '_')
        self.entity_id = f"switch.{sanitized_nickname}_connection_enabled"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the grill connection is enabled."""
        return self._api_client.is_grill_enabled(self._serial_number)

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, representing connection status."""
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the grill connection."""
        _LOGGER.info("Enabling connection for grill %s via switch", self._serial_number)
        await self._api_client.enable_grill(self._serial_number, True)
        # The state update is now handled by the callback

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the grill connection."""
        _LOGGER.info("Disabling connection for grill %s via switch", self._serial_number)
        await self._api_client.enable_grill(self._serial_number, False)
        # The state update is now handled by the callback

    @callback
    def _handle_state_update(self) -> None:
        """Handle state updates from the API client (e.g., after timeout)."""
        _LOGGER.debug("Received state update for switch %s, updating HA state", self.entity_id)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""
        self.async_on_remove(
            self._api_client.register_state_callback(self._serial_number, self._handle_state_update)
        )

