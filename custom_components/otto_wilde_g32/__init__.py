"""The Otto Wilde G32 Grill integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

from .api import OttoWildeG32ApiClient
from .const import DOMAIN, PLATFORMS # PLATFORMS is now imported

_LOGGER = logging.getLogger(__name__)
# PLATFORMS constant is now defined in const.py

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Otto Wilde G32 Grill from a config entry."""
    _LOGGER.info("Setting up Otto Wilde G32 integration for account: %s", entry.title)

    session = async_get_clientsession(hass)
    api_client = OttoWildeG32ApiClient(
        entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD], session
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api_client

    if not await api_client.async_get_grill_details():
        _LOGGER.error("Failed to get any grill details, integration will not be set up.")
        return False

    device_registry = dr.async_get(hass)
    for grill in api_client.grills:
        serial_number = grill["serialNumber"]
        devicenickname = grill.get("nickname", f"G32 {serial_number[:6]}")
        
        gasbuddy_info = grill.get("gasbuddyInfo", {})
        
        # Use ASCII-compatible strings to avoid encoding issues.
        gas_capacity_str = f"Kapazitaet: {gasbuddy_info.get('gasCapacity')}kg"
        gas_tara_str = f"Tara: {gasbuddy_info.get('tareWeight')}kg"
        
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, serial_number)},
            name=devicenickname,
            model=serial_number,
            manufacturer="Otto Wilde",
            sw_version=grill.get("firmwareSemanticVersion"),
            hw_version=f"{gas_capacity_str}, {gas_tara_str}"
        )

    # This line now correctly forwards to all platforms listed in const.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    await api_client.async_start_listeners()

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Otto Wilde G32 integration")
    
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    await api_client.async_stop_listeners()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

