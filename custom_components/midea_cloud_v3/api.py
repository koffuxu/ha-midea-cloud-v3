"""Pure async client for Midea IoT Cloud-to-Cloud V3 API."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

API_BASE_URL = "https://api-prod.smartmidea.net"
SIGNATURE_VERSION = "2.0"

AUTH_ERROR_CODES = {"1006", "2001", "2003"}
OFFLINE_ERROR_CODES = {"41102"}


class MideaApiError(Exception):
    """Base exception for Midea Cloud V3 API errors."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        error_code: str | None = None,
        error_description: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.error_description = error_description


class MideaAuthError(MideaApiError):
    """Authentication or authorization error (expired/invalid token or client)."""


class MideaDeviceOfflineError(MideaApiError):
    """Device is offline on Midea Cloud (error 41102)."""


def build_signature(
    client_secret: str,
    method: str,
    uri: str,
    query_string: str,
    body_str: str,
) -> str:
    """Compute Midea V3 HMAC-SHA256 Base64 signature."""
    to_sign = f"{method}{uri}{query_string}{body_str}"
    digest = hmac.new(
        client_secret.encode("utf-8"),
        to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _new_req_meta() -> dict[str, str]:
    """Generate Midea V3 reqId (32-char alphanumeric) and millisecond stamp."""
    return {
        "reqId": uuid.uuid4().hex,
        "stamp": time.strftime("%Y%m%d%H%M%S000"),
    }


def _parse_error_payload(raw_text: str) -> tuple[str | None, str | None]:
    """Extract error code and description from JSON error body if present."""
    try:
        parsed = json.loads(raw_text)
    except ValueError:
        return None, raw_text[:300]
    if isinstance(parsed, dict):
        code = parsed.get("error") or parsed.get("code")
        desc = (
            parsed.get("error_description")
            or parsed.get("message")
            or parsed.get("msg")
        )
        return (str(code) if code is not None else None), (
            str(desc) if desc is not None else raw_text[:300]
        )
    return None, raw_text[:300]


class MideaCloudV3Client:
    """Async client for Midea IoT Cloud-to-Cloud V3 API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        token_provider: Callable[[], Awaitable[str]],
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_provider = token_provider
        self._base_url = base_url.rstrip("/")
        self._token_lock = asyncio.Lock()

    async def _get_token(self) -> str:
        async with self._token_lock:
            return await self._token_provider()

    async def _request(
        self,
        method: str,
        uri: str,
        *,
        query_params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._get_token()
        query_string = urllib.parse.urlencode(query_params) if query_params else ""
        body_str = (
            json.dumps(json_body, ensure_ascii=False, separators=(",", ":"))
            if json_body is not None
            else ""
        )
        signature = build_signature(
            self._client_secret, method, uri, query_string, body_str
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "ClientId": self._client_id,
            "SignatureVersion": SIGNATURE_VERSION,
            "Signature": signature,
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        url = f"{self._base_url}{uri}"
        if query_string:
            url = f"{url}?{query_string}"

        try:
            async with self._session.request(
                method,
                url,
                data=body_str.encode("utf-8") if body_str else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                raw_text = await resp.text()
                if resp.status in (401, 403):
                    code, desc = _parse_error_payload(raw_text)
                    raise MideaAuthError(
                        f"HTTP {resp.status} on {uri}: {desc}",
                        http_status=resp.status,
                        error_code=code,
                        error_description=desc,
                    )
                if resp.status >= 400:
                    code, desc = _parse_error_payload(raw_text)
                    if code in AUTH_ERROR_CODES:
                        raise MideaAuthError(
                            f"Auth error {code} on {uri}: {desc}",
                            http_status=resp.status,
                            error_code=code,
                            error_description=desc,
                        )
                    if code in OFFLINE_ERROR_CODES:
                        raise MideaDeviceOfflineError(
                            f"Device offline on {uri}: {desc}",
                            http_status=resp.status,
                            error_code=code,
                            error_description=desc,
                        )
                    raise MideaApiError(
                        f"HTTP {resp.status} on {uri}: {desc}",
                        http_status=resp.status,
                        error_code=code,
                        error_description=desc,
                    )

                try:
                    data = json.loads(raw_text)
                except ValueError as err:
                    raise MideaApiError(
                        f"Invalid JSON from {uri}: {raw_text[:200]}",
                        http_status=resp.status,
                    ) from err

                if not isinstance(data, dict):
                    raise MideaApiError(
                        f"Unexpected non-object JSON from {uri}",
                        http_status=resp.status,
                    )
                return data
        except aiohttp.ClientError as err:
            raise MideaApiError(f"Network error calling {uri}: {err}") from err
        except TimeoutError as err:
            raise MideaApiError(f"Timeout calling {uri}") from err

    async def async_get_user(self) -> dict[str, Any]:
        """Get user info and created homegroup list."""
        return await self._request("POST", "/v3/open/user/get", json_body=_new_req_meta())

    async def async_get_devices(
        self, open_homegroup_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get device list, optionally filtered by homegroup ID."""
        body: dict[str, Any] = _new_req_meta()
        if open_homegroup_id is not None:
            body["openHomegroupId"] = str(open_homegroup_id)
        res = await self._request("POST", "/v3/open/device/list/get", json_body=body)
        return list(res.get("applianceList") or [])

    async def async_get_scenes(self, open_homegroup_id: str) -> list[dict[str, Any]]:
        """Get one-click scene list for a homegroup."""
        body: dict[str, Any] = _new_req_meta()
        body["openHomegroupId"] = str(open_homegroup_id)
        res = await self._request("POST", "/v3/open/scene/item/list", json_body=body)
        return list(res.get("sceneList") or [])

    async def async_execute_scene(
        self, open_homegroup_id: str, scene_id: str
    ) -> dict[str, Any]:
        """Execute a one-click scene."""
        body: dict[str, Any] = _new_req_meta()
        body["openHomegroupId"] = str(open_homegroup_id)
        body["sceneId"] = str(scene_id)
        return await self._request("POST", "/v3/open/scene/item/execute", json_body=body)

    async def async_get_thing_model_instance(self, spid: str) -> dict[str, Any] | None:
        """Fetch thing-model metadata for a product spid."""
        res = await self._request(
            "GET",
            "/v3/open/thing/doc/public/instance",
            query_params={"resType": "json", "identify": str(spid)},
        )
        result = res.get("result")
        return result if isinstance(result, dict) and result else None

    async def async_fetch_json_url(self, url: str) -> dict[str, Any]:
        """Fetch a public thing-model JSON file from Midea CDN."""
        try:
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
                data = json.loads(text)
                if not isinstance(data, dict):
                    raise MideaApiError(f"Unexpected thing-model payload at {url}")
                return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise MideaApiError(f"Failed fetching thing-model {url}: {err}") from err

    async def async_get_entire_properties(
        self, open_appliance_code: str
    ) -> dict[str, Any]:
        """Read all flat properties for a device."""
        body: dict[str, Any] = _new_req_meta()
        body["openApplianceCode"] = open_appliance_code
        res = await self._request(
            "POST", "/v3/open/thing/entire/properties", json_body=body
        )
        data = res.get("data")
        return dict(data) if isinstance(data, dict) else {}

    async def async_modify_properties(
        self, open_appliance_code: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Modify writable properties on a device."""
        body: dict[str, Any] = _new_req_meta()
        body["openApplianceCode"] = open_appliance_code
        body["properties"] = properties
        return await self._request(
            "POST", "/v3/open/thing/properties/modify", json_body=body
        )

    async def async_invoke_action(
        self,
        open_appliance_code: str,
        module_code: str,
        action_code: str,
        action: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke a thing-model action on a device."""
        body: dict[str, Any] = _new_req_meta()
        body["openApplianceCode"] = open_appliance_code
        body["moduleCode"] = module_code
        body["actionCode"] = action_code
        body["action"] = action if action is not None else {}
        return await self._request("POST", "/v3/open/thing/action", json_body=body)
