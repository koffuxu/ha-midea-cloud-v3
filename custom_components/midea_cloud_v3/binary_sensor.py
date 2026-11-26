"""Binary sensor platform for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity

PROP_HUMAN_PRESENCE = "humanPresenceSensor.humanPresenceState"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea binary sensor entities."""
    coordinator = entry.runtime_data
    entities: list[MideaOccupancySensor] = []
    for code, dev in coordinator.data.devices.items():
        if (
            dev.thing_model
            and PROP_HUMAN_PRESENCE in dev.thing_model.properties
            and dev.thing_model.properties[PROP_HUMAN_PRESENCE].readable
        ):
            entities.append(MideaOccupancySensor(coordinator, code))
    async_add_entities(entities)


class MideaOccupancySensor(MideaEntity, BinarySensorEntity):
    """Representation of a Midea human presence sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_name = "Occupancy"

    def __init__(
        self, coordinator: MideaDataUpdateCoordinator, appliance_code: str
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._attr_unique_id = f"{appliance_code}_{PROP_HUMAN_PRESENCE}"

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        if not dev or PROP_HUMAN_PRESENCE not in dev.properties:
            return None
        return dev.properties.get(PROP_HUMAN_PRESENCE) == 1
