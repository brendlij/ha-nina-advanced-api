"""Switch platform for N.I.N.A. Advanced API."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .api import NinaApiClient, NinaApiError
from .const import DEVICE_CAMERA, DEVICE_MOUNT, DEVICE_NAMES, TRACKING_MODE_TO_INT
from .coordinator import NinaData, NinaDataUpdateCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)

# Fallback when the camera reports no set point at all - matches NINA's
# own default cooling target.
DEFAULT_TARGET_TEMP = 0.0


async def _cooler_on(client: NinaApiClient, data: NinaData) -> None:
    """Start cooling towards whatever set point the camera already holds."""
    target = data.camera.get("TemperatureSetPoint")
    if target is None:
        target = data.camera.get("TargetTemp")
    if target is None:
        target = DEFAULT_TARGET_TEMP
        _LOGGER.debug(
            "Camera reports no temperature set point, cooling to %s C", target
        )
    await client.camera_cool(temperature=float(target), minutes=0)


@dataclass(frozen=True, kw_only=True)
class NinaSwitchEntityDescription(SwitchEntityDescription):
    """Describes a NINA switch."""

    value_fn: Callable[[NinaData], bool | None]
    turn_on_fn: Callable[[NinaApiClient, NinaData], Awaitable[Any]]
    turn_off_fn: Callable[[NinaApiClient, NinaData], Awaitable[Any]]
    # Some switches only make sense on hardware that supports them.
    supported_fn: Callable[[NinaData], bool] = lambda _: True


CAMERA_SWITCHES: tuple[NinaSwitchEntityDescription, ...] = (
    NinaSwitchEntityDescription(
        key="camera_cooler",
        translation_key="camera_cooler",
        icon="mdi:snowflake",
        value_fn=lambda d: d.camera.get("CoolerOn"),
        turn_on_fn=lambda client, data: _cooler_on(client, data),
        turn_off_fn=lambda client, _: client.camera_warm(minutes=0),
        supported_fn=lambda d: bool(d.camera.get("CanSetTemperature")),
    ),
    NinaSwitchEntityDescription(
        key="camera_dew_heater",
        translation_key="camera_dew_heater",
        icon="mdi:heat-wave",
        value_fn=lambda d: d.camera.get("DewHeaterOn"),
        turn_on_fn=lambda client, _: client.camera_set_dew_heater(True),
        turn_off_fn=lambda client, _: client.camera_set_dew_heater(False),
        supported_fn=lambda d: bool(d.camera.get("HasDewHeater")),
    ),
)

MOUNT_SWITCHES: tuple[NinaSwitchEntityDescription, ...] = (
    NinaSwitchEntityDescription(
        key="mount_tracking",
        translation_key="mount_tracking",
        icon="mdi:target",
        device_class=SwitchDeviceClass.SWITCH,
        value_fn=lambda d: d.mount.get("TrackingEnabled"),
        turn_on_fn=lambda client, _: client.mount_set_tracking(
            TRACKING_MODE_TO_INT["sidereal"]
        ),
        turn_off_fn=lambda client, _: client.mount_set_tracking(
            TRACKING_MODE_TO_INT["stopped"]
        ),
        supported_fn=lambda d: bool(d.mount.get("CanSetTrackingEnabled")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    groups = (
        (DEVICE_CAMERA, DEVICE_NAMES[DEVICE_CAMERA], CAMERA_SWITCHES),
        (DEVICE_MOUNT, DEVICE_NAMES[DEVICE_MOUNT], MOUNT_SWITCHES),
    )
    async_add_entities(
        NinaSwitch(coordinator, device_key, device_name, description)
        for device_key, device_name, descriptions in groups
        for description in descriptions
    )


class NinaSwitch(NinaEntity, SwitchEntity):
    """A NINA toggle backed by two API calls."""

    entity_description: NinaSwitchEntityDescription

    def __init__(
        self,
        coordinator: NinaDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        description: NinaSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_key, device_name, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Hide the switch when the hardware cannot do it.

        The capability flags only arrive once the device is connected, so
        an unsupported switch reads as unavailable rather than silently
        failing on every press.
        """
        return super().available and self.entity_description.supported_fn(
            self.coordinator.data
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._call(self.entity_description.turn_on_fn)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._call(self.entity_description.turn_off_fn)

    async def _call(
        self, func: Callable[[NinaApiClient, NinaData], Awaitable[Any]]
    ) -> None:
        try:
            await func(self.coordinator.client, self.coordinator.data)
        except NinaApiError as err:
            raise HomeAssistantError(
                f"NINA switch '{self.entity_description.key}' failed: {err}"
            ) from err
        finally:
            await self.coordinator.async_request_refresh()
