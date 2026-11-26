"""Constants for the Midea Cloud V3 integration."""

from homeassistant.const import Platform

DOMAIN = "midea_cloud_v3"

API_BASE_URL = "https://api-prod.smartmidea.net"
OAUTH2_AUTHORIZE_URL = f"{API_BASE_URL}/v3/open/oauth2/authorize"
OAUTH2_TOKEN_URL = f"{API_BASE_URL}/v3/open/oauth2/token"
SIGNATURE_VERSION = "2.0"

CONF_HOMEGROUP_IDS = "homegroup_ids"
CONF_INCLUDE_OFFLINE = "include_offline"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

PLATFORMS: list[Platform] = [
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SCENE,
]
