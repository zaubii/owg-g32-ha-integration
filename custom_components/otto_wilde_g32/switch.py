"""Switch platform for the Otto Wilde G32 Grill."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    # Create a switch for each grill
    for grill in api_client.grills:
        entities.append(G32EnableSwitch(api_client, grill))

    # Create a single, global debug switch
    entities.append(G32DebugSwitch(api_client, entry))

    async_add_entities(entities)

class G32EnableSwitch(SwitchEntity):
    """Represents the master enable/disable switch for a grill's connection."""
    # ... (code for this class remains the same) ...
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_should_poll = False

    def __init__(self, api_client: OttoWildeG32ApiClient, grill_info: dict):
        """Initialize the switch."""
        self._api_client = api_client
        self._serial_number = grill_info["serialNumber"]
        devicenickname = grill_info.get("nickname", f"G32 {self._serial_number[:6]}")

        self._attr_unique_id = f"{self._serial_number}_enable_connection"
        sanitized_nickname = devicenickname.lower().replace(' ', '_').replace('-', '_')
        self.entity_id = f"switch.{sanitized_nickname}_verbindung_aktiv"
        self._attr_name = "Verbindung Aktiv"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the grill connection is enabled."""
        return self._api_client.is_grill_enabled(self._serial_number)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the grill connection."""
        _LOGGER.info("Enabling connection for grill %s", self._serial_number)
        await self._api_client.enable_grill(self._serial_number, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the grill connection."""
        _LOGGER.info("Disabling connection for grill %s", self._serial_number)
        await self._api_client.enable_grill(self._serial_number, False)
        self.async_write_ha_state()

class G32DebugSwitch(SwitchEntity):
    """A switch to enable or disable the debug logging sensor."""

    _attr_should_poll = False
    _attr_icon = "mdi:bug"

    def __init__(self, api_client: OttoWildeG32ApiClient, entry: ConfigEntry):
        """Initialize the debug switch."""
        self._api_client = api_client
        self._attr_unique_id = f"{entry.entry_id}_debug_switch"
        self._attr_name = "Otto Wilde G32 Debug Sensor"

    @property
    def is_on(self) -> bool:
        """Return true if debug mode is enabled."""
        return self._api_client._debug_enabled

    def turn_on(self, **kwargs: Any) -> None:
        """Enable debug mode."""
        self._api_client.set_debug_mode(True)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        """Disable debug mode."""
        self._api_client.set_debug_mode(False)
        self.schedule_update_ha_state()

