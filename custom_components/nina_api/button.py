"""Button platform for N.I.N.A. Advanced API (fire-and-forget mount actions)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .api import NinaApiClient, NinaApiError
from .const import DEVICE_MOUNT
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        NinaButton(coordinator, DEVICE_MOUNT, "Mount", description)
        for description in MOUNT_BUTTONS
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
