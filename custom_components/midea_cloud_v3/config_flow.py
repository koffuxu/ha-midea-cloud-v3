"""Config flow for Midea Cloud V3."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow, selector

from .api import MideaApiError, MideaCloudV3Client
from .const import (
    CONF_HOMEGROUP_IDS,
    CONF_INCLUDE_OFFLINE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class MideaCloudV3FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle OAuth2 config flow for Midea Cloud V3."""

    DOMAIN = DOMAIN

    def __init__(self) -> None:
        super().__init__()
        self._oauth_data: dict[str, Any] = {}
        self._user_info: dict[str, Any] = {}

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MideaCloudV3OptionsFlow()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Fetch Midea user/homes after OAuth2 token exchange."""
        token = data["token"]["access_token"]

        async def _token_provider() -> str:
            return str(token)

        client = MideaCloudV3Client(
            aiohttp_client.async_get_clientsession(self.hass),
            self.flow_impl.client_id,
            getattr(self.flow_impl, "client_secret", ""),
            _token_provider,
        )
        try:
            user = await client.async_get_user()
        except MideaApiError as err:
            _LOGGER.error("Failed to fetch Midea user profile: %s", err)
            return self.async_abort(reason="cannot_connect")

        open_uid = str(user.get("openUid") or "")
        if not open_uid:
            return self.async_abort(reason="missing_user_id")

        await self.async_set_unique_id(open_uid)
        if self.source == "reauth":
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )

        self._abort_if_unique_id_configured()
        self._oauth_data = data
        self._user_info = user
        return await self.async_step_configure()

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose which homes and polling options to include."""
        raw_homes = self._user_info.get("homegroupList") or []
        home_options = [
            selector.SelectOptionDict(
                value=str(h["openHomegroupId"]),
                label=str(h.get("homegroupName") or h["openHomegroupId"]),
            )
            for h in raw_homes
            if h.get("openHomegroupId") is not None
        ]
        all_home_ids = [opt["value"] for opt in home_options]

        if user_input is not None:
            entry_data = {
                **self._oauth_data,
                CONF_HOMEGROUP_IDS: user_input.get(CONF_HOMEGROUP_IDS, all_home_ids),
                CONF_INCLUDE_OFFLINE: user_input.get(CONF_INCLUDE_OFFLINE, True),
                CONF_SCAN_INTERVAL: int(
                    user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
            }
            title_name = str(self._user_info.get("userName") or self._user_info.get("openUid"))
            return self.async_create_entry(
                title=f"Midea ({title_name})",
                data=entry_data,
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOMEGROUP_IDS, default=all_home_ids): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=home_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_INCLUDE_OFFLINE, default=True): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="configure", data_schema=schema)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication before redirecting to Midea OAuth."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()


class MideaCloudV3OptionsFlow(OptionsFlow):
    """Handle options flow for Midea Cloud V3."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        coordinator = self.config_entry.runtime_data
        homes = coordinator.data.homes if coordinator.data else {}
        home_options = [
            selector.SelectOptionDict(value=hid, label=name)
            for hid, name in homes.items()
        ]
        current_homes = list(
            self.config_entry.options.get(
                CONF_HOMEGROUP_IDS,
                self.config_entry.data.get(CONF_HOMEGROUP_IDS, list(homes.keys())),
            )
        )
        current_offline = bool(
            self.config_entry.options.get(
                CONF_INCLUDE_OFFLINE,
                self.config_entry.data.get(CONF_INCLUDE_OFFLINE, True),
            )
        )
        current_interval = int(
            self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_HOMEGROUP_IDS: user_input.get(CONF_HOMEGROUP_IDS, current_homes),
                    CONF_INCLUDE_OFFLINE: bool(user_input.get(CONF_INCLUDE_OFFLINE, True)),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOMEGROUP_IDS, default=current_homes): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=home_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_INCLUDE_OFFLINE, default=current_offline): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
