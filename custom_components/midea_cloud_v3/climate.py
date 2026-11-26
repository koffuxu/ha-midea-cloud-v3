"""Climate platform for Midea Cloud V3 (air conditioners)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity

_HVAC_MAP = {
    "cool": HVACMode.COOL,
    "cooling": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "heating": HVACMode.HEAT,
    "dry": HVACMode.DRY,
    "dehumidify": HVACMode.DRY,
    "fan": HVACMode.FAN_ONLY,
    "fanonly": HVACMode.FAN_ONLY,
    "fan_only": HVACMode.FAN_ONLY,
    "wind": HVACMode.FAN_ONLY,
    "auto": HVACMode.AUTO,
}


def _find_ac_module(modules: tuple[str, ...]) -> str | None:
    for candidate in ("airConditioner", "ac"):
        if candidate in modules:
            return candidate
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea climate entities."""
    coordinator = entry.runtime_data
    entities: list[MideaClimate] = []
    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        mod = _find_ac_module(dev.thing_model.modules)
        if mod and f"{mod}.targetTemperature" in dev.thing_model.properties:
            entities.append(MideaClimate(coordinator, code, mod))
    async_add_entities(entities)


class MideaClimate(MideaEntity, ClimateEntity):
    """Representation of a Midea air conditioner."""

    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
        module_code: str,
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._module = module_code
        self._attr_unique_id = f"{appliance_code}_{module_code}"

        dev = self.device
        props = dev.thing_model.module_properties(module_code) if dev and dev.thing_model else {}
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        self._temp_key = f"{module_code}.targetTemperature"
        if "targetTemperature" in props:
            t_spec = props["targetTemperature"]
            self._attr_min_temp = float(t_spec.minimum or 16.0)
            self._attr_max_temp = float(t_spec.maximum or 30.0)
            self._attr_target_temperature_step = float(t_spec.precision or 0.5)

        self._indoor_key = (
            f"{module_code}.indoorTemperature"
            if "indoorTemperature" in props
            else f"{module_code}.currentTemperature"
        )
        self._power_key = f"{module_code}.power" if "power" in props else None
        self._mode_key = f"{module_code}.mode" if "mode" in props else None

        self._ha_to_midea_mode: dict[HVACMode, Any] = {}
        self._midea_to_ha_mode: dict[Any, HVACMode] = {}
        hvac_modes: list[HVACMode] = [HVACMode.OFF]
        if "mode" in props:
            for e_code, val in props["mode"].code_to_value.items():
                ha_mode = _HVAC_MAP.get(e_code.lower())
                if ha_mode and ha_mode not in hvac_modes:
                    hvac_modes.append(ha_mode)
                    self._ha_to_midea_mode[ha_mode] = val
                if ha_mode:
                    self._midea_to_ha_mode[val] = ha_mode
        if len(hvac_modes) == 1:
            hvac_modes.append(HVACMode.AUTO)
        self._attr_hvac_modes = hvac_modes

        self._fan_key = None
        for fan_cand in ("windSpeed", "fanSpeed"):
            if fan_cand in props and props[fan_cand].writable:
                self._fan_key = f"{module_code}.{fan_cand}"
                features |= ClimateEntityFeature.FAN_MODE
                self._fan_spec = props[fan_cand]
                self._attr_fan_modes = list(self._fan_spec.label_to_value.keys()) or None
                break

        self._attr_supported_features = features

    @property
    def native_current_temperature(self) -> float | None:
        dev = self.device
        if not dev:
            return None
        val = dev.properties.get(self._indoor_key)
        return float(val) if val is not None else None

    @property
    def native_target_temperature(self) -> float | None:
        dev = self.device
        if not dev:
            return None
        val = dev.properties.get(self._temp_key)
        return float(val) if val is not None else None

    @property
    def hvac_mode(self) -> HVACMode | None:
        dev = self.device
        if not dev:
            return None
        if self._power_key and dev.properties.get(self._power_key) is False:
            return HVACMode.OFF
        if self._mode_key and self._mode_key in dev.properties:
            raw_mode = dev.properties.get(self._mode_key)
            return self._midea_to_ha_mode.get(raw_mode, HVACMode.AUTO)
        return HVACMode.AUTO

    @property
    def fan_mode(self) -> str | None:
        if not self._fan_key or not self.device:
            return None
        raw = self.device.properties.get(self._fan_key)
        return self._fan_spec.value_to_label.get(raw)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE not in kwargs:
            return
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._temp_key: float(kwargs[ATTR_TEMPERATURE])}
        )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            if self._power_key:
                await self.coordinator.client.async_modify_properties(
                    self._appliance_code, {self._power_key: False}
                )
        else:
            updates: dict[str, Any] = {}
            if self._power_key:
                updates[self._power_key] = True
            if self._mode_key and hvac_mode in self._ha_to_midea_mode:
                updates[self._mode_key] = self._ha_to_midea_mode[hvac_mode]
            if updates:
                await self.coordinator.client.async_modify_properties(
                    self._appliance_code, updates
                )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if not self._fan_key:
            return
        val = self._fan_spec.label_to_value.get(fan_mode)
        if val is None:
            return
        await self.coordinator.client.async_modify_properties(
            self._appliance_code, {self._fan_key: val}
        )
        await self.coordinator.async_request_refresh()
