"""Tests for MideaCloudV3Client async calls and error mapping."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from typing import Any

API_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components"
    / "midea_cloud_v3"
    / "api.py"
)
SPEC = importlib.util.spec_from_file_location("midea_api_client", API_PATH)
assert SPEC and SPEC.loader
midea_api = importlib.util.module_from_spec(SPEC)
sys.modules["midea_api_client"] = midea_api
SPEC.loader.exec_module(midea_api)


class _FakeResponse:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self._text = text

    async def text(self) -> str:
        return self._text

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self._responses.pop(0)


class TestMideaCloudV3Client(unittest.IsolatedAsyncioTestCase):
    """Verify request headers, endpoints, and error classification."""

    async def test_get_user_and_auth_error(self) -> None:
        session = _FakeSession(
            [
                _FakeResponse(200, '{"openUid":"u1","userName":"demo","homegroupList":[]}'),
                _FakeResponse(409, '{"error":"1006","error_description":"invalid token"}'),
                _FakeResponse(409, '{"error":"41102","error_description":"device offline"}'),
            ]
        )

        async def _tok() -> str:
            return "tok123"

        client = midea_api.MideaCloudV3Client(session, "cid", "csec", _tok)
        user = await client.async_get_user()
        self.assertEqual(user["openUid"], "u1")
        self.assertEqual(session.calls[0]["headers"]["SignatureVersion"], "2.0")

        with self.assertRaises(midea_api.MideaAuthError):
            await client.async_get_user()

        with self.assertRaises(midea_api.MideaDeviceOfflineError):
            await client.async_get_entire_properties("dev1")


if __name__ == "__main__":
    unittest.main()
