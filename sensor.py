"""Sensor platform for the Otto Wilde G32 Grill."""
import logging
from typing import Any
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TCP_SENSOR_TYPES = {
    "zone_1": {"name": "Zone 1", "device_class": SensorDeviceClass.TEMPERATURE},
    "zone_2": {"name": "Zone 2", "device_class": SensorDeviceClass.TEMPERATURE},
    "zone_3": {"name": "Zone 3", "device_class": SensorDeviceClass.TEMPERATURE},
    "zone_4": {"name": "Zone 4", "device_class": SensorDeviceClass.TEMPERATURE},
    "probe_1": {"name": "Probe 1", "device_class": SensorDeviceClass.TEMPERATURE},
    "probe_2": {"name": "Probe 2", "device_class": SensorDeviceClass.TEMPERATURE},
    "probe_3": {"name": "Probe 3", "device_class": SensorDeviceClass.TEMPERATURE},
    "probe_4": {"name": "Probe 4", "device_class": SensorDeviceClass.TEMPERATURE},
    "gas_weight": {"name": "Gas Weight", "device_class": SensorDeviceClass.WEIGHT, "unit": UnitOfMass.GRAMS},
    "gas_level": {"name": "Gas Level", "device_class": SensorDeviceClass.BATTERY, "unit": PERCENTAGE},
    "raw_hex_dump": {"name": "Raw Hex Dump", "entity_category": EntityCategory.DIAGNOSTIC, "enabled_by_default": False},
}
STATIC_SENSOR_TYPES = {
    "gas_installed": {"key": "tankInstalledDate", "name": "New Gas Installed", "device_class": SensorDeviceClass.TIMESTAMP},
    "gas_changed": {"key": "tsGasConsumed", "name": "Gas Setup Changed", "device_class": SensorDeviceClass.TIMESTAMP},
    "gas_consumed": {"key": "tsLastModified", "name": "Gas Consumed", "device_class": SensorDeviceClass.TIMESTAMP},
}
GASBUDDY_STATIC_SENSOR_TYPES = {
    "gas_original_capacity": {"key": "gasCapacity", "name": "Gas Original Capacity", "device_class": SensorDeviceClass.WEIGHT, "unit": UnitOfMass.KILOGRAMS},
    "gas_tara_weight": {"key": "tareWeight", "name": "Gas Tara Weight", "device_class": SensorDeviceClass.WEIGHT, "unit": UnitOfMass.KILOGRAMS},
}
LIVENESS_SENSOR_TYPES = {
    # CHANGE: Removed "G32" from the friendly name for consistency
    "last_data_received": {"name": "Last Data Received", "device_class": SensorDeviceClass.TIMESTAMP, "icon": "mdi:timeline-clock-outline"},
}
DIAGNOSTIC_SENSOR_TYPES = {
    "api_login_calls": {"name": "API Login Calls", "icon": "mdi:api"},
    "api_grills_calls": {"name": "API Grills Calls", "icon": "mdi:api"},
    "tcp_connection_attempts": {"name": "TCP Connection Attempts", "icon": "mdi:network-outline"},
    "tcp_reconnect_counter": {"name": "TCP Backoff Counter", "icon": "mdi:timer-sand"},
    "next_connection_attempt": {"name": "Next Backoff Attempt", "device_class": SensorDeviceClass.TIMESTAMP},
}
# Define which counters are grill-specific for state restoration
GRILL_SPECIFIC_COUNTERS = ["tcp_connection_attempts", "tcp_reconnect_counter"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor entities for all grills."""
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for grill in api_client.grills:
        # TCP-based sensors
        for sensor_id, config in TCP_SENSOR_TYPES.items():
            entities.append(G32TcpSensor(api_client, grill, sensor_id, config))
        
        gasbuddy_info = grill.get("gasbuddyInfo", {})
        
        # Static timestamp sensors
        for sensor_id, config in STATIC_SENSOR_TYPES.items():
            if value := gasbuddy_info.get(config["key"]):
                dt_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                entities.append(G32StaticSensor(grill, sensor_id, config["name"], dt_value, config["device_class"]))
        
        # Static GasBuddy weight sensors
        for sensor_id, config in GASBUDDY_STATIC_SENSOR_TYPES.items():
            if (value := gasbuddy_info.get(config["key"])) is not None:
                entities.append(G32StaticSensor(
                    grill_info=grill,
                    entity_id_suffix=sensor_id,
                    name_suffix=config["name"],
                    state=value,
                    device_class=config["device_class"],
                    entity_category=config.get("entity_category"),
                    unit=config.get("unit")
                ))

        # Liveness sensor
        for sensor_id, config in LIVENESS_SENSOR_TYPES.items():
            entities.append(G32LivenessSensor(api_client, grill, sensor_id, config))

        # Diagnostic sensors
        for sensor_id, config in DIAGNOSTIC_SENSOR_TYPES.items():
            entities.append(G32DiagnosticSensor(api_client, grill, sensor_id, config))
            
    async_add_entities(entities)

class G32BaseSensor(SensorEntity):
    """Base class for Otto Wilde G32 sensors."""
    def __init__(self, grill_info: dict, entity_id_suffix: str, name_suffix: str):
        self._serial_number = grill_info["serialNumber"]
        devicenickname = grill_info.get("nickname", f"G32 {self._serial_number[:6]}")
        self._attr_unique_id = f"{self._serial_number}_{entity_id_suffix}"
        self.entity_id = f"sensor.{devicenickname.lower().replace(' ', '_').replace('-', '_')}_{entity_id_suffix}"
        self._attr_name = name_suffix
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._serial_number)})

class G32TcpSensor(G32BaseSensor):
    """Representation of a sensor that updates via TCP stream."""
    def __init__(self, api_client: OttoWildeG32ApiClient, grill_info: dict, sensor_id: str, config: dict):
        super().__init__(grill_info, sensor_id, config["name"])
        self._api_client, self._sensor_id = api_client, sensor_id
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
    def _handle_update(self, data: dict[str, Any]):
        if self._sensor_id in data: self._attr_native_value = data[self._sensor_id]; self.async_write_ha_state()
    async def async_added_to_hass(self): self.async_on_remove(self._api_client.register_update_callback(self._serial_number, self._handle_update))

class G32StaticSensor(G32BaseSensor):
    """Representation of a sensor with a static value from the API."""
    def __init__(self, grill_info: dict, entity_id_suffix: str, name_suffix: str, state: Any, device_class: SensorDeviceClass | None = None, entity_category: EntityCategory | None = None, unit: str | None = None):
        super().__init__(grill_info, entity_id_suffix, name_suffix)
        self._attr_native_value = state
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_native_unit_of_measurement = unit
        self._attr_should_poll = False
        if self.device_class == SensorDeviceClass.WEIGHT:
            self._attr_state_class = SensorStateClass.MEASUREMENT

class G32LivenessSensor(G32BaseSensor, RestoreEntity):
    """Representation of a sensor that indicates data reception liveness."""
    _attr_should_poll = False

    def __init__(self, api_client: OttoWildeG32ApiClient, grill_info: dict, sensor_id: str, config: dict):
        super().__init__(grill_info, sensor_id, config["name"])
        self._api_client = api_client
        self._sensor_id = sensor_id
        self._attr_device_class = config.get("device_class")
        self._attr_icon = config.get("icon")
        self._attr_native_value = None

    @callback
    def _handle_update(self, data: dict[str, Any]):
        """Handle data updates from the API client."""
        if self._sensor_id in data:
            self._attr_native_value = data[self._sensor_id]
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""
        await super().async_added_to_hass()
        # Restore the last known timestamp
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            self._attr_native_value = dt_util.parse_datetime(last_state.state)

        # This sensor gets its updates from the general data dispatch
        self.async_on_remove(
            self._api_client.register_update_callback(self._serial_number, self._handle_update)
        )

class G32DiagnosticSensor(G32BaseSensor, RestoreEntity):
    """Represents a diagnostic sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, api_client: OttoWildeG32ApiClient, grill_info: dict, sensor_id: str, config: dict):
        super().__init__(grill_info, sensor_id, config["name"])
        self._api_client, self._sensor_id = api_client, sensor_id
        self._attr_icon = config.get("icon")
        self._attr_device_class = config.get("device_class")
        # Set state class for counters
        if "Calls" in config["name"] or "Attempts" in config["name"] or "Counter" in config["name"]:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT if self.device_class != SensorDeviceClass.TIMESTAMP else None

    @callback
    def _handle_diagnostics_update(self, data: dict[str, Any]):
        if self._sensor_id in data:
            value = data[self._sensor_id]
            # Ensure timestamps are timezone-aware for HA
            if isinstance(value, datetime) and value.tzinfo is None:
                self._attr_native_value = value.replace(tzinfo=timezone.utc)
            else:
                self._attr_native_value = value
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore last state, sync with API, and register for updates."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        # Restore counter state and sync it back to the API client
        if self._attr_state_class == SensorStateClass.TOTAL_INCREASING:
            initial_value = 0
            if last_state and last_state.state.isdigit():
                initial_value = int(last_state.state)
            
            self._attr_native_value = initial_value
            
            serial_number = self._serial_number if self._sensor_id in GRILL_SPECIFIC_COUNTERS else None
            self._api_client.sync_counter(self._sensor_id, initial_value, serial_number)

        # Set initial state for all diagnostic sensors from the API client
        initial_data = self._api_client.get_diagnostics_data(self._serial_number)
        self._handle_diagnostics_update(initial_data)
        
        # Register for future updates
        self.async_on_remove(self._api_client.register_diagnostics_callback(self._serial_number, self._handle_diagnostics_update))

