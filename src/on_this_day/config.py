from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_scoring_api_key: str
    trmnl_webhook_url: str
    discord_webhook_url: str
    log_level: str
    today: date
    image_style: str


def load_config() -> Config:
    load_dotenv()

    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_scoring_api_key = os.environ.get("GEMINI_SCORING_API_KEY", "").strip() or gemini_api_key
    trmnl_webhook_url = os.environ.get("TRMNL_WEBHOOK_URL", "").strip()

    missing = [
        name
        for name, val in [
            ("GEMINI_API_KEY", gemini_api_key),
            ("TRMNL_WEBHOOK_URL", trmnl_webhook_url),
        ]
        if not val
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    timezone = os.environ.get("TIMEZONE", "UTC")
    today = datetime.now(ZoneInfo(timezone)).date()
    image_style = os.environ.get("IMAGE_STYLE", "sketch").strip().lower()

    return Config(
        gemini_api_key=gemini_api_key,
        gemini_scoring_api_key=gemini_scoring_api_key,
        trmnl_webhook_url=trmnl_webhook_url,
        discord_webhook_url=discord_webhook_url,
        log_level=log_level,
        today=today,
        image_style=image_style,
    )
