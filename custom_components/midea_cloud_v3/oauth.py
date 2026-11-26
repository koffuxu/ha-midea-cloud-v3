"""Custom OAuth2 implementation for Midea Cloud V3 JSON token endpoint."""

from __future__ import annotations

import json
from typing import Any, override

import aiohttp
from homeassistant.components import application_credentials
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow


class MideaOAuth2Implementation(application_credentials.AuthImplementation):
    """Midea Cloud V3 OAuth2 implementation using JSON token requests."""

    @override
    async def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Exchange authorization code or refresh token via JSON POST."""
        grant_type = data.get("grant_type")
        if grant_type == "authorization_code":
            payload: dict[str, Any] = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": data["code"],
            }
        elif grant_type == "refresh_token":
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": data["refresh_token"],
            }
        else:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                **data,
            }

        session = aiohttp_client.async_get_clientsession(self.hass)
        redirect_uri = data.get("redirect_uri")

        for attempt in range(2):
            try:
                async with session.post(
                    self.token_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    raw_text = await resp.text()
                    if resp.status >= 500:
                        raise config_entry_oauth2_flow.OAuth2TokenRequestTransientError(
                            domain=self.service_domain
                        )
                    if resp.status >= 400:
                        if (
                            attempt == 0
                            and grant_type == "authorization_code"
                            and redirect_uri
                            and "1001" in raw_text
                        ):
                            payload["redirect_uri"] = redirect_uri
                            continue
                        raise config_entry_oauth2_flow.OAuth2TokenRequestReauthError(
                            domain=self.service_domain
                        )
                    try:
                        token_data = json.loads(raw_text)
                    except ValueError as err:
                        raise config_entry_oauth2_flow.OAuth2TokenRequestTransientError(
                            domain=self.service_domain
                        ) from err

                    if not isinstance(token_data, dict) or not token_data.get("access_token"):
                        raise config_entry_oauth2_flow.OAuth2TokenRequestReauthError(
                            domain=self.service_domain
                        )
                    return token_data
            except (aiohttp.ClientError, TimeoutError) as err:
                raise config_entry_oauth2_flow.OAuth2TokenRequestTransientError(
                    domain=self.service_domain
                ) from err

        raise config_entry_oauth2_flow.OAuth2TokenRequestTransientError(
            domain=self.service_domain
        )
