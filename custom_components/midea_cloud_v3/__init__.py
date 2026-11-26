"""The Midea Cloud V3 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from .api import MideaCloudV3Client
from .const import PLATFORMS
from .coordinator import MideaDataUpdateCoordinator

type MideaConfigEntry = ConfigEntry[MideaDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MideaConfigEntry) -> bool:
    """Set up Midea Cloud V3 from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    async def _get_access_token() -> str:
        await session.async_ensure_token_valid()
        return str(session.token["access_token"])

    client = MideaCloudV3Client(
        aiohttp_client.async_get_clientsession(hass),
        implementation.client_id,
        getattr(implementation, "client_secret", ""),
        _get_access_token,
    )
    coordinator = MideaDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: MideaConfigEntry
) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MideaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
