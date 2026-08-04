"""Config flow for the N.I.N.A. Advanced API integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    NinaApiClient,
    NinaApiConnectionError,
    NinaApiError,
    NinaApiNotFoundError,
)
from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class NinaApiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for N.I.N.A. Advanced API."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )

            session = async_get_clientsession(self.hass)
            client = NinaApiClient(
                user_input[CONF_HOST], user_input[CONF_PORT], session
            )

            try:
                version = await client.get_api_version()
            except NinaApiConnectionError as err:
                _LOGGER.debug("Cannot reach NINA: %s", err)
                errors["base"] = "cannot_connect"
            except NinaApiNotFoundError as err:
                # Something is listening, but it isn't the Advanced API -
                # usually the wrong port or a different web service.
                _LOGGER.debug("Wrong endpoint for NINA: %s", err)
                errors["base"] = "not_nina_api"
            except NinaApiError as err:
                # Reachable and the right service, but it reported an error.
                _LOGGER.debug("NINA reported an error: %s", err)
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating NINA connection")
                errors["base"] = "unknown"
            else:
                _LOGGER.debug("Connected to NINA Advanced API version %s", version)
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
