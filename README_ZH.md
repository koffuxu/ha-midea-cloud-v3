# Midea Cloud V3（美的开放平台 V3 Home Assistant 集成）

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English README](README.md)

基于**美的 IoT 开发者平台官方 Cloud-to-Cloud V3 接口**（`https://api-prod.smartmidea.net`）与**动态物模型（`midea-iot-spec-v1`）**实现的 Home Assistant 自定义集成，支持 HACS 安装。

## 核心特性

- **官方 V3 云云对接协议**：完整实现 OAuth 2.0 授权码登录、HMAC-SHA256（`SignatureVersion: 2.0`）签名及单次轮换 `refresh_token` 自动续期与持久化。
- **零外部 PyPI 依赖**：仅使用 Home Assistant 内置 `aiohttp` 与 `application_credentials`。
- **动态物模型解析**：自动按设备 `spid` 拉取美的物模型定义并映射为标准 HA 实体：
  - **窗帘 (`cover`)**：电动开合帘（打开、关闭、暂停、开合百分比定位）。
  - **灯光 (`light`)**：智能灯具（开关、亮度 1~100%、色温开尔文）。
  - **开关 (`switch`)**：单键/多键墙壁开关、带屏开关、网关状态灯、智慧屏麦克风开关。
  - **空调 (`climate`)**：空调模式、目标温度、当前室温、风速。
  - **传感器 (`sensor` / `binary_sensor`)**：温度、湿度、TVOC、PM2.5、CO2、光照度、人体存在检测。
  - **数值/选择/按键 (`number` / `select` / `button`)**：智慧屏音量、屏幕显示模式、窗帘电机转速、语音唤醒等。
  - **一键场景 (`scene`)**：同步美的美居家庭中已启用的一键场景。

## 前置准备：美的 IoT 开发者平台配置要点

1. 登录 [美的 IoT 开发者平台](https://iot.midea.com/) 并完成企业开发者认证。
2. 进入 **应用服务 → 创建新应用 → 云控端**：
   - **应用授权类型**：务必选择 **「用户级别授权」**（不要选「应用级别授权」，应用级别 `client_credentials` 无法读取美居家庭和设备列表）。
   - **Redirect Url（回调地址）**：填写 `https://my.home-assistant.io/redirect/oauth`（注意中间是英文减号 `-`）。
   - **启用服务配置（消息订阅）**：如无公网 HTTPS 回调服务，取消勾选即可。
3. 审核通过后记录应用详情中的 **Client ID** 与 **Client Secret**。

## 安装方式

### 方式一：HACS 自定义仓库（推荐）
1. 在 Home Assistant 中打开 **HACS → 集成 → 右上角 ⋮ → 自定义存储库**。
2. 添加仓库地址 `https://github.com/koffuxu/ha-midea-cloud-v3`，类别选择 **Integration（集成）**。
3. 搜索并安装 **Midea Cloud V3**，重启 Home Assistant。

### 方式二：手动安装
1. 将本仓库中的 `custom_components/midea_cloud_v3` 目录复制到 HA 配置目录 `<config>/custom_components/midea_cloud_v3`。
2. 重启 Home Assistant。

## 添加与配置

1. 打开 **设置 → 设备与服务 → 添加集成 → 搜索 `Midea Cloud V3`**。
2. 按提示在应用凭据中填入美的开放平台的 **Client ID** 和 **Client Secret**。
3. 跳转到美居授权页面后，使用绑定了智能设备的美居 App 账号登录并同意授权。
4. 回调返回 Home Assistant 后，勾选需要接入的美居家庭、是否包含离线设备及轮询间隔（默认 30 秒）即可完成。
