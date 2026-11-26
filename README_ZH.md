# Midea Cloud V3（美的开放平台 V3 Home Assistant 集成）

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English README](README.md)

基于**美的 IoT 开发者平台官方 Cloud-to-Cloud V3 接口**（`https://api-prod.smartmidea.net`）与**动态物模型（`midea-iot-spec-v1`）**实现的 Home Assistant 自定义集成，支持 HACS 安装。

## 核心特性

- **官方 V3 云云对接协议**：完整实现 OAuth 2.0 授权码登录、HMAC-SHA256（`SignatureVersion: 2.0`）请求签名，以及单次轮换 `refresh_token` 的自动续期与持久化。
- **零外部 PyPI 依赖**：仅依赖 Home Assistant 内置的 `aiohttp` 与 `application_credentials`，开箱即用。
- **动态物模型解析**：自动按设备 `spid` 从美的云拉取物模型规范并动态映射为原生 HA 实体，无需针对单个型号硬编码。
- **支持局域网部署**：借助 `https://my.home-assistant.io/redirect/oauth` 完成一次性浏览器 OAuth 回调，Home Assistant 本身**不需要暴露到公网**。
- **已实测兼容**：已在 Home Assistant `2026.11.2`（Python `3.14`）及 `2024.12+` 环境下完成实机验证。

---

## 第一步：在美的 IoT 开发者平台获取 Client ID 与 Client Secret

> [!IMPORTANT]
> 本集成依赖美的官方开放平台凭据。你需要先注册并认证为企业开发者，再创建**「云控端」**应用。

1. **注册并完成企业用户认证**
   - 打开美的 IoT 开发者平台：<https://iot.midea.com/>
   - 注册开发者账号并进入控制台完成 **企业用户认证**（审核通过后才可创建应用并调用开放接口）。
2. **创建「云控端」应用**
   - 进入控制台 **「应用服务」→「创建新应用」**。
   - 应用类型选择 **「云控端」**（用于第三方系统控制美的云端设备；**不要选**面向硬件厂商的「云设备」或「创建产品」）。
3. **填写基础信息（最关键的两项）**
   - **应用授权类型**：务必选择 **「用户级别授权」**（OAuth 2.0 授权码模式）。
     > [!WARNING]
     > **请勿选择「应用级别授权」**：`应用级别授权` 走的是 `client_credentials` 模式，既没有回调地址，也不会关联具体的美居用户账号，调用设备列表接口会直接报错 `1006 userid value is illegal`。只有 **「用户级别授权」** 才能读取并控制你美居 App 账号下的家庭与设备。
   - **Redirect Url（回调地址）**：填写：
     ```text
     https://my.home-assistant.io/redirect/oauth
     ```
     > [!CAUTION]
     > 请直接复制上面的地址，确保 `home-assistant` 中间是**英文减号 `-`**，切勿误输入中文长横杠 `–`（否则 OAuth 跳转会失败或报参数错误）。该地址仅在首次授权时由你的浏览器本地转发一次 `code`，日常设备控制不经过它。
4. **更多配置（服务订阅与 A2A）**
   - **启用服务配置（订阅设备信息）**：**取消勾选**。消息订阅需要自建公网 HTTPS Webhook 服务，本集成采用云端轮询机制，无需配置公网回调。
   - **A2A 服务能力配置**：按需勾选或取消即可，不影响本集成的 V3 接口调用。
5. **等待审核并获取凭据**
   - 提交后等待平台审核通过（通常较快）。
   - 审核通过后，在应用详情页即可看到 **`Client ID`** 和 **`Client Secret`**，妥善保存备用。

---

## 第二步：数据流与授权机制说明

1. **首次绑定（仅需一次）**：你在浏览器登录美居 App 账号并同意授权 → 美的云重定向至 `https://my.home-assistant.io/redirect/oauth?code=...` → 浏览器将一次性 `code` 转交局域网内的 Home Assistant → HA 用 `code` + `Client ID` + `Client Secret` 换取 `access_token`（有效期 24 小时）与 `refresh_token`（有效期 30 天）。
2. **日常控制与自动续期**：Home Assistant **直接**与 `https://api-prod.smartmidea.net` 通信进行轮询与控制，不再经过 `my.home-assistant.io`。`access_token` 到期前 HA 会自动使用 `refresh_token` 换取新令牌并持久化保存新的轮换 `refresh_token`（只要 HA 不是连续离线超过 30 天，即可长期免密运行）。

---

## 第三步：安装集成

### 方式一：HACS 自定义仓库（推荐）
1. 在 Home Assistant 中打开 **HACS → 集成 → 右上角 `⋮` → 自定义存储库**。
2. 仓库地址填写你的 GitHub 仓库 URL（例如 `https://github.com/koffuxu/ha-midea-cloud-v3`），类别选择 **Integration（集成）**。
3. 搜索并下载 **Midea Cloud V3**，然后 **重启 Home Assistant**。

### 方式二：手动安装
1. 将本仓库中的 `custom_components/midea_cloud_v3` 目录完整复制到 Home Assistant 配置目录下：
   `<config>/custom_components/midea_cloud_v3`
2. **重启 Home Assistant**。

---

## 第四步：在 Home Assistant 中添加与配置

1. 打开 Home Assistant 网页端，进入 **设置 → 设备与服务 → 右下角「添加集成」**，搜索 **`Midea Cloud V3`**。
2. 按提示在「应用凭据」弹窗中填入第一步获取的 **`Client ID`** 和 **`Client Secret`**（如需修改已保存的凭据，可在 **设置 → 设备与服务 → 右上角 `⋮` → 应用凭据** 中管理）。
3. 浏览器会自动跳转到美的美居登录授权页，使用**绑定了智能设备的美居 App 账号**登录并同意授权。
4. 授权完成后跳转到 `my.home-assistant.io`，确认页面上的 Home Assistant 实例地址正确后点击 **Open Link** 返回 HA。
5. 在配置表单中选择：
   - **美居家庭**：勾选需要接入的家庭（支持多家庭）；
   - **包含当前离线设备**：建议开启，避免设备暂时断电时实体被移除；
   - **轮询间隔（秒）**：默认 `30` 秒（范围 `10 ~ 300` 秒）。
6. 后续可在集成卡片点击 **「配置」** 随时调整家庭范围、离线设备开关和轮询间隔；若超过 30 天未刷新导致授权过期，HA 会自动弹出 **「重新配置（Reauth）」** 引导重新登录。

---

## 支持的设备与物模型映射

| HA 平台 | 美的物模型模块 / 属性 | 支持能力 |
|---|---|---|
| `cover` | `electricCurtain` | 电动开合帘：打开、关闭、暂停、百分比开合度 |
| `light` | `light` | 智能灯具：开关、亮度（1~100%）、色温（开尔文） |
| `switch` | `wallSwitch` / `wallSwitch1..N` / `screenSwitch` / `connectedStateLight` / `microphone` | 单/多键墙壁开关、带屏开关、网关状态灯、智慧屏麦克风 |
| `climate` | `airConditioner` / `ac` | 空调：开关、HVAC 模式、目标温度、室温、风速 |
| `sensor` | `temperatureHumiditySensor` / `airQuality` / `humanPresenceSensor` | 温度、湿度、TVOC、PM2.5、CO2、光照度 |
| `binary_sensor` | `humanPresenceSensor.humanPresenceState` | 人体存在检测（Occupancy） |
| `number` | `speaker.mediaVolume` / `speaker.systemVolume` | 智慧屏媒体音量、系统音量 |
| `select` | `screenDisplay.screenDisplaySwitch` / `electricCurtain.motorSpeed` | 屏幕显示模式、窗帘电机转速 |
| `button` | `aiVoice.aiWakeUp` / `light.deviceIdentify` | 语音唤醒、灯具识别 |
| `scene` | 美居一键场景 | 同步并触发美居家庭中已启用的一键场景 |

---

## 常见问题排查（FAQ）

1. **提示 `1006 userid value is illegal` 或拉不到任何设备**
   - 原因：美的开放平台应用选成了 **「应用级别授权」**。
   - 解决：到美的控制台将应用授权类型改为 **「用户级别授权」**（并配置好 `Redirect Url`），等待审核通过后重新走一次 OAuth 授权。
2. **跳转美的授权页直接显示「哎呀！系统出错啦」**
   - 原因：传入的 `redirect_uri` 与美的控制台填写的不完全一致（常见坑：混入了中文长横杠 `–`、末尾多了斜杠 `/` 或协议 `http`/`https` 不匹配）。
   - 解决：核对控制台的 `Redirect Url` 为精确的 `https://my.home-assistant.io/redirect/oauth`。
3. **部分设备显示「不可用（Unavailable）」或日志出现 `41102`**
   - 原因：设备在美居 App 中处于离线状态（断电或未联网），V3 接口返回 `41102`。设备重新上线后下个轮询周期会自动恢复。
4. **如何更换 Client ID / Client Secret？**
   - 进入 Home Assistant **设置 → 设备与服务 → 右上角 `⋮` → 应用凭据**，删除旧的 `Midea Cloud V3` 凭据后重新添加即可。
