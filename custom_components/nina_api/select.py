"""Select platform for N.I.N.A. Advanced API (mount tracking mode)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .api import NinaApiError
from .const import (
    DEVICE_MOUNT,
    TRACKING_MODE_OPTIONS,
    TRACKING_MODE_TO_INT,
    TRACKING_MODES,
)
from .coordinator import NinaDataUpdateCoordinator
from .entity import NinaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([NinaTrackingModeSelect(entry.runtime_data)])


class NinaTrackingModeSelect(NinaEntity, SelectEntity):
    """Reads and sets the mount's tracking mode."""

    _attr_translation_key = "mount_tracking_mode"
    _attr_icon = "mdi:target"
    _attr_options = TRACKING_MODE_OPTIONS

    def __init__(self, coordinator: NinaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, DEVICE_MOUNT, "Mount", "tracking_mode")

    @property
    def current_option(self) -> str | None:
        mode = TRACKING_MODES.get(self.coordinator.data.mount.get("TrackingMode"))
        # "custom" is a real NINA mode but is not offered as an option, so
        # report it as unknown rather than handing HA an invalid state.
        return mode if mode in TRACKING_MODE_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        try:
            await self.coordinator.client.mount_set_tracking(
                TRACKING_MODE_TO_INT[option]
            )
        except NinaApiError as err:
            raise HomeAssistantError(
                f"Setting tracking mode to '{option}' failed: {err}"
            ) from err
        finally:
            await self.coordinator.async_request_refresh()
