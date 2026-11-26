"""Application credentials platform for Midea Cloud V3."""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import OAUTH2_AUTHORIZE_URL, OAUTH2_TOKEN_URL
from .oauth import MideaOAuth2Implementation


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server for Midea Cloud V3."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE_URL,
        token_url=OAUTH2_TOKEN_URL,
    )


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return custom Midea OAuth2 implementation."""
    server = await async_get_authorization_server(hass)
    return MideaOAuth2Implementation(hass, auth_domain, credential, server)
