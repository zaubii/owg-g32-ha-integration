"""Text platform for the Otto Wilde G32 Grill."""
from __future__ import annotations
import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text entities for the integration."""
    api_client: OttoWildeG32ApiClient = hass.data[DOMAIN][entry.entry_id]
    
    # Create a single, global debug text entity for the integration
    async_add_entities([G32DebugText(api_client, entry)])

class G32DebugText(TextEntity):
    """A text entity to display the debug log."""

    _attr_should_poll = False

    def __init__(self, api_client: OttoWildeG32ApiClient, entry: ConfigEntry):
        """Initialize the debug text entity."""
        self._api_client = api_client
        self._attr_unique_id = f"{entry.entry_id}_debug_log"
        self._attr_name = "Otto Wilde G32 Debug Text"
        self._attr_native_value = self._api_client.get_debug_log()

    @property
    def native_value(self) -> str | None:
        """Return the value of the text entity."""
        return self._api_client.get_debug_log()

    @callback
    def _handle_debug_update(self) -> None:
        """Handle updates to the debug log."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added."""
        self.async_on_remove(
            self._api_client.register_debug_callback(self._handle_debug_update)
        )

