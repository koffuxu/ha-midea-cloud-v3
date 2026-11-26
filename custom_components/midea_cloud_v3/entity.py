"""Base entity for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MideaDataUpdateCoordinator, MideaDeviceRuntime


class MideaEntity(CoordinatorEntity[MideaDataUpdateCoordinator]):
    """Base entity linked to a Midea device in MideaDataUpdateCoordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
    ) -> None:
        super().__init__(coordinator)
        self._appliance_code = appliance_code

    @property
    def device(self) -> MideaDeviceRuntime | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.devices.get(self._appliance_code)

    @property
    def available(self) -> bool:
        dev = self.device
        return super().available and dev is not None and dev.online

    @property
    def device_info(self) -> DeviceInfo:
        dev = self.device
        if dev is None:
            return DeviceInfo(identifiers={(DOMAIN, self._appliance_code)})
        model_suffix = dev.model_number or dev.spid
        model = f"{dev.category or dev.device_type} ({model_suffix})" if model_suffix else (
            dev.category or dev.device_type
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._appliance_code)},
            name=dev.name,
            manufacturer="Midea",
            model=model,
            sw_version=dev.thing_model.version if dev.thing_model else None,
            suggested_area=dev.room_name or None,
        )
