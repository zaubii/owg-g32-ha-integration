"""Config flow for Otto Wilde G32 Grill integration."""
import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OttoWildeG32ApiClient
from .const import DOMAIN

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
        api_client = OttoWildeG32ApiClient(email, password, session)

        try:
            # Login to the API
            login_success = await api_client.async_login()
            if not login_success:
                errors["base"] = "invalid_auth"
            else:
                # Use email as unique ID for the config entry
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                # Get user info for a more descriptive title
                user_info = api_client.user_info or {}
                first_name = user_info.get("name", "")
                surname = user_info.get("surname", "")
                user_nickname = user_info.get("nickname", email)
                
                title = f"{first_name} {surname} ({user_nickname})" if first_name else user_nickname

                # Store user info along with credentials
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

