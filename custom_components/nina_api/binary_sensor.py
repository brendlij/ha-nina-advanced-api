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
from .const import DEVICE_APPLICATION, DEVICE_CAMERA, DEVICE_MOUNT, DEVICE_SEQUENCE
from .coordinator import NinaData, NinaDataUpdateCoordinator
from .entity import NinaEntity


@dataclass(frozen=True, kw_only=True)
class NinaBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_fn: Callable[[NinaData], bool | None]
    # A sensor whose whole job is reporting the connection cannot go
    # unavailable when the connection drops - it has to stay readable to
    # report "off".
    available_when_disconnected: bool = False


APPLICATION_SENSORS: tuple[NinaBinarySensorEntityDescription, ...] = (
    NinaBinarySensorEntityDescription(
        key="application_connected",
        translation_key="application_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.application_connected,
        available_when_disconnected=True,
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
        key="mount_at_home",
        translation_key="mount_at_home",
        icon="mdi:home-import-outline",
        value_fn=lambda d: d.mount.get("AtHome"),
    ),
    NinaBinarySensorEntityDescription(
        key="mount_slewing",
        translation_key="mount_slewing",
        icon="mdi:rotate-3d-variant",
        value_fn=lambda d: d.mount.get("Slewing"),
    ),
    NinaBinarySensorEntityDescription(
        key="mount_pulse_guiding",
        translation_key="mount_pulse_guiding",
        icon="mdi:crosshairs-gps",
        value_fn=lambda d: d.mount.get("IsPulseGuiding"),
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
    NinaBinarySensorEntityDescription(
        key="camera_at_target_temp",
        translation_key="camera_at_target_temp",
        icon="mdi:thermometer-check",
        value_fn=lambda d: d.camera.get("AtTargetTemp"),
    ),
    NinaBinarySensorEntityDescription(
        key="camera_exposing",
        translation_key="camera_exposing",
        icon="mdi:camera-timer",
        value_fn=lambda d: d.camera.get("IsExposing"),
    ),
    NinaBinarySensorEntityDescription(
        key="camera_dew_heater",
        translation_key="camera_dew_heater",
        icon="mdi:heat-wave",
        value_fn=lambda d: d.camera.get("DewHeaterOn"),
    ),
)

SEQUENCE_SENSORS: tuple[NinaBinarySensorEntityDescription, ...] = (
    NinaBinarySensorEntityDescription(
        key="sequence_running",
        translation_key="sequence_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.sequence_running,
    ),
    NinaBinarySensorEntityDescription(
        key="sequence_loaded",
        translation_key="sequence_loaded",
        icon="mdi:playlist-check",
        value_fn=lambda d: d.sequence_loaded,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    groups = (
        (DEVICE_APPLICATION, "N.I.N.A.", APPLICATION_SENSORS),
        (DEVICE_MOUNT, "Mount", MOUNT_SENSORS),
        (DEVICE_CAMERA, "Camera", CAMERA_SENSORS),
        (DEVICE_SEQUENCE, "Sequence", SEQUENCE_SENSORS),
    )
    async_add_entities(
        NinaBinarySensor(coordinator, device_key, device_name, description)
        for device_key, device_name, descriptions in groups
        for description in descriptions
    )


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
    def available(self) -> bool:
        if self.entity_description.available_when_disconnected:
            return self.coordinator.last_update_success
        return super().available

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
