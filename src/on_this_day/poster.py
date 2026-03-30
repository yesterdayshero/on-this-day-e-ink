from __future__ import annotations

import time

import requests

_RETRY_DELAY = 2  # seconds


def post_to_trmnl(image_bytes: bytes, webhook_url: str) -> None:
    """POST PNG image bytes to the TRMNL webhook endpoint."""
    for attempt in range(2):
        try:
            response = requests.post(
                webhook_url,
                data=image_bytes,
                headers={"Content-Type": "image/png"},
                timeout=15,
            )
            response.raise_for_status()
            return
        except requests.RequestException:
            if attempt == 0:
                time.sleep(_RETRY_DELAY)
            else:
                raise
