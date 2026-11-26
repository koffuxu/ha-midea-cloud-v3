# Midea Cloud V3 for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文文档](README_ZH.md)

A Home Assistant custom integration built on the official **Midea IoT Developer Platform Cloud-to-Cloud V3 API** (`https://api-prod.smartmidea.net`) and dynamic **Midea Thing-Model (`midea-iot-spec-v1`)** discovery.

## Features

- **Official Cloud-to-Cloud V3 API**: Implements Midea's OAuth 2.0 Authorization Code flow, HMAC-SHA256 (`SignatureVersion: 2.0`) request signing, and automatic token refresh with rotational `refresh_token` persistence via Home Assistant `application_credentials`.
- **Zero External PyPI Dependencies**: Uses Home Assistant's built-in `aiohttp` only.
- **Dynamic Thing-Model Discovery**: Automatically fetches each product's `spid` Thing-Model JSON and maps properties/actions to native Home Assistant entities without hardcoding individual device models.
- **LAN-Friendly OAuth**: Uses `https://my.home-assistant.io/redirect/oauth` for the one-time browser redirect — your Home Assistant instance does **not** need to be exposed to the public internet.
- **Tested On**: Home Assistant `2026.11.2` (Python `3.14`) and compatible with `2024.12+`.

---

## Step 1: Obtain Client ID and Client Secret on Midea IoT Developer Platform

> [!IMPORTANT]
> You need a verified enterprise developer account on the Midea IoT Developer Platform and a **Cloud Control (`云控端`)** application.

1. **Register & Complete Enterprise Verification**
   - Visit the Midea IoT Developer Platform: <https://iot.midea.com/>
   - Create an account and complete **Enterprise User Verification (`企业用户认证`)**.
2. **Create a Cloud Control (`云控端`) Application**
   - Go to **Application Services (`应用服务`) → Create Application (`创建新应用`)**.
   - Select **Cloud Control (`云控端`)** as the application type (do **not** choose `云设备` / hardware product creation).
3. **Configure Authorization & Redirect URL (Critical)**
   - **Authorization Type (`应用授权类型`)**: Select **User-level Authorization (`用户级别授权`)** (OAuth 2.0 Authorization Code flow).
     > [!WARNING]
     > **Do NOT select Application-level Authorization (`应用级别授权`)**: Application-level `client_credentials` tokens do not bind to a Midea Meiju user and will fail `/v3/open/device/list/get` with `1006 userid value is illegal`. You must use **User-level Authorization (`用户级别授权`)** to access and control devices under your Meiju account.
   - **Redirect Url**: Enter:
     ```text
     https://my.home-assistant.io/redirect/oauth
     ```
     > [!CAUTION]
     > Make sure the hyphen in `home-assistant` is an ASCII hyphen `-` (not an en-dash `–`). This URL is only used once during initial OAuth login to hand the authorization `code` back to your local Home Assistant.
4. **Additional Settings**
   - **Service Subscription (`启用服务配置`)**: Leave **unchecked** (webhooks require a public HTTPS endpoint; this integration uses cloud polling).
   - **A2A Service (`启用A2A服务能力`)**: Optional; does not affect V3 API calls.
5. **Wait for Approval & Copy Credentials**
   - Once approved, copy your **`Client ID`** and **`Client Secret`** from the application details page.

---

## Step 2: Data Flow & Token Lifecycle

1. **One-time Binding**: You log in with your Midea Meiju (`美的美居`) account in your browser → Midea redirects to `https://my.home-assistant.io/redirect/oauth?code=...` → Your browser forwards the one-time `code` to your LAN Home Assistant → HA exchanges `code` + `Client ID` + `Client Secret` for an `access_token` (24h TTL) and `refresh_token` (30-day TTL).
2. **Daily Operation**: Home Assistant communicates **directly** with `https://api-prod.smartmidea.net` for polling and device control. Before `access_token` expires, HA automatically refreshes it and persists the rotated `refresh_token` (as long as HA is not offline for >30 consecutive days, no re-login is needed).

---

## Step 3: Installation

### Option 1: HACS (Custom Repository)
1. In Home Assistant, go to **HACS → Integrations → `⋮` → Custom repositories**.
2. Add your repository URL (e.g. `https://github.com/koffuxu/ha-midea-cloud-v3`) with category **Integration**.
3. Install **Midea Cloud V3** and **restart Home Assistant**.

### Option 2: Manual
1. Copy `custom_components/midea_cloud_v3` into `<ha_config>/custom_components/midea_cloud_v3`.
2. **Restart Home Assistant**.

---

## Step 4: Configure in Home Assistant

1. Go to **Settings → Devices & Services → Add Integration → search `Midea Cloud V3`**.
2. Enter your **`Client ID`** and **`Client Secret`** when prompted by Application Credentials.
3. Log in with your Midea Meiju (`美的美居`) account on the OAuth2 page and approve access.
4. On `my.home-assistant.io`, verify your Home Assistant instance URL and click **Open Link**.
5. Choose which Midea **Homes** to import, whether to **Include offline devices**, and your **Polling interval** (default `30s`, range `10–300s`).
6. You can adjust these options anytime via **Configure** on the integration card. If a token expires after >30 days offline, HA will prompt a **Re-authenticate** flow automatically.

---

## Supported Platforms & Thing-Model Mapping

| HA Platform | Midea Thing-Model Module / Property | Capabilities |
|---|---|---|
| `cover` | `electricCurtain` | Electric curtains: open, close, stop, target opening percentage |
| `light` | `light` | Smart lights: on/off, brightness (1–100%), Kelvin color temperature |
| `switch` | `wallSwitch` / `wallSwitch1..N` / `screenSwitch` / `connectedStateLight` / `microphone` | 1/multi-gang wall switches, screen switch, gateway status light, microphone toggle |
| `climate` | `airConditioner` / `ac` | Air conditioners: power, HVAC mode, target & indoor temperature, fan speed |
| `sensor` | `temperatureHumiditySensor` / `airQuality` / `humanPresenceSensor` | Temperature, humidity, TVOC, PM2.5, CO2, illuminance |
| `binary_sensor` | `humanPresenceSensor.humanPresenceState` | Human presence occupancy |
| `number` | `speaker.mediaVolume` / `speaker.systemVolume` | Media & system volume |
| `select` | `screenDisplay.screenDisplaySwitch` / `electricCurtain.motorSpeed` | Screen display mode, curtain motor speed |
| `button` | `aiVoice.aiWakeUp` / `light.deviceIdentify` | Voice wake-up, light identify |
| `scene` | Midea one-click scenes | Activate enabled Meiju one-click scenes |

---

## Troubleshooting

- **`1006 userid value is illegal` / No devices found**: Your Midea app was created with **Application-level Authorization (`应用级别授权`)**. Switch it to **User-level Authorization (`用户级别授权`)** in the Midea console and re-authorize.
- **Midea login page shows "系统出错啦"**: The `redirect_uri` in Midea console does not match `https://my.home-assistant.io/redirect/oauth` byte-for-byte (watch out for en-dashes `–` or trailing slashes).
- **Entities show `Unavailable` / `41102`**: The device is offline in the Midea Meiju app. It will recover automatically on the next poll once online.
- **Updating Client ID / Client Secret**: Go to **Settings → Devices & Services → `⋮` → Application Credentials**, remove the old `Midea Cloud V3` credential, and re-add the integration.
