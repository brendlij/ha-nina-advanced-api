"""The most recently saved frame, as a Home Assistant image entity.

N.I.N.A. already has the picture on screen; this is about getting the same
one onto a dashboard or into a notification without anyone opening a remote
desktop session to look.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import NinaConfigEntry
from .api import NinaApiError
from .const import DEVICE_LAST_IMAGE, IMAGE_SCALE
from .coordinator import NinaDataUpdateCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)


def _capture_time(value: Any) -> datetime | None:
    """Turn NINA's capture timestamp into an aware datetime.

    The API serializes a C# DateTime with no UTC offset, so a naive value is
    read as local time — the usual single-PC or same-site setup.
    """
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([NinaLastImage(hass, entry.runtime_data)])


class NinaLastImage(NinaEntity, ImageEntity):
    """The last frame the running sequence saved."""

    # The device is this frame, so the entity carries the device's name
    # rather than repeating it.
    _attr_name = None

    def __init__(
        self, hass: HomeAssistant, coordinator: NinaDataUpdateCoordinator
    ) -> None:
        NinaEntity.__init__(self, coordinator, DEVICE_LAST_IMAGE, "Last image", "image")
        ImageEntity.__init__(self, hass)
        self._cached: bytes | None = None
        self._cached_index: int | None = None
        self._apply_timestamp()

    @property
    def available(self) -> bool:
        """Available once the session has actually saved something.

        Before the first frame there is no index to fetch and NINA answers
        the image endpoint with an error, so claiming availability would
        only produce a broken picture on the dashboard.
        """
        return super().available and self.coordinator.data.last_image_index >= 0

    @callback
    def _handle_coordinator_update(self) -> None:
        self._apply_timestamp()
        super()._handle_coordinator_update()

    def _apply_timestamp(self) -> None:
        """Point Home Assistant at the capture time of the newest frame.

        image_last_updated is what makes the frontend re-fetch, so it has to
        track the frame rather than the poll: using now() would re-download
        a megabyte every coordinator tick for a picture that had not changed.
        """
        captured = _capture_time(self.coordinator.data.last_image.get("Date"))
        if captured is not None and captured != self._attr_image_last_updated:
            self._attr_image_last_updated = captured

    async def async_image(self) -> bytes | None:
        index = self.coordinator.data.last_image_index
        if index < 0:
            return None
        if self._cached is not None and self._cached_index == index:
            return self._cached

        try:
            content, content_type = await self.coordinator.client.get_image_bytes(
                index, scale=IMAGE_SCALE
            )
        except NinaApiError as err:
            # A frame that cannot be fetched is not a reason to drop the
            # entity: the next capture gets its own chance.
            _LOGGER.debug("last image unavailable: %s", err)
            return None

        self._attr_content_type = content_type
        self._cached = content
        self._cached_index = index
        return content
