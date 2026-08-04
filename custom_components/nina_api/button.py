"""Button platform for N.I.N.A. Advanced API (fire-and-forget actions)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .api import NinaApiClient, NinaApiError
from .const import (
    DEVICE_CAMERA,
    DEVICE_MOUNT,
    DEVICE_SEQUENCE,
    SKIP_CURRENT_ITEMS,
    SKIP_TO_END,
    SKIP_TO_IMAGING,
)
from .coordinator import NinaDataUpdateCoordinator
from .entity import NinaEntity


@dataclass(frozen=True, kw_only=True)
class NinaButtonEntityDescription(ButtonEntityDescription):
    press_fn: Callable[[NinaApiClient], Awaitable[None]]


MOUNT_BUTTONS: tuple[NinaButtonEntityDescription, ...] = (
    NinaButtonEntityDescription(
        key="mount_park",
        translation_key="mount_park",
        icon="mdi:parking",
        press_fn=lambda client: client.mount_park(),
    ),
    NinaButtonEntityDescription(
        key="mount_unpark",
        translation_key="mount_unpark",
        icon="mdi:parking",
        press_fn=lambda client: client.mount_unpark(),
    ),
    NinaButtonEntityDescription(
        key="mount_home",
        translation_key="mount_home",
        icon="mdi:home-import-outline",
        press_fn=lambda client: client.mount_home(),
    ),
    NinaButtonEntityDescription(
        key="mount_flip",
        translation_key="mount_flip",
        icon="mdi:flip-horizontal",
        press_fn=lambda client: client.mount_flip(),
    ),
    NinaButtonEntityDescription(
        key="mount_stop_slew",
        translation_key="mount_stop_slew",
        icon="mdi:stop-circle-outline",
        press_fn=lambda client: client.mount_stop_slew(),
    ),
    NinaButtonEntityDescription(
        key="mount_set_park_position",
        translation_key="mount_set_park_position",
        icon="mdi:map-marker-plus",
        press_fn=lambda client: client.mount_set_park_position(),
    ),
)

CAMERA_BUTTONS: tuple[NinaButtonEntityDescription, ...] = (
    NinaButtonEntityDescription(
        key="camera_abort_exposure",
        translation_key="camera_abort_exposure",
        icon="mdi:camera-off",
        press_fn=lambda client: client.camera_abort_exposure(),
    ),
    NinaButtonEntityDescription(
        key="camera_cancel_cooling",
        translation_key="camera_cancel_cooling",
        icon="mdi:snowflake-off",
        press_fn=lambda client: client.camera_cancel_cooling(),
    ),
)

SEQUENCE_BUTTONS: tuple[NinaButtonEntityDescription, ...] = (
    NinaButtonEntityDescription(
        key="sequence_start",
        translation_key="sequence_start",
        icon="mdi:play",
        press_fn=lambda client: client.sequence_start(),
    ),
    NinaButtonEntityDescription(
        key="sequence_stop",
        translation_key="sequence_stop",
        icon="mdi:stop",
        press_fn=lambda client: client.sequence_stop(),
    ),
    NinaButtonEntityDescription(
        key="sequence_reset",
        translation_key="sequence_reset",
        icon="mdi:restart",
        press_fn=lambda client: client.sequence_reset(),
    ),
    NinaButtonEntityDescription(
        key="sequence_skip_current",
        translation_key="sequence_skip_current",
        icon="mdi:skip-next",
        press_fn=lambda client: client.sequence_skip(SKIP_CURRENT_ITEMS),
    ),
    NinaButtonEntityDescription(
        key="sequence_skip_to_imaging",
        translation_key="sequence_skip_to_imaging",
        icon="mdi:skip-forward",
        press_fn=lambda client: client.sequence_skip(SKIP_TO_IMAGING),
    ),
    NinaButtonEntityDescription(
        key="sequence_skip_to_end",
        translation_key="sequence_skip_to_end",
        icon="mdi:skip-forward-outline",
        press_fn=lambda client: client.sequence_skip(SKIP_TO_END),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    groups = (
        (DEVICE_MOUNT, "Mount", MOUNT_BUTTONS),
        (DEVICE_CAMERA, "Camera", CAMERA_BUTTONS),
        (DEVICE_SEQUENCE, "Sequence", SEQUENCE_BUTTONS),
    )
    async_add_entities(
        NinaButton(coordinator, device_key, device_name, description)
        for device_key, device_name, descriptions in groups
        for description in descriptions
    )


class NinaButton(NinaEntity, ButtonEntity):
    """A single fire-and-forget NINA action."""

    entity_description: NinaButtonEntityDescription

    def __init__(
        self,
        coordinator: NinaDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        description: NinaButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_key, device_name, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        try:
            await self.entity_description.press_fn(self.coordinator.client)
        except NinaApiError as err:
            raise HomeAssistantError(
                f"NINA action '{self.entity_description.key}' failed: {err}"
            ) from err
        finally:
            await self.coordinator.async_request_refresh()
