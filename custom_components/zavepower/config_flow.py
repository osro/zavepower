"""Config flow for the Zavepower integration."""

import logging

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, LOGIN_ENDPOINT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class ZavepowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zavepower."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        LOGIN_ENDPOINT,
                        json={
                            "method": "POST",
                            "credentials": "include",
                            "headers": {
                                "Content-Type": "application/json;charset=utf-8"
                            },
                            "username": username,
                            "password": password,
                        },
                        timeout=15,
                    )
                    response.raise_for_status()
                    data = response.json()
            except httpx.RequestError as err:
                _LOGGER.error("Request error: %s", err)
                errors["base"] = "cannot_connect"
            except httpx.HTTPStatusError as err:
                _LOGGER.error("HTTP status error: %s", err)
                errors["base"] = "invalid_auth"
            else:
                if "jwtToken" not in data or "refreshToken" not in data:
                    # We didn't get back what we expected.
                    errors["base"] = "invalid_auth"
                else:
                    # We have a valid token
                    await self.async_set_unique_id(data["id"])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Zavepower ({data['firstName']} {data['lastName']})",
                        data={
                            "user_id": data["id"],
                            "username": data["username"],
                            "jwt_token": data["jwtToken"],
                            "refresh_token": data["refreshToken"],
                            "expiration": data["expiration"],
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ZavepowerOptionsFlowHandler(config_entry)


class ZavepowerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Zavepower options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Example: no custom options yet, just an example text to show
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
