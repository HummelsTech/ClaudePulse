"""Domain models for Claude Pulse.

Pure Python — no Home Assistant imports. Everything in this module is
unit-testable without the HA test harness.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

NOT_AVAILABLE = "N/A"

# Model display name (case-insensitive) used to locate the Fable weekly quota
# inside the API's ``limits[]`` array.
FABLE_MODEL_NAME = "fable"

# Flat top-level keys some accounts still expose for the Fable weekly quota,
# tried in order after the ``limits[]`` array. See ``extract_fable``.
FABLE_FLAT_KEYS = ("seven_day_fable", "fable_weekly", "fable_seven_day", "fable")

# Locale tables for the display strings baked into sensor states (weekday
# names, reset times, countdowns). Keys are two-letter language codes as
# reported by ``hass.config.language``; anything unknown falls back to "en".
LOCALES = {
    "en": {
        "weekdays": (
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ),
        "months": (
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ),
        "clock_24h": False,
        "hour_unit": "h",
        "minute_unit": "m",
        "date_day_first": False,
    },
    "nl": {
        "weekdays": (
            "maandag", "dinsdag", "woensdag", "donderdag",
            "vrijdag", "zaterdag", "zondag",
        ),
        "months": (
            "jan", "feb", "mrt", "apr", "mei", "jun",
            "jul", "aug", "sep", "okt", "nov", "dec",
        ),
        "clock_24h": True,
        "hour_unit": "u",
        "minute_unit": "m",
        "date_day_first": True,
    },
}


def _locale(language: str | None) -> dict:
    """Resolve a language code ("nl", "en-GB", ...) to a locale table."""
    if not isinstance(language, str):
        return LOCALES["en"]
    return LOCALES.get(language.split("-")[0].lower(), LOCALES["en"])


# Known ``rate_limit_tier`` values from the organization payload, mapped to
# display names. Unknown tiers are prettified instead of dropped — see
# ``detect_plan``.
PLAN_TIERS = {
    "default_claude_ai": "Free",
    "default_free": "Free",
    "default_claude_pro": "Pro",
    "default_pro": "Pro",
    "default_claude_max_5x": "Max 5x",
    "default_claude_max_20x": "Max 20x",
    "default_raven": "Team",
}

# ``capabilities[]`` fallbacks for org payloads without a usable
# ``rate_limit_tier``, probed in order (most-specific first).
PLAN_CAPABILITIES = (
    ("claude_max", "Max"),
    ("claude_pro", "Pro"),
    ("raven", "Team"),
    ("chat", "Free"),
)


@dataclass(frozen=True)
class ResetInfo:
    """Display-friendly representation of a usage-window reset timestamp."""

    date: str = NOT_AVAILABLE
    time: str = NOT_AVAILABLE
    weekday: str = NOT_AVAILABLE
    countdown: str = NOT_AVAILABLE

    @property
    def is_known(self) -> bool:
        """Whether the reset timestamp could be parsed."""
        return self.weekday != NOT_AVAILABLE


def parse_reset_timestamp(
    ts, now: datetime | None = None, language: str = "en"
) -> ResetInfo:
    """Parse an ISO or epoch timestamp into a ResetInfo.

    Accepts ISO-8601 strings (with or without trailing ``Z``), epoch seconds,
    or epoch milliseconds. Returns an empty ResetInfo on any parse failure.
    Display strings (weekday, time, countdown) are rendered in ``language``
    per the ``LOCALES`` table, falling back to English.
    """
    if not ts:
        return ResetInfo()
    try:
        if isinstance(ts, (int, float)):
            if ts > 1e10:  # heuristic: epoch milliseconds
                ts /= 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        now = now or datetime.now(tz=timezone.utc)
        remaining = max(0.0, (dt - now).total_seconds())
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        loc = dt.astimezone()
        loc_table = _locale(language)
        month = loc_table["months"][loc.month - 1]
        hour_u, minute_u = loc_table["hour_unit"], loc_table["minute_unit"]
        return ResetInfo(
            date=(
                f"{loc.day} {month}"
                if loc_table["date_day_first"]
                else f"{month} {loc.day:02d}"
            ),
            time=(
                loc.strftime("%H:%M")
                if loc_table["clock_24h"]
                else loc.strftime("%I:%M %p")
            ),
            weekday=loc_table["weekdays"][loc.weekday()],
            countdown=(
                f"{hours}{hour_u} {minutes}{minute_u}"
                if hours
                else f"{minutes}{minute_u}"
            ),
        )
    except (ValueError, OverflowError, OSError):
        return ResetInfo()


def _as_float(value) -> float | None:
    """Coerce a numeric-ish value to float, or None if not convertible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_fable(raw: dict) -> tuple[float | None, str | None]:
    """Extract the Fable weekly quota from the raw usage payload.

    The Fable quota is undocumented and shows up in two different shapes
    depending on the account/rollout, so this probes defensively:

    1. The top-level ``limits`` array — the current source of truth on
       migrated accounts. The Fable window is the entry with
       ``kind == "weekly_scoped"`` whose ``scope.model.display_name`` is
       "Fable" (case-insensitive; ``scope.model.id`` is often ``null``).
       Utilization is exposed as ``percent`` here, not ``utilization``.
    2. Legacy flat keys (``seven_day_fable`` and friends), each an object
       with ``utilization`` (or ``percent``) and ``resets_at``.

    Returns ``(percent, resets_at)``. ``percent`` is ``None`` when no Fable
    quota is present so callers can render "unavailable" rather than 0%.
    Every field may be ``null`` in the payload, so all access is guarded.
    """
    if not isinstance(raw, dict):
        return (None, None)

    # 1. limits[] array (current format).
    limits = raw.get("limits")
    if isinstance(limits, list):
        for entry in limits:
            if not isinstance(entry, dict):
                continue
            if entry.get("kind") != "weekly_scoped":
                continue
            scope = entry.get("scope")
            model = scope.get("model") if isinstance(scope, dict) else None
            name = model.get("display_name") if isinstance(model, dict) else None
            if not isinstance(name, str) or name.strip().lower() != FABLE_MODEL_NAME:
                continue
            return (_as_float(entry.get("percent")), entry.get("resets_at"))

    # 2. Legacy flat keys.
    for key in FABLE_FLAT_KEYS:
        window = raw.get(key)
        if isinstance(window, dict):
            pct = _as_float(window.get("utilization"))
            if pct is None:
                pct = _as_float(window.get("percent"))
            return (pct, window.get("resets_at"))

    return (None, None)


def detect_plan(org) -> str:
    """Derive the subscription plan from the ``/api/organizations/{id}`` payload.

    Reads ``rate_limit_tier`` (e.g. ``default_claude_max_5x``) and falls back
    to the ``capabilities`` array. Unknown tiers are prettified
    (``default_claude_foo_7x`` → "Foo 7x") so new plans still render something
    useful. Returns ``NOT_AVAILABLE`` when nothing can be derived.
    """
    if not isinstance(org, dict):
        return NOT_AVAILABLE

    tier = org.get("rate_limit_tier")
    if isinstance(tier, str) and tier:
        if tier in PLAN_TIERS:
            return PLAN_TIERS[tier]
        pretty = tier
        for prefix in ("default_", "claude_"):
            pretty = pretty.removeprefix(prefix)
        pretty = pretty.replace("_", " ").strip().capitalize()
        if pretty:
            return pretty

    caps = org.get("capabilities")
    if isinstance(caps, list):
        for capability, plan in PLAN_CAPABILITIES:
            if capability in caps:
                return plan

    return NOT_AVAILABLE


@dataclass(frozen=True)
class ClaudeUsage:
    """A snapshot of Claude.ai usage limits."""

    session_pct: float
    weekly_pct: float
    session_reset: ResetInfo
    weekly_reset: ResetInfo
    plan: str = NOT_AVAILABLE
    fable_pct: float | None = None
    fable_reset: ResetInfo = ResetInfo()

    @classmethod
    def from_payload(
        cls,
        raw: dict,
        now: datetime | None = None,
        org: dict | None = None,
        language: str = "en",
    ) -> ClaudeUsage:
        """Build a ClaudeUsage from the raw claude.ai usage API payload.

        Expected shape::

            {"five_hour": {"utilization": 22, "resets_at": "..."},
             "seven_day": {"utilization": 7, "resets_at": "..."}}

        The optional Fable weekly quota is parsed separately by
        :func:`extract_fable`, which handles the ``limits[]`` and legacy
        flat-key shapes. ``fable_pct`` stays ``None`` when absent.

        ``org`` is the (optional) organization payload; the subscription plan
        is derived from it by :func:`detect_plan` and stays ``NOT_AVAILABLE``
        when the payload is missing. ``language`` localizes the display
        strings (weekdays, times, countdowns) via the ``LOCALES`` table.
        """
        sess = raw.get("five_hour") or {}
        week = raw.get("seven_day") or {}
        fable_pct, fable_resets_at = extract_fable(raw)
        return cls(
            session_pct=float(sess.get("utilization") or 0),
            weekly_pct=float(week.get("utilization") or 0),
            session_reset=parse_reset_timestamp(
                sess.get("resets_at"), now, language
            ),
            weekly_reset=parse_reset_timestamp(
                week.get("resets_at"), now, language
            ),
            plan=detect_plan(org),
            fable_pct=fable_pct,
            fable_reset=parse_reset_timestamp(fable_resets_at, now, language),
        )

    def as_sensor_data(self) -> dict:
        """Flatten into the dict consumed by the sensor platform."""
        weekly = self.weekly_reset
        fable = self.fable_reset
        return {
            "session_pct":             self.session_pct,
            "session_used":            self.session_pct,
            "session_limit":           100.0,
            "session_reset_time":      self.session_reset.time,
            "session_reset_countdown": self.session_reset.countdown,
            "weekly_pct":              self.weekly_pct,
            "weekly_reset_date":       weekly.date,
            "weekly_reset_time":       weekly.time,
            "weekly_reset_weekday":    weekly.weekday,
            "weekly_reset":            (
                f"{weekly.weekday} @ {weekly.time}"
                if weekly.is_known
                else NOT_AVAILABLE
            ),
            "plan":       self.plan,
            "fable_pct":  self.fable_pct,
            "fable_reset": (
                f"{fable.weekday} @ {fable.time}"
                if fable.is_known
                else NOT_AVAILABLE
            ),
            "fetched_at": datetime.now().strftime("%H:%M"),
        }
