"""Binary sensor platform for the Otto Wilde G32 Grill."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_TYPES = {
    "firebox_open": {"name": "Firebox", "device_class": BinarySensorDeviceClass.OPENING},
    "light_on": {"name": "Light", "device_class": BinarySensorDeviceClass.LIGHT},
    "gas_low": {"name": "Gas Low", "device_class": BinarySensorDeviceClass.PROBLEM},
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor entities for all grills."""
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for grill in api_client.grills:
        for sensor_id, config in BINARY_SENSOR_TYPES.items():
            entities.append(G32BinarySensor(api_client, grill, sensor_id, config))

    async_add_entities(entities)

class G32BinarySensor(BinarySensorEntity):
    """Representation of an Otto Wilde G32 binary sensor."""

    def __init__(
        self,
        api_client: OttoWildeG32ApiClient,
        grill_info: dict,
        sensor_id: str,
        config: dict,
    ):
        """Initialize the binary sensor."""
        self._api_client = api_client
        self._sensor_id = sensor_id
        self._serial_number = grill_info["serialNumber"]
        devicenickname = grill_info.get("nickname", f"G32 {self._serial_number[:6]}")
        
        self._attr_unique_id = f"{self._serial_number}_{self._sensor_id}"
        sanitized_nickname = devicenickname.lower().replace(' ', '_').replace('-', '_')
        self.entity_id = f"binary_sensor.{sanitized_nickname}_{self._sensor_id}"
        self._attr_name = config["name"]
        self._attr_device_class = config.get("device_class")
        self._attr_is_on = None
        self._attr_should_poll = False

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
        )

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._sensor_id == "firebox_open":
            return "mdi:window-opened" if self.is_on else "mdi:window-closed"
        if self._sensor_id == "light_on":
            return "mdi:wall-sconce-flat"
        return None

    @callback
    def _handle_update(self, data: dict[str, Any]) -> None:
        """Handle data updates from the TCP stream."""
        # The key from the API is still 'lid_open', we just map it to our new sensor_id
        api_key = "lid_open" if self._sensor_id == "firebox_open" else self._sensor_id
        
        if api_key in data:
            self._attr_is_on = data[api_key]
            self.async_write_ha_state()
    
    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""
        self.async_on_remove(
            self._api_client.register_update_callback(self._serial_number, self._handle_update)
        )

