"""Light platform for Midea Cloud V3."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity

MODULE_LIGHT = "light"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea light entities."""
    coordinator = entry.runtime_data
    entities: list[MideaLight] = []
    for code, dev in coordinator.data.devices.items():
        if (
            dev.thing_model
            and dev.thing_model.has_module(MODULE_LIGHT)
            and f"{MODULE_LIGHT}.power" in dev.thing_model.properties
        ):
            entities.append(MideaLight(coordinator, code))
    async_add_entities(entities)


class MideaLight(MideaEntity, LightEntity):
    """Representation of a Midea smart light."""

    _attr_name = None

    def __init__(self, coordinator: MideaDataUpdateCoordinator, appliance_code: str) -> None:
        super().__init__(coordinator, appliance_code)
        self._attr_unique_id = f"{appliance_code}_{MODULE_LIGHT}"
        dev = self.device
        props = dev.thing_model.module_properties(MODULE_LIGHT) if dev and dev.thing_model else {}

        self._has_brightness = "brightness" in props and props["brightness"].writable
        self._has_color_temp = "colorTemperature" in props and props["colorTemperature"].writable

        if self._has_color_temp:
            ct_spec = props["colorTemperature"]
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = int(ct_spec.minimum or 1800)
            self._attr_max_color_temp_kelvin = int(ct_spec.maximum or 6500)
        elif self._has_brightness:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        if not dev or f"{MODULE_LIGHT}.power" not in dev.properties:
            return None
        return bool(dev.properties.get(f"{MODULE_LIGHT}.power"))

    @property
    def brightness(self) -> int | None:
        if not self._has_brightness:
            return None
        dev = self.device
        if not dev:
            return None
        raw = dev.properties.get(f"{MODULE_LIGHT}.brightness")
        if raw is None:
            return None
        return max(1, min(255, round(int(raw) * 255 / 100)))

    @property
    def color_temp_kelvin(self) -> int | None:
        if not self._has_color_temp:
            return None
        dev = self.device
        if not dev:
            return None
        raw = dev.properties.get(f"{MODULE_LIGHT}.colorTemperature")
        return int(raw) if raw is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        updates: dict[str, Any] = {f"{MODULE_LIGHT}.power": True}
        if self._has_brightness and ATTR_BRIGHTNESS in kwargs:
            ha_br = int(kwargs[ATTR_BRIGHTNESS])
            updates[f"{MODULE_LIGHT}.brightness"] = max(1, min(100, round(ha_br * 100 / 255)))
        if self._has_color_temp and ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            min_k = self._attr_min_color_temp_kelvin or 1800
            max_k = self._attr_max_color_temp_kelvin or 6500
            updates[f"{MODULE_LIGHT}.colorTemperature"] = max(min_k, min(max_k, kelvin))
        await self.coordinator.client.async_modify_properties(self._appliance_code, updates)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {f"{MODULE_LIGHT}.power": False}
        )
        await self.coordinator.async_request_refresh()
