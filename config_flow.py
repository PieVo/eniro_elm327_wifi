import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class KiaEniroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration for the Kia e-Niro ELM327 WiFi integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Kia e-Niro ELM327 WiFi", data=user_input)

        data_schema = vol.Schema({
            vol.Required("elm_ip"): str,
            vol.Required("elm_port", default=35000): int,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)


class KiaEniroOptionsFlowHandler(config_entries.OptionsFlow):
    """Options for Kia e-Niro ELM327 WiFi."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                "scan_interval_minutes",
                default=self.config_entry.options.get("scan_interval_minutes", 10)
            ): int,
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)


@callback
def configured_instances(hass):
    """Retourne les instances déjà configurées."""
    return set(entry.data["elm_ip"] for entry in hass.config_entries.async_entries(DOMAIN))
