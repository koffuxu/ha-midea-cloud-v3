"""DataUpdateCoordinator for Midea Cloud V3."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MideaApiError, MideaAuthError, MideaCloudV3Client, MideaDeviceOfflineError
from .const import (
    CONF_HOMEGROUP_IDS,
    CONF_INCLUDE_OFFLINE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .thing_model import ParsedThingModel, parse_thing_model

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MideaDeviceRuntime:
    """Runtime representation of a Midea device."""

    open_appliance_code: str
    name: str
    room_name: str
    device_type: str
    category: str
    spid: str
    sn8: str
    model_number: str
    enterprise: str
    homegroup_id: str
    homegroup_name: str
    online: bool
    thing_model: ParsedThingModel | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MideaSceneRuntime:
    """Runtime representation of a Midea one-click scene."""

    scene_id: str
    scene_name: str
    homegroup_id: str
    homegroup_name: str
    enable: bool


@dataclass(slots=True)
class MideaCoordinatorData:
    """Snapshot of all Midea homes, devices, and scenes."""

    user: dict[str, Any]
    homes: dict[str, str]
    devices: dict[str, MideaDeviceRuntime]
    scenes: dict[str, MideaSceneRuntime]


class MideaDataUpdateCoordinator(DataUpdateCoordinator[MideaCoordinatorData]):
    """Coordinator managing Midea Cloud V3 polling and thing-model caching."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: MideaCloudV3Client,
    ) -> None:
        scan_seconds = int(
            config_entry.options.get(
                CONF_SCAN_INTERVAL,
                config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds),
        )
        self.client = client
        self._thing_model_cache: dict[str, ParsedThingModel | None] = {}
        self._sem = asyncio.Semaphore(5)

    def _selected_homegroup_ids(self) -> set[str] | None:
        raw = self.config_entry.options.get(
            CONF_HOMEGROUP_IDS, self.config_entry.data.get(CONF_HOMEGROUP_IDS)
        )
        if not raw:
            return None
        return {str(x) for x in raw}

    def _include_offline(self) -> bool:
        return bool(
            self.config_entry.options.get(
                CONF_INCLUDE_OFFLINE,
                self.config_entry.data.get(CONF_INCLUDE_OFFLINE, True),
            )
        )

    async def _get_thing_model(self, spid: str) -> ParsedThingModel | None:
        if not spid:
            return None
        if spid in self._thing_model_cache:
            return self._thing_model_cache[spid]

        async with self._sem:
            if spid in self._thing_model_cache:
                return self._thing_model_cache[spid]
            try:
                meta = await self.client.async_get_thing_model_instance(spid)
                if not meta:
                    self._thing_model_cache[spid] = None
                    return None
                spec_url = meta.get("jsonFileUrl") or meta.get("simpleJsonFileUrl")
                if not spec_url:
                    self._thing_model_cache[spid] = None
                    return None
                spec_json = await self.client.async_fetch_json_url(spec_url)
                parsed = parse_thing_model(
                    spid,
                    spec_json,
                    version=str(meta.get("currentVersion") or ""),
                )
                self._thing_model_cache[spid] = parsed
                return parsed
            except MideaAuthError:
                raise
            except MideaApiError as err:
                _LOGGER.debug("Could not fetch thing-model for spid %s: %s", spid, err)
                return None

    async def _fetch_device_properties(
        self, dev: MideaDeviceRuntime
    ) -> None:
        if not dev.online:
            return
        async with self._sem:
            try:
                dev.properties = await self.client.async_get_entire_properties(
                    dev.open_appliance_code
                )
            except MideaDeviceOfflineError:
                dev.online = False
                dev.properties = {}
            except MideaAuthError:
                raise
            except MideaApiError as err:
                _LOGGER.debug(
                    "Failed reading properties for %s (%s): %s",
                    dev.name,
                    dev.open_appliance_code,
                    err,
                )

    async def _async_update_data(self) -> MideaCoordinatorData:
        try:
            user = await self.client.async_get_user()
            raw_homes = user.get("homegroupList") or []
            all_homes: dict[str, str] = {
                str(h["openHomegroupId"]): str(h.get("homegroupName") or h["openHomegroupId"])
                for h in raw_homes
                if h.get("openHomegroupId") is not None
            }

            selected_ids = self._selected_homegroup_ids()
            target_homes = (
                {hid: name for hid, name in all_homes.items() if hid in selected_ids}
                if selected_ids is not None
                else all_homes
            )

            include_offline = self._include_offline()
            devices: dict[str, MideaDeviceRuntime] = {}
            scenes: dict[str, MideaSceneRuntime] = {}

            for hid, hname in target_homes.items():
                raw_devs = await self.client.async_get_devices(hid)
                for raw in raw_devs:
                    code = str(raw.get("openApplianceCode") or "")
                    if not code:
                        continue
                    online = str(raw.get("onlineStatus")) == "1"
                    if not include_offline and not online:
                        continue
                    devices[code] = MideaDeviceRuntime(
                        open_appliance_code=code,
                        name=str(raw.get("name") or code),
                        room_name=str(raw.get("roomName") or ""),
                        device_type=str(raw.get("type") or ""),
                        category=str(raw.get("category") or ""),
                        spid=str(raw.get("spid") or ""),
                        sn8=str(raw.get("sn8") or ""),
                        model_number=str(raw.get("modelNumber") or ""),
                        enterprise=str(raw.get("enterprise") or ""),
                        homegroup_id=hid,
                        homegroup_name=hname,
                        online=online,
                    )

                raw_scenes = await self.client.async_get_scenes(hid)
                for sc in raw_scenes:
                    sid = str(sc.get("sceneId") or "")
                    if not sid or str(sc.get("enable")) != "1":
                        continue
                    scenes[sid] = MideaSceneRuntime(
                        scene_id=sid,
                        scene_name=str(sc.get("sceneName") or sid),
                        homegroup_id=hid,
                        homegroup_name=hname,
                        enable=True,
                    )

            unique_spids = {d.spid for d in devices.values() if d.spid}
            await asyncio.gather(*(self._get_thing_model(spid) for spid in unique_spids))
            for dev in devices.values():
                if dev.spid:
                    dev.thing_model = self._thing_model_cache.get(dev.spid)

            await asyncio.gather(*(self._fetch_device_properties(d) for d in devices.values()))

            return MideaCoordinatorData(
                user=user,
                homes=all_homes,
                devices=devices,
                scenes=scenes,
            )
        except MideaAuthError as err:
            raise ConfigEntryAuthFailed(f"Midea authentication failed: {err}") from err
        except MideaApiError as err:
            raise UpdateFailed(f"Error communicating with Midea Cloud V3: {err}") from err
