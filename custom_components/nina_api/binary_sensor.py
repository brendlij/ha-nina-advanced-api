"""Binary sensor platform for N.I.N.A. Advanced API."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .const import DEVICE_APPLICATION, DEVICE_CAMERA, DEVICE_MOUNT
from .coordinator import NinaData, NinaDataUpdateCoordinator
from .entity import NinaEntity


@dataclass(frozen=True, kw_only=True)
class NinaBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_fn: Callable[[NinaData], bool | None]


APPLICATION_SENSORS: tuple[NinaBinarySensorEntityDescription, ...] = (
    NinaBinarySensorEntityDescription(
        key="application_connected",
        translation_key="application_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.application_connected,
    ),
)

MOUNT_SENSORS: tuple[NinaBinarySensorEntityDescription, ...] = (
    NinaBinarySensorEntityDescription(
        key="mount_connected",
        translation_key="mount_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.mount.get("Connected"),
    ),
    NinaBinarySensorEntityDescription(
        key="mount_tracking",
        translation_key="mount_tracking",
        icon="mdi:target",
        value_fn=lambda d: d.mount.get("TrackingEnabled"),
    ),
    NinaBinarySensorEntityDescription(
        key="mount_parked",
        translation_key="mount_parked",
        icon="mdi:parking",
        value_fn=lambda d: d.mount.get("AtPark"),
    ),
    NinaBinarySensorEntityDescription(
        key="mount_slewing",
        translation_key="mount_slewing",
        icon="mdi:rotate-3d-variant",
        value_fn=lambda d: d.mount.get("Slewing"),
    ),
)

CAMERA_SENSORS: tuple[NinaBinarySensorEntityDescription, ...] = (
    NinaBinarySensorEntityDescription(
        key="camera_connected",
        translation_key="camera_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.camera.get("Connected"),
    ),
    NinaBinarySensorEntityDescription(
        key="camera_cooling",
        translation_key="camera_cooling",
        icon="mdi:snowflake",
        value_fn=lambda d: d.camera.get("CoolerOn"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[NinaBinarySensor] = (
        [
            NinaBinarySensor(coordinator, DEVICE_APPLICATION, "N.I.N.A.", description)
            for description in APPLICATION_SENSORS
        ]
        + [
            NinaBinarySensor(coordinator, DEVICE_MOUNT, "Mount", description)
            for description in MOUNT_SENSORS
        ]
        + [
            NinaBinarySensor(coordinator, DEVICE_CAMERA, "Kamera", description)
            for description in CAMERA_SENSORS
        ]
    )
    async_add_entities(entities)


class NinaBinarySensor(NinaEntity, BinarySensorEntity):
    """A single NINA boolean state."""

    entity_description: NinaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: NinaDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        description: NinaBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_key, device_name, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
