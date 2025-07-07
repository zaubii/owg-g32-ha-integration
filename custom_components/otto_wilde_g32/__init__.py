"""The Otto Wilde G32 Grill integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_state_change_event

from .api import OttoWildeG32ApiClient
from .const import DOMAIN, PLATFORMS, CONF_DEVICE_TRACKER

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Otto Wilde G32 Grill from a config entry."""
    _LOGGER.info("Setting up Otto Wilde G32 integration for account: %s", entry.title)

    session = async_get_clientsession(hass)
    # Pass hass to the client so it can access states
    api_client = OttoWildeG32ApiClient(
        entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD], session, hass
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
        
        gas_capacity_str = f"Capacity: {gasbuddy_info.get('gasCapacity')}kg"
        gas_tara_str = f"Tare: {gasbuddy_info.get('tareWeight')}kg"
        
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, serial_number)},
            name=devicenickname,
            model=serial_number,
            manufacturer="Otto Wilde",
            sw_version=grill.get("firmwareSemanticVersion"),
            hw_version=f"{gas_capacity_str}, {gas_tara_str}"
        )

    # Set up the options listener and initial tracker registration
    await async_update_options(hass, entry)
    entry.add_update_listener(async_update_options)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start listeners after platforms are set up
    await api_client.async_start_listeners()

    # Ensure listeners are stopped on HA shutdown
    async def _stop_listeners(event):
        await api_client.async_stop_listeners()
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_listeners)
    )

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options from the config entry."""
    _LOGGER.debug("Updating Otto Wilde G32 options.")
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    
    # Clear any existing listeners to avoid duplicates
    api_client.clear_state_listeners()

    for grill in api_client.grills:
        serial_number = grill["serialNumber"]
        tracker_key = f"{CONF_DEVICE_TRACKER}_{serial_number}"
        entity_id = entry.options.get(tracker_key)

        api_client.register_device_tracker(serial_number, entity_id)

        if entity_id:
            _LOGGER.info("Grill %s is being tracked by %s", serial_number, entity_id)
            
            # Define the callback for the state tracker
            @callback
            def _state_change_handler(event, sn=serial_number):
                """Handle device_tracker state changes."""
                new_state = event.data.get("new_state")
                if not new_state:
                    return

                _LOGGER.debug("State change for %s: %s", event.data.get("entity_id"), new_state.state)
                if new_state.state == "home":
                    _LOGGER.info("Tracked device for grill %s is home. Triggering connection check.", sn)
                    hass.async_create_task(api_client.connect_if_needed(sn))

            # Register the state change listener
            unsubscribe = async_track_state_change_event(
                hass, [entity_id], _state_change_handler
            )
            api_client.add_state_listener_unsubscribe(unsubscribe)

            # Check initial state on setup
            initial_state = hass.states.get(entity_id)
            if initial_state and initial_state.state == "home":
                _LOGGER.info("Initial state for %s is 'home'. Triggering connection check.", entity_id)
                hass.async_create_task(api_client.connect_if_needed(serial_number))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Otto Wilde G32 integration")
    
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    await api_client.async_stop_listeners()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
