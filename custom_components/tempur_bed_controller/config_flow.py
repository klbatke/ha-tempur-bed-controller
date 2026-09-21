"""Config flow for Tempur Bed Controller."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class TempurBedControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a UI-created controller configuration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, object] | None = None) -> FlowResult:
        """Show the controller host and port form."""
        if user_input is not None:
            return self.async_create_entry(
                title=str(user_input[CONF_NAME]),
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
        )
