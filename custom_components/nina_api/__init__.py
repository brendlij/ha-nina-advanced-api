"""The N.I.N.A. Advanced API integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NinaApiClient
from .coordinator import NinaDataUpdateCoordinator
from .websocket import NinaWebsocketListener

_LOGGER = logging.getLogger(__name__)

# Entities that only report what N.I.N.A. is doing. Always set up.
READ_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

# Entities that command N.I.N.A. Skipped entirely in read-only mode, so a
# read-only entry has no way to move the mount, touch the cooler or drive
# the sequence - not even from Developer tools.
CONTROL_PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SWITCH,
]

type NinaConfigEntry = ConfigEntry[NinaDataUpdateCoordinator]


def _platforms_for(read_only: bool) -> list[Platform]:
    """Return the platforms an entry in this mode owns."""
    if read_only:
        return list(READ_PLATFORMS)
    return [*READ_PLATFORMS, *CONTROL_PLATFORMS]


async def async_setup_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Set up N.I.N.A. Advanced API from a config entry."""
    session = async_get_clientsession(hass)
    client = NinaApiClient(entry.data[CONF_HOST], entry.data[CONF_PORT], session)

    coordinator = NinaDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Push channel. It reconnects on its own and never blocks setup, so an
    # unreachable N.I.N.A. just leaves the integration on its poll interval.
    listener = NinaWebsocketListener(
        hass, client, coordinator, entry.entry_id, session
    )
    listener.start(entry)
    entry.async_on_unload(listener.async_stop)

    # Picks up a changed host/port from the reconfigure flow, and a changed
    # poll interval or read-only mode from the options flow - all of them
    # only take effect on reload.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    if coordinator.read_only:
        _async_remove_control_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, _platforms_for(coordinator.read_only)
    )
    return True


@callback
def _async_remove_control_entities(
    hass: HomeAssistant, entry: NinaConfigEntry
) -> None:
    """Drop the control entities this entry left behind in the registry.

    Skipping the platforms is enough to make the entities stop working, but
    the registry would keep the old rows around as unavailable and Home
    Assistant would nag about them "no longer being provided". Read-only is
    an explicit choice, so clear them out; flipping back re-creates them.
    """
    registry = er.async_get(hass)
    control_domains = {platform.value for platform in CONTROL_PLATFORMS}

    # Materialized up front: async_remove mutates the registry's index.
    for registry_entry in list(
        er.async_entries_for_config_entry(registry, entry.entry_id)
    ):
        if registry_entry.domain in control_domains:
            _LOGGER.debug(
                "Read-only mode: removing control entity %s",
                registry_entry.entity_id,
            )
            registry.async_remove(registry_entry.entity_id)


async def _async_update_listener(hass: HomeAssistant, entry: NinaConfigEntry) -> None:
    """Reload the entry after its data or options changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    # The coordinator carries the mode this entry was *set up* with. Reading
    # the options again here would be wrong: on an options change Home
    # Assistant saves them before reloading, so the new mode would be used to
    # tear down platforms the old one never loaded.
    return await hass.config_entries.async_unload_platforms(
        entry, _platforms_for(entry.runtime_data.read_only)
    )
