"""DataUpdateCoordinator for ClaudePulse — fetches Claude.ai usage data."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CLAUDE_BASE_URL,
    CLAUDE_HEADERS,
    CONF_ORG_ID,
    CONF_SESSION_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ENDPOINT_ACCOUNT_USAGE,
    ENDPOINT_ORG_USAGE,
    ENDPOINT_USAGE,
)

_LOGGER = logging.getLogger(__name__)


class ClaudePulseCoordinator(DataUpdateCoordinator):
    """Fetches Claude usage data from claude.ai on a configurable interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._session_key: str = entry.data[CONF_SESSION_KEY]
        self._org_id: str = entry.data.get(CONF_ORG_ID, "")
        interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_endpoints(self) -> list[str]:
        endpoints: list[str] = []
        if self._org_id:
            endpoints.append(
                CLAUDE_BASE_URL + ENDPOINT_ORG_USAGE.format(org_id=self._org_id)
            )
        endpoints.append(CLAUDE_BASE_URL + ENDPOINT_USAGE)
        endpoints.append(CLAUDE_BASE_URL + ENDPOINT_ACCOUNT_USAGE)
        return endpoints

    def _build_headers(self) -> dict:
        return {**CLAUDE_HEADERS, "Cookie": f"sessionKey={self._session_key}"}

    @staticmethod
    def _parse_timestamp(ts) -> dict:
        """Parse an ISO or epoch timestamp into display-friendly strings.

        Mirrors the fmt() function from the legacy claude_usage.py script.
        """
        fallback = {"date": "N/A", "time": "N/A", "weekday": "N/A", "countdown": "N/A"}
        if not ts:
            return fallback
        try:
            if isinstance(ts, (int, float)):
                if ts > 1e10:
                    ts /= 1000
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            remaining = max(0.0, (dt - now).total_seconds())
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            loc = dt.astimezone()
            return {
                "date":      loc.strftime("%b %d"),
                "time":      loc.strftime("%I:%M %p"),
                "weekday":   loc.strftime("%A"),
                "countdown": f"{h}h {m}m" if h else f"{m}m",
            }
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to parse timestamp: %s", ts)
            return fallback

    # ------------------------------------------------------------------
    # DataUpdateCoordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        """Fetch latest usage data from claude.ai.

        Raises:
            ConfigEntryAuthFailed: On HTTP 401/403 — triggers HA reauth flow.
            UpdateFailed: On all other errors.
        """
        session = async_get_clientsession(self.hass)
        headers = self._build_headers()
        endpoints = self._build_endpoints()
        raw = None
        last_error = ""

        for url in endpoints:
            try:
                async with session.get(url, headers=headers, timeout=12) as resp:
                    if resp.status in (401, 403):
                        raise ConfigEntryAuthFailed(
                            f"Claude.ai authentication failed (HTTP {resp.status}). "
                            "Please update your session key."
                        )
                    if resp.status == 200:
                        raw = await resp.json(content_type=None)
                        break
                    last_error = f"HTTP {resp.status} from {url}"
            except ConfigEntryAuthFailed:
                raise
            except Exception as err:  # noqa: BLE001
                last_error = str(err)
                _LOGGER.debug("Endpoint %s failed: %s", url, err)

        if raw is None:
            raise UpdateFailed(
                f"All Claude.ai endpoints failed. Last error: {last_error}"
            )

        # API response shape: {"five_hour": {"utilization": 22, "resets_at": "..."}, "seven_day": {...}}
        sess = raw.get("five_hour") or {}
        week = raw.get("seven_day") or {}

        sess_pct = float(sess.get("utilization") or 0)
        week_pct = float(week.get("utilization") or 0)

        sr = self._parse_timestamp(sess.get("resets_at"))
        wr = self._parse_timestamp(week.get("resets_at"))

        return {
            "session_pct":             sess_pct,
            "session_used":            sess_pct,
            "session_limit":           100.0,
            "session_reset_time":      sr["time"],
            "session_reset_countdown": sr["countdown"],
            "weekly_pct":              week_pct,
            "weekly_reset_date":       wr["date"],
            "weekly_reset_time":       wr["time"],
            "weekly_reset_weekday":    wr["weekday"],
            "weekly_reset":            (
                f"{wr['weekday']} @ {wr['time']}" if wr["weekday"] != "N/A" else "N/A"
            ),
            "plan":       "Pro",
            "fetched_at": datetime.now().strftime("%H:%M"),
        }
