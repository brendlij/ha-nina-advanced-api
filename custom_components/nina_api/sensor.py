"""Sensor platform for N.I.N.A. Advanced API."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .const import DEVICE_CAMERA, DEVICE_MOUNT
from .coordinator import NinaData, NinaDataUpdateCoordinator
from .entity import NinaEntity


@dataclass(frozen=True, kw_only=True)
class NinaSensorEntityDescription(SensorEntityDescription):
    """Describes a NINA sensor: how to read it from a NinaData snapshot."""

    value_fn: Callable[[NinaData], Any]


MOUNT_SENSORS: tuple[NinaSensorEntityDescription, ...] = (
    NinaSensorEntityDescription(
        key="mount_ra",
        translation_key="mount_ra",
        icon="mdi:telescope",
        value_fn=lambda d: d.mount.get("RightAscensionString"),
    ),
    NinaSensorEntityDescription(
        key="mount_dec",
        translation_key="mount_dec",
        icon="mdi:telescope",
        value_fn=lambda d: d.mount.get("DeclinationString"),
    ),
    NinaSensorEntityDescription(
        key="mount_altitude",
        translation_key="mount_altitude",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.mount.get("Altitude"),
    ),
    NinaSensorEntityDescription(
        key="mount_azimuth",
        translation_key="mount_azimuth",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.mount.get("Azimuth"),
    ),
)

CAMERA_SENSORS: tuple[NinaSensorEntityDescription, ...] = (
    NinaSensorEntityDescription(
        key="camera_temperature",
        translation_key="camera_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.camera.get("Temperature"),
    ),
    NinaSensorEntityDescription(
        key="camera_cooler_power",
        translation_key="camera_cooler_power",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:snowflake",
        value_fn=lambda d: d.camera.get("CoolerPower"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NinaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[NinaSensor] = [
        NinaSensor(coordinator, DEVICE_MOUNT, "Mount", description)
        for description in MOUNT_SENSORS
    ] + [
        NinaSensor(coordinator, DEVICE_CAMERA, "Kamera", description)
        for description in CAMERA_SENSORS
    ]
    async_add_entities(entities)


class NinaSensor(NinaEntity, SensorEntity):
    """A single read-only NINA value."""

    entity_description: NinaSensorEntityDescription

    def __init__(
        self,
        coordinator: NinaDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        description: NinaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_key, device_name, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
