#!/usr/bin/env python3
"""
Claude Usage Fetcher for Home Assistant
Save this file in /homeassistant/claude_usage.py
Run: python3 /homeassistant/claude_usage.py <SESSION_KEY> <ORG_ID>
"""
import urllib.request, json, sys
from datetime import datetime, timezone

CONFIG_FILE = "/config/claude_config.json"
try:
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    SESSION_KEY = cfg.get("session_key", "")
    ORG_ID = cfg.get("org_id", "")
except Exception as e:
    print(json.dumps({"error": str(e), "session_pct": 0, "weekly_pct": 0}))
    sys.exit(0)

HEADERS = {
    "Cookie": f"sessionKey={SESSION_KEY}",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0",
    "Accept": "application/json",
    "Referer": "https://claude.ai/settings/usage",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
}

ENDPOINTS = []
if ORG_ID:
    ENDPOINTS += [f"https://claude.ai/api/organizations/{ORG_ID}/usage"]
ENDPOINTS += ["https://claude.ai/api/usage", "https://claude.ai/api/account/usage"]

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())

def fmt(ts):
    e = {"date": "N/A", "time": "N/A", "weekday": "N/A", "countdown": "N/A"}
    if not ts:
        return e
    try:
        if isinstance(ts, (int, float)):
            if ts > 1e10: ts /= 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)
        s = max(0, (dt - now).total_seconds())
        h, m = int(s // 3600), int((s % 3600) // 60)
        loc = dt.astimezone()
        return {
            "date":      loc.strftime("%b %d"),
            "time":      loc.strftime("%I:%M %p"),
            "weekday":   loc.strftime("%A"),
            "countdown": f"{h}h {m}m" if h else f"{m}m",
        }
    except:
        return e

raw = None
last_err = ""
for url in ENDPOINTS:
    try:
        raw = fetch(url)
        break
    except Exception as e:
        last_err = str(e)
        continue

if raw is None:
    print(json.dumps({
        "error": f"all endpoints failed: {last_err}",
        "session_pct": 0, "session_used": 0, "session_limit": 100,
        "session_reset_time": "N/A", "session_reset_countdown": "N/A",
        "weekly_pct": 0, "weekly_used": 0, "weekly_limit": 100,
        "weekly_reset_date": "N/A", "weekly_reset_time": "N/A", "weekly_reset_weekday": "N/A",
        "plan": "Pro", "fetched_at": datetime.now().strftime("%H:%M"),
    }))
    sys.exit(0)

# Current format API claude.ai:
# { "five_hour": {"utilization": 22, "resets_at": "2026-..."}, "seven_day": {...} }
sess = raw.get("five_hour") or {}
week = raw.get("seven_day") or {}

sess_pct = float(sess.get("utilization") or 0)
week_pct = float(week.get("utilization") or 0)

sr = fmt(sess.get("resets_at"))
wr = fmt(week.get("resets_at"))

print(json.dumps({
    "session_pct":             sess_pct,
    "session_used":            sess_pct,
    "session_limit":           100,
    "session_reset_time":      sr["time"],
    "session_reset_countdown": sr["countdown"],
    "weekly_pct":              week_pct,
    "weekly_used":             week_pct,
    "weekly_limit":            100,
    "weekly_reset_date":       wr["date"],
    "weekly_reset_time":       wr["time"],
    "weekly_reset_weekday":    wr["weekday"],
    "plan":                    "Pro",
    "fetched_at":              datetime.now().strftime("%H:%M"),
}))