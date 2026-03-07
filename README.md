# ClaudePulse 🔵

> **Your Claude AI usage, always at a glance.**

ClaudePulse is a hardware monitor that displays your Claude.ai usage statistics in real-time on an M5Stack Basic device or on your Home Assistant instance.
It uses Home Assistant as a bridge to fetch and expose your session and weekly usage data, then renders it on the M5Stack's 320×240 display via ESPHome.

---

## Features

- 📊 **Session usage** (5-hour window) — percentage + time until reset
- 📅 **Weekly usage** (7-day window) — percentage + reset day and time
- 🔄 **Auto-refresh** every 2 minutes via Home Assistant API
- 🔘 **Button A** — manual refresh
- 🔘 **Button C** — toggle display brightness
- 🟢 **Connection indicator** — shows HA connectivity status
- 🏠 **Native HA integration** — device and sensors appear automatically in Home Assistant

---

## Architecture

```
claude.ai
    │
    ▼
Home Assistant          (Python script fetches usage via session cookie)
    │  command_line sensor
    ▼
ESPHome (Native API)    (M5Stack reads HA sensors directly — no HTTP tokens needed)
    │
    ▼
M5Stack Basic Display   (Renders usage cards, progress bars, reset timers)
```

---

## Hardware

| Component | Details |
|-----------|---------|
| [M5Stack Basic](https://shop.m5stack.com/products/esp32-basic-core-lot-development-kit) | ESP32, 320×240 ILI9341 display, 3 buttons, 4MB PSRAM |

---

## Requirements

- Home Assistant (any recent version)
- ESPHome add-on installed in HA
- Python 3 available in the HA environment
- A Claude.ai Pro account
- M5Stack Basic device

---

## Setup

### 1. Get your Claude credentials

**Session Key:**
1. Open [claude.ai](https://claude.ai) in Chrome
2. Open DevTools (`F12`) → **Application** → **Cookies** → `https://claude.ai`
3. Copy the value of `sessionKey`

**Organization ID:**
1. In DevTools → **Network** tab → filter by `Fetch/XHR`
2. Look for any request to `/api/organizations/`
3. Copy the UUID from the URL (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

---

### 2. Home Assistant — Python script

Copy `claude_usage.py` to your HA config directory:

```
/config/claude_usage.py         (if using /config mount)
/homeassistant/claude_usage.py  (if using /homeassistant mount)
```

Create the credentials file at the same path:

**`claude_config.json`**
```json
{
  "session_key": "YOUR_SESSION_KEY_HERE",
  "org_id": "YOUR_ORG_ID_HERE"
}
```

Test from the HA terminal:
```bash
python3 /config/claude_usage.py
```

Expected output:
```json
{
  "session_pct": 22.0,
  "weekly_pct": 50.0,
  "session_reset_countdown": "2h 30m",
  ...
}
```

---

### 3. Home Assistant — Package

Enable packages in `configuration.yaml` (if not already enabled):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Copy `claude_usage_package.yaml` to `/config/packages/claude_usage.yaml`.

Update the `command` path inside the file if needed:
```yaml
command: "python3 /config/claude_usage.py"
```

Restart Home Assistant. You should see `sensor.claude_usage_raw` in **Developer Tools → States** with attributes like `session_pct`, `weekly_pct`, `session_reset_countdown`, etc.

---

### 4. ESPHome — M5Stack

Copy `claude_monitor_esphome.yaml` into your ESPHome configuration.

Update the `api`, `ota` and `wifi` section with your own values:

```yaml
api:
  encryption:
    key: "YOUR_API_KEY"

ota:
  platform: esphome
  password: "YOUR_OTA_PASSWORD"

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "M5Stack Fallback Hotspot"
    password: "YOUR_AP_PASSWORD"
```

Add your WiFi credentials to ESPHome's `secrets.yaml`:
```yaml
wifi_ssid: "YourWifiNetwork"
wifi_password: "YourWifiPassword"
```

Flash the device from the ESPHome Dashboard and it will automatically appear in Home Assistant.

---

## File Reference

| File | Location | Description |
|------|----------|-------------|
| `claude_usage.py` | `/config/` | Python script that fetches usage from claude.ai |
| `claude_config.json` | `/config/` | Your Claude session key and org ID |
| `claude_usage_package.yaml` | `/config/packages/` | HA command_line sensor + template sensors |
| `claude_monitor_esphome.yaml` | ESPHome | Full ESPHome config for M5Stack |

---

## Home Assistant Sensors

Once set up, the following entities are available in HA:

| Entity | Description |
|--------|-------------|
| `sensor.claude_usage_raw` | Raw sensor with all data as attributes |
| `sensor.claude_session_usage_pct` | Session usage percentage |
| `sensor.claude_weekly_usage_pct` | Weekly usage percentage |
| `sensor.claude_session_reset` | Time until session resets |
| `sensor.claude_weekly_reset` | Day and time of weekly reset |

![Home Assistant Sensors](![Home Assistant card](ha-card.png))

---

## Troubleshooting

**Display shows nothing / `Could not allocate buffer for display!`**
Add PSRAM support to the ESPHome config:
```yaml
psram:
  mode: quad
  speed: 80MHz
```

**`command_line` sensor fails with exit code 2**
The script path in the package YAML doesn't match where the file is located. Check which path HA uses:
```bash
ls /config/claude_usage.py
ls /homeassistant/claude_usage.py
```
Update the `command` in `claude_usage_package.yaml` accordingly.

**All endpoints return 404**
Your `org_id` in `claude_config.json` is incorrect. Verify it using Chrome DevTools → Network → look for requests to `/api/organizations/`.

**Session data shows 0% for everything**
The `sessionKey` cookie may have expired. Re-extract it from Chrome DevTools → Application → Cookies → `claude.ai`.

**M5Stack shows "Connecting to Home Assistant..."**
The ESPHome device is not yet paired with HA. Go to **Settings → Devices & Services** in HA and accept the new ESPHome device integration.

---

## License

MIT — do whatever you want with it.

---

*ClaudePulse is an unofficial project and is not affiliated with Anthropic.*
