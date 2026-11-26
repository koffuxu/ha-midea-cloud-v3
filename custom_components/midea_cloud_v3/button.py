"""Button platform for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity
from .thing_model import ActionSpec

BUTTON_ACTIONS: dict[str, str] = {
    "aiVoice.aiWakeUp": "Wake Up Voice",
    "light.deviceIdentify": "Identify Light",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea button entities."""
    coordinator = entry.runtime_data
    entities: list[MideaButton] = []
    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        for key, label in BUTTON_ACTIONS.items():
            act = dev.thing_model.actions.get(key)
            if act and not act.input_keys:
                entities.append(MideaButton(coordinator, code, act, label))
    async_add_entities(entities)


class MideaButton(MideaEntity, ButtonEntity):
    """Representation of a parameterless Midea thing-model action."""

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
        action: ActionSpec,
        name: str,
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._action = action
        self._attr_name = name
        self._attr_unique_id = f"{appliance_code}_{action.key}"

    async def async_press(self) -> None:
        await self.coordinator.client.async_invoke_action(
            self._appliance_code,
            self._action.module,
            self._action.code,
            {},
        )
