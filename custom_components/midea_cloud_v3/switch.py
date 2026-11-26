"""Switch platform for Midea Cloud V3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity


@dataclass(frozen=True, slots=True)
class SwitchMapping:
    """Mapping from thing-model property to HA switch."""

    read_key: str
    write_key: str
    name: str
    on_value: Any = True
    off_value: Any = False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea switch entities."""
    coordinator = entry.runtime_data
    entities: list[MideaSwitch] = []

    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        props = dev.thing_model.properties

        for mod in dev.thing_model.modules:
            if mod == "wallSwitch" or (mod.startswith("wallSwitch") and mod[10:].isdigit()):
                p_key = f"{mod}.power"
                if p_key in props and props[p_key].writable:
                    suffix = mod[10:]
                    label = f"Switch {suffix}" if suffix else "Switch"
                    entities.append(
                        MideaSwitch(
                            coordinator,
                            code,
                            SwitchMapping(read_key=p_key, write_key=p_key, name=label),
                        )
                    )

        if "screenSwitch.switchControl" in props and props["screenSwitch.switchControl"].writable:
            entities.append(
                MideaSwitch(
                    coordinator,
                    code,
                    SwitchMapping(
                        read_key="screenSwitch.switchControl",
                        write_key="screenSwitch.switchControl",
                        name="Switch",
                        on_value=1,
                        off_value=0,
                    ),
                )
            )

        if (
            "connectedStateLight.connectedStateLightSwitch" in props
            and props["connectedStateLight.connectedStateLightSwitch"].writable
        ):
            entities.append(
                MideaSwitch(
                    coordinator,
                    code,
                    SwitchMapping(
                        read_key="connectedStateLight.connectedStateLightSwitch",
                        write_key="connectedStateLight.connectedStateLightSwitch",
                        name="Status Light",
                    ),
                )
            )

        if (
            "microphone.microphoneSwitchControl" in props
            and props["microphone.microphoneSwitchControl"].writable
        ):
            entities.append(
                MideaSwitch(
                    coordinator,
                    code,
                    SwitchMapping(
                        read_key="microphone.microphoneSwitchStatus",
                        write_key="microphone.microphoneSwitchControl",
                        name="Microphone",
                        on_value=1,
                        off_value=0,
                    ),
                )
            )

    async_add_entities(entities)


class MideaSwitch(MideaEntity, SwitchEntity):
    """Representation of a Midea switchable property."""

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
        mapping: SwitchMapping,
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._mapping = mapping
        self._attr_name = mapping.name
        self._attr_unique_id = f"{appliance_code}_{mapping.write_key}"

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        if not dev or self._mapping.read_key not in dev.properties:
            return None
        val = dev.properties.get(self._mapping.read_key)
        if isinstance(self._mapping.on_value, bool):
            return bool(val)
        if isinstance(val, bool):
            return val
        return val == self._mapping.on_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._mapping.write_key: self._mapping.on_value}
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._mapping.write_key: self._mapping.off_value}
        )
        await self.coordinator.async_request_refresh()
