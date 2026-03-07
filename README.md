# Claude Pulse

> **Monitor your Claude.ai usage directly in Home Assistant.**

Claude Pulse is a HACS custom integration that exposes your Claude.ai session and weekly usage as Home Assistant sensors, updated automatically every 2 minutes.

![Home Assistant card](ha-card.png)

---

## Features

- **Session usage** (5-hour window) — percentage and time until reset
- **Weekly usage** (7-day window) — percentage and weekly reset day/time
- **Auto-refresh** every 2 minutes (configurable)
- **Re-authentication flow** — HA notifies you when your session key expires
- **10 sensors** — all data exposed as individual HA entities

---

## Installation via HACS

1. Open HACS in your Home Assistant sidebar
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/nikolmedo/ClaudePulse` with category **Integration**
4. Click **Download** on Claude Pulse and confirm
5. **Restart Home Assistant**
6. Go to **Settings → Devices & Services → Add Integration** and search for **Claude Pulse**
7. Enter your Session Key and Organization ID (see below)

---

## Getting your credentials

### Session Key

1. Open [claude.ai](https://claude.ai) in Chrome and log in
2. Open DevTools (`F12`) → **Application** → **Cookies** → `https://claude.ai`
3. Copy the value of the `sessionKey` cookie

### Organization ID

1. In DevTools, open the **Network** tab and reload the page
2. Find any request URL containing `/api/organizations/`
3. Copy the UUID from the URL (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

---

## Available Sensors

Once set up, the following entities appear in Home Assistant under a single **Claude Pulse** device:

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.claudepulse_session_usage` | Session usage (5h window) | % |
| `sensor.claudepulse_weekly_usage` | Weekly usage (7d window) | % |
| `sensor.claudepulse_session_reset_countdown` | Time until session resets (e.g. `2h 30m`) | — |
| `sensor.claudepulse_session_reset_time` | Clock time of session reset | — |
| `sensor.claudepulse_weekly_reset` | Weekly reset summary (e.g. `Friday @ 03:45 AM`) | — |
| `sensor.claudepulse_weekly_reset_weekday` | Day of the week of weekly reset | — |
| `sensor.claudepulse_weekly_reset_time` | Clock time of weekly reset | — |
| `sensor.claudepulse_session_used` | Session used (same as session usage) | % |
| `sensor.claudepulse_session_limit` | Session limit (always 100) | % |
| `sensor.claudepulse_plan` | Subscription plan | — |

> Note: exact entity IDs depend on the device name HA assigns. Find them in **Developer Tools → States** and filter by `claude_pulse`.

---

## Troubleshooting

**Authentication failed (HTTP 401/403)**
Your `sessionKey` cookie has expired. Go to **Settings → Devices & Services → Claude Pulse → Configure** to enter a new session key.

**All endpoints return 404**
Your Organization ID is incorrect. Verify it using Chrome DevTools → Network → look for requests to `/api/organizations/`.

**Sensors show `unavailable` after setup**
Check **Settings → System → Logs** for errors from the `claude_pulse` integration. A network error at startup causes HA to retry automatically.

**HA shows a repair notification for Claude Pulse**
Your session key expired. Click the notification to open the re-authentication form and enter a new key.

---

## Legacy / Manual Setup

If you prefer not to use HACS, you can still use the standalone files:

| File | Location | Description |
|------|----------|-------------|
| `claude_usage.py` | `/config/` | Python script that fetches usage from claude.ai |
| `claude_usage.yaml` | `/config/packages/` | HA command_line sensor + template sensors |

See the git history for setup instructions for the manual approach.

---

## License

MIT — do whatever you want with it.

---

*Claude Pulse is an unofficial project and is not affiliated with Anthropic.*
