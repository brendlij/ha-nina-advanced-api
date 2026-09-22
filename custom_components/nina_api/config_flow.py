"""Config flow for the N.I.N.A. Advanced API integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import (
    NinaApiClient,
    NinaApiConnectionError,
    NinaApiError,
    NinaApiNotFoundError,
)
from .const import (
    CONF_READ_ONLY,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_READ_ONLY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Host and port on their own: reconfigure only moves the connection and must
# not offer - or silently reset - the mode, which lives in the options.
CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)

STEP_USER_DATA_SCHEMA = CONNECTION_SCHEMA.extend(
    {
        vol.Required(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
    }
)


async def _async_validate(hass: HomeAssistant, host: str, port: int) -> str | None:
    """Probe a NINA instance. Returns an error key, or None on success."""
    client = NinaApiClient(host, port, async_get_clientsession(hass))
    try:
        version = await client.get_api_version()
    except NinaApiConnectionError as err:
        _LOGGER.debug("Cannot reach NINA: %s", err)
        return "cannot_connect"
    except NinaApiNotFoundError as err:
        # Something is listening, but it isn't the Advanced API - usually
        # the wrong port or a different web service.
        _LOGGER.debug("Wrong endpoint for NINA: %s", err)
        return "not_nina_api"
    except NinaApiError as err:
        # Reachable and the right service, but it reported an error.
        _LOGGER.debug("NINA reported an error: %s", err)
        return "invalid_response"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error validating NINA connection")
        return "unknown"

    _LOGGER.debug("Connected to NINA Advanced API version %s", version)
    return None


class NinaApiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for N.I.N.A. Advanced API."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NinaApiOptionsFlow:
        return NinaApiOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )

            error = await _async_validate(
                self.hass, user_input[CONF_HOST], user_input[CONF_PORT]
            )
            if error is None:
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    },
                    # The mode belongs to the options, next to the polling
                    # interval, so it stays editable under "Configure".
                    options={CONF_READ_ONLY: user_input[CONF_READ_ONLY]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user point an existing entry at a different host/port.

        Reached via the integration's "Reconfigure" menu entry. The entry is
        updated and reloaded in place, so entity IDs, history and dashboard
        cards all survive the move.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            if self._is_taken_by_another_entry(entry, host, port):
                errors["base"] = "already_configured"
            else:
                error = await _async_validate(self.hass, host, port)
                if error is None:
                    return self.async_update_reload_and_abort(
                        entry, data_updates={CONF_HOST: host, CONF_PORT: port}
                    )
                errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                CONNECTION_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )

    def _is_taken_by_another_entry(
        self, entry: ConfigEntry, host: str, port: int
    ) -> bool:
        """Guard against pointing two entries at the same NINA instance.

        The current entry is skipped - reconfiguring without changing
        anything, or only changing the port, must not collide with itself.
        """
        return any(
            other.entry_id != entry.entry_id
            and other.data.get(CONF_HOST) == host
            and other.data.get(CONF_PORT) == port
            for other in self._async_current_entries()
        )


class NinaApiOptionsFlow(OptionsFlow):
    """Settings that do not affect how we reach NINA."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
