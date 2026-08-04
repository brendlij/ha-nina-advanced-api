"""Shared entity base classes."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import NinaDataUpdateCoordinator


class NinaEntity(CoordinatorEntity[NinaDataUpdateCoordinator]):
    """Base entity tying every NINA entity to one logical device per sub-system."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NinaDataUpdateCoordinator,
        device_key: str,
        device_name: str,
        unique_id_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{device_key}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{device_key}")},
            name=device_name,
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, entry_id),
        )

    @property
    def available(self) -> bool:
        """Entities read as unavailable while N.I.N.A. is not answering.

        The coordinator deliberately keeps succeeding when NINA is closed
        (see NinaDataUpdateCoordinator._async_update_data), so availability
        hangs off the connection flag rather than last_update_success. That
        way the entities stay in the registry across a NINA restart instead
        of disappearing from it.
        """
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.application_connected
        )
