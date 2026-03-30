from __future__ import annotations

import time

import requests

_API_URL = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month:02d}/{day:02d}"
_HEADERS = {"User-Agent": "on-this-day-e-ink/1.0 (https://github.com/yesterdayshero/on-this-day-e-ink)"}
_RETRY_DELAY = 2  # seconds


def fetch_events(month: int, day: int) -> list[dict]:
    """Fetch all historical events from Wikipedia for a given month/day."""
    url = _API_URL.format(month=month, day=day)
    for attempt in range(2):
        try:
            response = requests.get(url, headers=_HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("events", []) + data.get("selected", []) + data.get("holidays", [])
        except requests.RequestException:
            if attempt == 0:
                time.sleep(_RETRY_DELAY)
            else:
                raise
