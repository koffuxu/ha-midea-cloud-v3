"""Cover platform for Midea Cloud V3 (electric curtains)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity

MODULE_CURTAIN = "electricCurtain"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea cover entities."""
    coordinator = entry.runtime_data
    entities: list[MideaCurtainCover] = []
    for code, dev in coordinator.data.devices.items():
        if dev.thing_model and dev.thing_model.has_module(MODULE_CURTAIN):
            entities.append(MideaCurtainCover(coordinator, code))
    async_add_entities(entities)


class MideaCurtainCover(MideaEntity, CoverEntity):
    """Representation of a Midea electric curtain."""

    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_name = None

    def __init__(self, coordinator: MideaDataUpdateCoordinator, appliance_code: str) -> None:
        super().__init__(coordinator, appliance_code)
        self._attr_unique_id = f"{appliance_code}_{MODULE_CURTAIN}"
        features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
        )
        dev = self.device
        if (
            dev
            and dev.thing_model
            and f"{MODULE_CURTAIN}.targetOpeningPercentage" in dev.thing_model.properties
            and dev.thing_model.properties[f"{MODULE_CURTAIN}.targetOpeningPercentage"].writable
        ):
            features |= CoverEntityFeature.SET_POSITION
        self._attr_supported_features = features

    @property
    def current_cover_position(self) -> int | None:
        dev = self.device
        if not dev:
            return None
        val = dev.properties.get(f"{MODULE_CURTAIN}.currentOpeningPercentage")
        if val is None:
            return None
        try:
            return max(0, min(100, int(val)))
        except (TypeError, ValueError):
            return None

    @property
    def is_opening(self) -> bool | None:
        dev = self.device
        if not dev or f"{MODULE_CURTAIN}.workStatus" not in dev.properties:
            return None
        return dev.properties.get(f"{MODULE_CURTAIN}.workStatus") == 1

    @property
    def is_closing(self) -> bool | None:
        dev = self.device
        if not dev or f"{MODULE_CURTAIN}.workStatus" not in dev.properties:
            return None
        return dev.properties.get(f"{MODULE_CURTAIN}.workStatus") == 2

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        if self.is_opening:
            return False
        return pos == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_invoke_action(
            self._appliance_code, MODULE_CURTAIN, "open", {}
        )
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_invoke_action(
            self._appliance_code, MODULE_CURTAIN, "close", {}
        )
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_invoke_action(
            self._appliance_code, MODULE_CURTAIN, "pause", {}
        )
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = int(kwargs[ATTR_POSITION])
        await self.coordinator.client.async_modify_properties(
            self._appliance_code,
            {f"{MODULE_CURTAIN}.targetOpeningPercentage": position},
        )
        await self.coordinator.async_request_refresh()
