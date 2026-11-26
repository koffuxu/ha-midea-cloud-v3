"""Scene platform for Midea Cloud V3 (one-click smart scenes)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MideaConfigEntry
from .const import DOMAIN
from .coordinator import MideaDataUpdateCoordinator, MideaSceneRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MideaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Midea one-click scenes."""
    coordinator = entry.runtime_data
    entities = [
        MideaScene(coordinator, scene)
        for scene in coordinator.data.scenes.values()
    ]
    async_add_entities(entities)


class MideaScene(CoordinatorEntity[MideaDataUpdateCoordinator], Scene):
    """Representation of a Midea one-click scene."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MideaDataUpdateCoordinator,
        scene: MideaSceneRuntime,
    ) -> None:
        super().__init__(coordinator)
        self._scene = scene
        self._attr_unique_id = f"scene_{scene.homegroup_id}_{scene.scene_id}"
        self._attr_name = scene.scene_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"home_{scene.homegroup_id}")},
            name=f"Midea {scene.homegroup_name}",
            manufacturer="Midea",
            model="Smart Homegroup",
        )

    async def async_activate(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_execute_scene(
            self._scene.homegroup_id, self._scene.scene_id
        )
