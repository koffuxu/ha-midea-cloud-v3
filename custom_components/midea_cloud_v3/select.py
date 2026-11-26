"""Select platform for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity
from .thing_model import PropertySpec

SELECT_CANDIDATES: dict[str, str] = {
    "screenDisplay.screenDisplaySwitch": "Screen Display",
    "electricCurtain.motorSpeed": "Motor Speed",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea select entities."""
    coordinator = entry.runtime_data
    entities: list[MideaSelect] = []
    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        for key, label in SELECT_CANDIDATES.items():
            spec = dev.thing_model.properties.get(key)
            if spec and spec.writable and spec.label_to_value:
                entities.append(MideaSelect(coordinator, code, spec, label))
    async_add_entities(entities)


class MideaSelect(MideaEntity, SelectEntity):
    """Representation of a Midea writable enum property."""

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
        self._attr_options = list(spec.label_to_value.keys())

    @property
    def current_option(self) -> str | None:
        dev = self.device
        if not dev or self._spec.key not in dev.properties:
            return None
        raw = dev.properties.get(self._spec.key)
        return self._spec.value_to_label.get(raw)

    async def async_select_option(self, option: str) -> None:
        val = self._spec.label_to_value.get(option)
        if val is None:
            return
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._spec.key: val}
        )
        await self.coordinator.async_request_refresh()
