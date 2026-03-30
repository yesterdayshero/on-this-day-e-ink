from __future__ import annotations

import io
import logging

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 15


def notify_success(
    webhook_url: str,
    image_bytes: bytes,
    year: str,
    description: str,
    runners_up: list[dict],
) -> None:
    """Post a success digest to Discord: image + event summary + runners-up."""
    lines = [
        f"**On This Day — {year}**",
        description,
        "",
        "**Runners-up:**",
    ]
    for i, r in enumerate(runners_up, 1):
        ry = r.get("year", "?")
        rt = r.get("text", "")[:100]
        lines.append(f"{i}. [{ry}] {rt}")

    payload = {"content": "\n".join(lines)}
    files = {"file": ("latest.png", io.BytesIO(image_bytes), "image/png")}

    resp = requests.post(
        webhook_url,
        data={"payload_json": __import__("json").dumps(payload)},
        files=files,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    logger.info("Discord success notification sent")


def notify_failure(webhook_url: str, error: str) -> None:
    """Post a failure alert to Discord."""
    payload = {"content": f"**On This Day — Pipeline Failed**\n{error}"}
    resp = requests.post(webhook_url, json=payload, timeout=_TIMEOUT)
    resp.raise_for_status()
    logger.info("Discord failure notification sent")
