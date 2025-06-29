"""Sensor platform for the Otto Wilde G32 Grill."""
import logging
from typing import Any
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Definitions for sensors that get real-time updates via TCP
TCP_SENSOR_TYPES = {
    "t1": {"name": "Probe 1", "device_class": SensorDeviceClass.TEMPERATURE},
    "t2": {"name": "Probe 2", "device_class": SensorDeviceClass.TEMPERATURE},
    "t3": {"name": "Probe 3", "device_class": SensorDeviceClass.TEMPERATURE},
    "t4": {"name": "Probe 4", "device_class": SensorDeviceClass.TEMPERATURE},
    "ex1": {"name": "Zone 1", "device_class": SensorDeviceClass.TEMPERATURE},
    "ex2": {"name": "Zone 2", "device_class": SensorDeviceClass.TEMPERATURE},
    "ex3": {"name": "Zone 3", "device_class": SensorDeviceClass.TEMPERATURE},
    "ex4": {"name": "Zone 4", "device_class": SensorDeviceClass.TEMPERATURE},
    "gas_weight_g": {"name": "Gas Weight", "device_class": SensorDeviceClass.WEIGHT, "unit": UnitOfMass.GRAMS},
    "gas_level_percent": {"name": "Gas Level", "device_class": SensorDeviceClass.BATTERY, "unit": PERCENTAGE},
    "raw_hex": {"name": "Raw Hex Dump", "entity_category": EntityCategory.DIAGNOSTIC, "enabled_by_default": False},
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities for all grills."""
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for grill in api_client.grills:
        # Create real-time TCP sensors
        for sensor_id, config in TCP_SENSOR_TYPES.items():
            entities.append(G32TcpSensor(api_client, grill, sensor_id, config))
            
        # Create static API-based sensors
        gasbuddy_info = grill.get("gasbuddyInfo", {})
        if tank_installed_date := gasbuddy_info.get("tankInstalledDate"):
            entities.append(G32StaticSensor(
                grill, 
                "gasflasche_installiert", 
                "Gasflasche Installiert", 
                datetime.fromisoformat(tank_installed_date.replace("Z", "+00:00")),
                SensorDeviceClass.TIMESTAMP
            ))

        # Add new GasBuddy timestamp sensors
        if ts_gas_consumed := gasbuddy_info.get("tsGasConsumed"):
            entities.append(G32StaticSensor(
                grill,
                "gasbuddy_letzter_verbrauch",
                "GasBuddy letzter Verbrauch",
                datetime.fromisoformat(ts_gas_consumed.replace("Z", "+00:00")),
                SensorDeviceClass.TIMESTAMP
            ))

        if ts_last_modified := gasbuddy_info.get("tsLastModified"):
            entities.append(G32StaticSensor(
                grill,
                "gasbuddy_letzter_wert",
                "GasBuddy letzter Wert",
                datetime.fromisoformat(ts_last_modified.replace("Z", "+00:00")),
                SensorDeviceClass.TIMESTAMP
            ))

    async_add_entities(entities)

class G32BaseSensor(SensorEntity):
    """Base class for Otto Wilde G32 sensors."""

    def __init__(self, grill_info: dict, entity_id_suffix: str, name_suffix: str):
        """Initialize the base sensor."""
        serial_number = grill_info["serialNumber"]
        devicenickname = grill_info.get("nickname", f"G32 {serial_number[:6]}")
        
        self._attr_unique_id = f"{serial_number}_{entity_id_suffix}"
        # Use a sanitized version of the nickname for the entity_id
        sanitized_nickname = devicenickname.lower().replace(' ', '_').replace('-', '_')
        self.entity_id = f"sensor.{sanitized_nickname}_{entity_id_suffix}"
        self._attr_name = f"{name_suffix}" # HA will prefix with device name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
        )

class G32TcpSensor(G32BaseSensor):
    """Representation of a sensor that updates via TCP stream."""

    def __init__(
        self,
        api_client: OttoWildeG32ApiClient,
        grill_info: dict,
        sensor_id: str,
        config: dict,
    ):
        """Initialize the TCP sensor."""
        super().__init__(grill_info, sensor_id, config["name"])
        self._api_client = api_client
        self._sensor_id = sensor_id
        self._serial_number = grill_info["serialNumber"]
        
        self._attr_device_class = config.get("device_class")
        self._attr_entity_category = config.get("entity_category")
        self._attr_entity_registry_enabled_by_default = config.get("enabled_by_default", True)
        self._attr_native_unit_of_measurement = config.get("unit")
        
        if self.device_class in (SensorDeviceClass.TEMPERATURE, SensorDeviceClass.WEIGHT, SensorDeviceClass.BATTERY):
            self._attr_state_class = SensorStateClass.MEASUREMENT
        
        if self.device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        
        self._attr_should_poll = False

    @callback
    def _handle_update(self, data: dict[str, Any]) -> None:
        """Handle data updates from the TCP stream."""
        if self._sensor_id in data:
            self._attr_native_value = data[self._sensor_id]
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added."""
        self.async_on_remove(
            self._api_client.register_update_callback(self._serial_number, self._handle_update)
        )

class G32StaticSensor(G32BaseSensor):
    """Representation of a sensor with a static value from the API."""
    def __init__(
        self,
        grill_info: dict,
        entity_id_suffix: str,
        name_suffix: str,
        state: Any,
        device_class: SensorDeviceClass | None = None,
    ):
        """Initialize the static sensor."""
        super().__init__(grill_info, entity_id_suffix, name_suffix)
        self._attr_native_value = state
        self._attr_device_class = device_class
        self._attr_should_poll = False

