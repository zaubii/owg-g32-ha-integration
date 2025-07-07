"""Config flow for Otto Wilde G32 Grill integration."""
import logging
from typing import Any, Dict

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .api import OttoWildeG32ApiClient
from .const import DOMAIN, CONF_DEVICE_TRACKER

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

class OttoWildeG32ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Otto Wilde G32 Grill."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OttoWildeG32OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        errors = {}
        email = user_input[CONF_EMAIL]
        password = user_input[CONF_PASSWORD]

        session = async_get_clientsession(self.hass)
        # Pass hass to the client for the first time to get grill details for setup
        api_client = OttoWildeG32ApiClient(email, password, session, self.hass)

        try:
            login_success = await api_client.async_login()
            if not login_success:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                user_info = api_client.user_info or {}
                first_name = user_info.get("name", "")
                surname = user_info.get("surname", "")
                user_nickname = user_info.get("nickname", email)
                
                title = f"{first_name} {surname} ({user_nickname})" if first_name else user_nickname

                entry_data = user_input.copy()
                entry_data["user_info"] = user_info

                return self.async_create_entry(title=title, data=entry_data)

        except (ClientError, ConnectionError):
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception during login")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class OttoWildeG32OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Otto Wilde G32 Grill."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        # The API client should already be initialized in hass.data
        api_client: OttoWildeG32ApiClient = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            # Process and save the user input
            options_data = {}
            for grill in api_client.grills:
                serial = grill["serialNumber"]
                tracker_key = f"{CONF_DEVICE_TRACKER}_{serial}"
                if tracker_entity := user_input.get(tracker_key):
                    options_data[tracker_key] = tracker_entity
            
            return self.async_create_entry(title="", data=options_data)

        # Build the form
        schema_fields: Dict[vol.Marker, Any] = {}
        if not api_client.grills:
             _LOGGER.warning("Options flow started, but no grills found in API client.")
             return self.async_abort(reason="no_grills_found")

        for grill in api_client.grills:
            serial = grill["serialNumber"]
            nickname = grill.get("nickname", f"G32 {serial[:6]}")
            tracker_key = f"{CONF_DEVICE_TRACKER}_{serial}"
            
            schema_fields[
                vol.Optional(
                    tracker_key,
                    description={"suggested_value": self.config_entry.options.get(tracker_key)},
                )
            ] = selector({
                "entity": {
                    "domain": "device_tracker"
                }
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
            description_placeholders={"grill_count": len(api_client.grills)},
        )
