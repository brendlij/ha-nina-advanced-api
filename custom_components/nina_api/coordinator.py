"""DataUpdateCoordinator for the N.I.N.A. Advanced API integration.

Fetches application/mount/camera state on a fixed poll interval as a
fallback, and can be nudged for an immediate refresh by the websocket
listener (see websocket.py) whenever NINA pushes an event.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NinaApiClient, NinaApiConnectionError, NinaApiError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class NinaData:
    """Snapshot of everything the entities need."""

    application_connected: bool = False
    application: dict[str, Any] = field(default_factory=dict)
    mount: dict[str, Any] = field(default_factory=dict)
    camera: dict[str, Any] = field(default_factory=dict)


class NinaDataUpdateCoordinator(DataUpdateCoordinator[NinaData]):
    """Coordinates polling and websocket-triggered refreshes."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: NinaApiClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> NinaData:
        data = NinaData()

        try:
            await self.client.get_application_info()
            data.application_connected = True
        except NinaApiConnectionError as err:
            # NINA itself isn't reachable at all -> whole entry is unavailable.
            raise UpdateFailed(f"NINA not reachable: {err}") from err
        except NinaApiError as err:
            # Reachable but reported an error -> keep entry alive, just log it.
            _LOGGER.debug("application/info returned an error: %s", err)

        # Equipment can be legitimately "not connected" in NINA (e.g. mount
        # powered off) without that being a coordinator-level failure, so
        # each equipment fetch is isolated.
        try:
            data.mount = await self.client.get_mount_info() or {}
        except NinaApiError as err:
            _LOGGER.debug("mount/info unavailable: %s", err)

        try:
            data.camera = await self.client.get_camera_info() or {}
        except NinaApiError as err:
            _LOGGER.debug("camera/info unavailable: %s", err)

        return data
