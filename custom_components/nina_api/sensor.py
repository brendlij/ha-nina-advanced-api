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
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NinaConfigEntry
from .const import (
    CAMERA_STATES,
    DEVICE_APPLICATION,
    DEVICE_CAMERA,
    DEVICE_MOUNT,
    DEVICE_SEQUENCE,
)
from .coordinator import NinaData, NinaDataUpdateCoordinator
from .entity import NinaEntity


@dataclass(frozen=True, kw_only=True)
class NinaSensorEntityDescription(SensorEntityDescription):
    """Describes a NINA sensor: how to read it from a NinaData snapshot."""

    value_fn: Callable[[NinaData], Any]
    attrs_fn: Callable[[NinaData], dict[str, Any]] | None = None


APPLICATION_SENSORS: tuple[NinaSensorEntityDescription, ...] = (
    NinaSensorEntityDescription(
        key="nina_version",
        translation_key="nina_version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.nina_version,
    ),
    NinaSensorEntityDescription(
        key="api_version",
        translation_key="api_version",
        icon="mdi:api",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.api_version,
    ),
)

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
    NinaSensorEntityDescription(
        key="mount_sidereal_time",
        translation_key="mount_sidereal_time",
        icon="mdi:clock-star-four-points-outline",
        value_fn=lambda d: d.mount.get("SiderealTimeString"),
    ),
    NinaSensorEntityDescription(
        key="mount_time_to_meridian_flip",
        translation_key="mount_time_to_meridian_flip",
        icon="mdi:flip-horizontal",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.mount.get("TimeToMeridianFlip"),
    ),
    NinaSensorEntityDescription(
        key="mount_side_of_pier",
        translation_key="mount_side_of_pier",
        icon="mdi:arrow-decision",
        # PierSide serializes as an int: 0=East, 1=West, -1=Unknown.
        value_fn=lambda d: {0: "east", 1: "west"}.get(
            d.mount.get("SideOfPier"), "unknown"
        )
        if d.mount
        else None,
    ),
    NinaSensorEntityDescription(
        key="mount_name",
        translation_key="mount_name",
        icon="mdi:telescope",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.mount.get("DisplayName") or d.mount.get("Name"),
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
        key="camera_target_temperature",
        translation_key="camera_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.camera.get("TemperatureSetPoint"),
    ),
    NinaSensorEntityDescription(
        key="camera_cooler_power",
        translation_key="camera_cooler_power",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:snowflake",
        value_fn=lambda d: d.camera.get("CoolerPower"),
    ),
    NinaSensorEntityDescription(
        key="camera_state",
        translation_key="camera_state",
        icon="mdi:camera-iris",
        value_fn=lambda d: CAMERA_STATES.get(d.camera.get("CameraState")),
    ),
    NinaSensorEntityDescription(
        key="camera_gain",
        translation_key="camera_gain",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:brightness-6",
        value_fn=lambda d: d.camera.get("Gain"),
    ),
    NinaSensorEntityDescription(
        key="camera_offset",
        translation_key="camera_offset",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:tune",
        value_fn=lambda d: d.camera.get("Offset"),
    ),
    NinaSensorEntityDescription(
        key="camera_binning",
        translation_key="camera_binning",
        icon="mdi:grid",
        value_fn=lambda d: (
            f"{d.camera['BinX']}x{d.camera['BinY']}"
            if d.camera.get("BinX") and d.camera.get("BinY")
            else None
        ),
    ),
    NinaSensorEntityDescription(
        key="camera_last_download_time",
        translation_key="camera_last_download_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:download",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda d: d.camera.get("LastDownloadTime"),
    ),
    NinaSensorEntityDescription(
        key="camera_name",
        translation_key="camera_name",
        icon="mdi:camera",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.camera.get("DisplayName") or d.camera.get("Name"),
    ),
)

SEQUENCE_SENSORS: tuple[NinaSensorEntityDescription, ...] = (
    NinaSensorEntityDescription(
        key="sequence_current_item",
        translation_key="sequence_current_item",
        icon="mdi:playlist-play",
        value_fn=lambda d: d.sequence_current_item,
    ),
    NinaSensorEntityDescription(
        key="sequence_progress",
        translation_key="sequence_progress",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:progress-clock",
        value_fn=lambda d: d.sequence_progress,
        attrs_fn=lambda d: {
            "items_total": d.sequence_items_total,
            "items_finished": d.sequence_items_finished,
        },
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
        NinaSensor(coordinator, device_key, device_name, description)
        for device_key, device_name, descriptions in groups
        for description in descriptions
    )


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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
