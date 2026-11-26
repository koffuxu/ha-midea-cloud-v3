"""Tests for Midea V3 HMAC-SHA256 signature helper."""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import pathlib
import unittest

API_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components"
    / "midea_cloud_v3"
    / "api.py"
)
SPEC = importlib.util.spec_from_file_location("midea_api", API_PATH)
assert SPEC and SPEC.loader
midea_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(midea_api)


class TestSigning(unittest.TestCase):
    """Verify HMAC-SHA256 signing matches Midea Cloud V3 specification."""

    def test_post_signature_with_utf8_chinese_body(self) -> None:
        secret = "test_secret_123"
        method = "POST"
        uri = "/v3/open/thing/properties/modify"
        body = '{"reqId":"abc123","properties":{"name":"客厅空调"}}'
        expected = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                f"{method}{uri}{body}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        actual = midea_api.build_signature(secret, method, uri, "", body)
        self.assertEqual(actual, expected)

    def test_get_signature_with_query_string(self) -> None:
        secret = "test_secret_123"
        method = "GET"
        uri = "/v3/open/thing/doc/public/instance"
        qs = "resType=json&identify=10004744"
        expected = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                f"{method}{uri}{qs}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        actual = midea_api.build_signature(secret, method, uri, qs, "")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
