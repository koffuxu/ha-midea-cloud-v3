# Midea Cloud V3 for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文文档](README_ZH.md)

A Home Assistant custom integration built on the official **Midea IoT Developer Platform Cloud-to-Cloud V3 API** (`https://api-prod.smartmidea.net`) and dynamic **Midea Thing-Model (`midea-iot-spec-v1`)** discovery.

## Features

- **Official Cloud-to-Cloud V3 API**: Uses Midea's official OAuth 2.0 Authorization Code flow and HMAC-SHA256 v2.0 request signing, with automatic token refresh & rotational `refresh_token` persistence via Home Assistant's `application_credentials`.
- **Zero External Dependencies**: Uses Home Assistant's built-in `aiohttp` only.
- **Dynamic Thing-Model Discovery**: Automatically fetches each product's `spid` Thing-Model specification and maps capabilities into native Home Assistant entities:
  - **Cover (`cover`)**: Electric curtains (`electricCurtain` — open, close, stop, target opening percentage).
  - **Light (`light`)**: Smart lights (`light` — on/off, brightness, Kelvin color temperature).
  - **Switch (`switch`)**: Wall switches (`wallSwitch`, multi-gang `wallSwitch1..N`), screen switches (`screenSwitch`), gateway status light (`connectedStateLight`), microphone toggle (`microphone`).
  - **Climate (`climate`)**: Air conditioners (`airConditioner` / `ac` — HVAC modes, target temperature, fan speed).
  - **Sensor (`sensor`) & Binary Sensor (`binary_sensor`)**: Temperature, humidity, TVOC, PM2.5, CO2, illuminance, human presence occupancy.
  - **Number (`number`), Select (`select`), Button (`button`)**: Speaker volume, screen display mode, curtain motor speed, voice wake-up / light identify actions.
  - **Scene (`scene`)**: Midea Meiju one-click smart scenes.

## Prerequisites on Midea IoT Developer Platform

1. Register and complete enterprise verification on [Midea IoT Developer Platform](https://iot.midea.com/).
2. Create a **Cloud Control (`云控端`)** application:
   - **Authorization Type (`应用授权类型`)**: Select **User-level Authorization (`用户级别授权`)** (OAuth 2.0 Authorization Code). *Note: Application-level (`client_credentials`) cannot access Meiju user homes/devices.*
   - **Redirect URL**: `https://my.home-assistant.io/redirect/oauth` (make sure the hyphen is ASCII `-`).
   - **Service Subscription (`启用服务配置`)**: Leave unchecked unless you expose a public HTTPS webhook.
3. Note your **Client ID** and **Client Secret** after approval.

## Installation

### Option 1: HACS (Custom Repository)
1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/koffuxu/ha-midea-cloud-v3` with category **Integration**.
3. Install **Midea Cloud V3** and restart Home Assistant.

### Option 2: Manual
1. Copy `custom_components/midea_cloud_v3` into `<ha_config>/custom_components/midea_cloud_v3`.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Midea Cloud V3**.
2. Enter your Midea **Client ID** and **Client Secret** when prompted by Application Credentials.
3. Log in with your Midea Meiju (`美的美居`) account on the OAuth2 page and approve access.
4. Select the Midea homes to import, whether to include offline devices, and your polling interval (default `30s`).
