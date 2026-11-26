"""Number platform for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity
from .thing_model import PropertySpec

NUMBER_CANDIDATES: dict[str, str] = {
    "speaker.mediaVolume": "Media Volume",
    "speaker.systemVolume": "System Volume",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea number entities."""
    coordinator = entry.runtime_data
    entities: list[MideaNumber] = []
    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        for key, label in NUMBER_CANDIDATES.items():
            spec = dev.thing_model.properties.get(key)
            if spec and spec.writable:
                entities.append(MideaNumber(coordinator, code, spec, label))
    async_add_entities(entities)


class MideaNumber(MideaEntity, NumberEntity):
    """Representation of a Midea writable numeric property."""

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
        spec: PropertySpec,
        name: str,
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._spec = spec
        self._attr_name = name
        self._attr_unique_id = f"{appliance_code}_{spec.key}"
        self._attr_native_min_value = float(spec.minimum if spec.minimum is not None else 0)
        self._attr_native_max_value = float(spec.maximum if spec.maximum is not None else 100)
        self._attr_native_step = float(spec.precision if spec.precision is not None else 1)
        if spec.unit == "percentage" or "Volume" in spec.code:
            self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        dev = self.device
        if not dev or self._spec.key not in dev.properties:
            return None
        val = dev.properties.get(self._spec.key)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        send_val: int | float = int(round(value)) if "int" in self._spec.data_type else value
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._spec.key: send_val}
        )
        await self.coordinator.async_request_refresh()
