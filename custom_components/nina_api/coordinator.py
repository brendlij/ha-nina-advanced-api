"""DataUpdateCoordinator for the N.I.N.A. Advanced API integration.

Fetches application/mount/camera/sequence state on a fixed poll interval.
Every sub-fetch is isolated: equipment can be legitimately absent or
disconnected in NINA without that making the whole entry unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    NinaApiClient,
    NinaApiConnectionError,
    NinaApiError,
    NinaApiResponseError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .sequence import summarize_sequence

_LOGGER = logging.getLogger(__name__)

# NINA answers 409 when a sub-system exists but has nothing loaded or
# connected yet. That is a normal idle state, not an error worth logging.
_STATUS_NOT_READY = 409


@dataclass
class NinaData:
    """Snapshot of everything the entities need."""

    application_connected: bool = False
    api_version: str | None = None
    nina_version: str | None = None
    application: dict[str, Any] = field(default_factory=dict)
    mount: dict[str, Any] = field(default_factory=dict)
    camera: dict[str, Any] = field(default_factory=dict)

    # Sequence
    sequence_loaded: bool = False
    sequence_running: bool = False
    sequence_current_item: str | None = None
    sequence_items_total: int = 0
    sequence_items_finished: int = 0
    sequence_state: list[Any] = field(default_factory=list)

    @property
    def sequence_progress(self) -> float | None:
        """Percentage of finished leaf items, or None if nothing is loaded."""
        if not self.sequence_items_total:
            return None
        return round(
            100 * self.sequence_items_finished / self.sequence_items_total, 1
        )


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
            update_interval=timedelta(
                seconds=config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )
        self.client = client
        # The NINA version cannot change while the app is running, so it is
        # fetched once and carried across refreshes.
        self._nina_version: str | None = None

    async def _async_update_data(self) -> NinaData:
        data = NinaData()

        # A closed N.I.N.A. is the normal daytime state of an imaging rig,
        # not an error. Reporting it as a failed update would tear the whole
        # config entry down, and Home Assistant would then drop every entity
        # ("no longer being provided by the integration") until NINA comes
        # back. Instead the refresh succeeds with application_connected
        # False, so the entities stay registered and simply read as
        # unavailable - and the connectivity sensor stays usable as a
        # trigger for "NINA just started".
        try:
            data.api_version = await self.client.get_api_version()
        except NinaApiConnectionError as err:
            _LOGGER.debug("NINA not reachable (is it running?): %s", err)
            # NINA may well be updated before it comes back, so re-read the
            # version on the next successful connection.
            self._nina_version = None
            return data
        except NinaApiError as err:
            # Reachable, but not answering like the Advanced API should.
            _LOGGER.debug("version endpoint returned an error: %s", err)
            return data

        data.application_connected = True

        if self._nina_version is None:
            try:
                self._nina_version = await self.client.get_nina_version()
            except NinaApiError as err:
                _LOGGER.debug("NINA version unavailable: %s", err)
        data.nina_version = self._nina_version

        data.mount = await self._fetch("mount", self.client.get_mount_info)
        data.camera = await self._fetch("camera", self.client.get_camera_info)

        await self._update_sequence(data)

        return data

    async def _fetch(self, name: str, method: Any) -> dict[str, Any]:
        """Run one equipment fetch, downgrading its failure to a debug log."""
        try:
            result = await method()
        except NinaApiError as err:
            _LOGGER.debug("%s info unavailable: %s", name, err)
            return {}
        return result if isinstance(result, dict) else {}

    async def _update_sequence(self, data: NinaData) -> None:
        """Populate the sequence fields, treating 'not loaded' as idle."""
        try:
            state = await self.client.get_sequence_state()
        except NinaApiResponseError as err:
            if err.status_code != _STATUS_NOT_READY:
                _LOGGER.debug("sequence state unavailable: %s", err)
            return
        except NinaApiError as err:
            _LOGGER.debug("sequence state unavailable: %s", err)
            return

        if not isinstance(state, list):
            return

        data.sequence_loaded = True
        data.sequence_state = state

        # The first element is the GlobalTriggers wrapper, the rest are the
        # actual root containers.
        containers = [
            item
            for item in state
            if isinstance(item, dict) and "GlobalTriggers" not in item
        ]
        summary = summarize_sequence(containers)

        data.sequence_current_item = summary.current_item
        data.sequence_running = summary.running
        data.sequence_items_total = summary.total
        data.sequence_items_finished = summary.finished
