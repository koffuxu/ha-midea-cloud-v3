"""Sensor platform for Midea Cloud V3."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfDensity,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MideaConfigEntry
from .coordinator import MideaDataUpdateCoordinator
from .entity import MideaEntity


@dataclass(frozen=True, slots=True)
class SensorMapping:
    """Mapping from Midea property key to HA Sensor metadata."""

    prop_key: str
    name: str
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


SENSOR_MAPPINGS: tuple[SensorMapping, ...] = (
    SensorMapping(
        "temperatureHumiditySensor.currentTemperature",
        "Temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    SensorMapping(
        "temperatureHumiditySensor.currentHumidity",
        "Humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
    ),
    SensorMapping(
        "airQuality.currentTvoc",
        "TVOC",
        SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
    ),
    SensorMapping(
        "airQuality.pm25",
        "PM2.5",
        SensorDeviceClass.PM25,
        UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
    ),
    SensorMapping(
        "airQuality.co2",
        "CO2",
        SensorDeviceClass.CO2,
        UnitOfRatio.PARTS_PER_MILLION,
    ),
    SensorMapping(
        "humanPresenceSensor.illumination",
        "Illuminance",
        SensorDeviceClass.ILLUMINANCE,
        LIGHT_LUX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea sensor entities."""
    coordinator = entry.runtime_data
    entities: list[MideaSensor] = []

    for code, dev in coordinator.data.devices.items():
        if not dev.thing_model:
            continue
        props = dev.thing_model.properties
        for mapping in SENSOR_MAPPINGS:
            if mapping.prop_key in props and props[mapping.prop_key].readable:
                entities.append(MideaSensor(coordinator, code, mapping))

    async_add_entities(entities)


class MideaSensor(MideaEntity, SensorEntity):
    """Representation of a Midea read-only sensor property."""

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        appliance_code: str,
        mapping: SensorMapping,
    ) -> None:
        super().__init__(coordinator, appliance_code)
        self._mapping = mapping
        self._attr_name = mapping.name
        self._attr_unique_id = f"{appliance_code}_{mapping.prop_key}"
        self._attr_device_class = mapping.device_class
        self._attr_native_unit_of_measurement = mapping.unit
        self._attr_state_class = mapping.state_class

    @property
    def native_value(self) -> float | int | str | None:
        dev = self.device
        if not dev or self._mapping.prop_key not in dev.properties:
            return None
        return dev.properties.get(self._mapping.prop_key)
