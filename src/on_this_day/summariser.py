from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)
_PRIMARY_MODEL = "gemini-2.5-flash"
_FALLBACK_MODEL = "gemini-2.5-flash-lite"
_MAX_RETRIES = 3
_BASE_DELAY_S = 5
_WORD_LIMIT = 20
_PROMPT = (
    "Summarise the following historical event description in 15–20 words as a single complete "
    "sentence, preserving the key facts. Return only the summary, no explanation.\n\n{text}"
)


def summarise_description(text: str, api_key: str) -> str:
    """Return a short complete-sentence summary of text.

    If text is already within the word limit, returns it unchanged.
    Falls back to hard truncation if the API call fails.
    """
    words = text.split()
    if len(words) <= _WORD_LIMIT:
        return text

    payload = {
        "contents": [{"parts": [{"text": _PROMPT.format(text=text)}]}],
        "generationConfig": {"temperature": 0.2},
    }
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        if attempt > 0:
            delay = _BASE_DELAY_S * (2 ** (attempt - 1))
            logger.warning(
                "Summarisation attempt %d/%d failed — retrying in %ds",
                attempt, _MAX_RETRIES, delay,
            )
            time.sleep(delay)
        model = _PRIMARY_MODEL if attempt < 2 else _FALLBACK_MODEL
        if attempt == 2:
            logger.warning("Falling back to %s for summarisation", _FALLBACK_MODEL)
        try:
            response = requests.post(
                _API_URL.format(model=model, api_key=api_key),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            summary = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.debug("Summarised description: %s", summary)
            return summary
        except Exception as exc:
            last_exc = exc
            logger.warning("Summarisation attempt %d/%d failed: %s", attempt + 1, _MAX_RETRIES, exc)

    logger.warning(
        "Description summarisation failed after %d attempts, falling back to truncation: %s",
        _MAX_RETRIES, last_exc,
    )
    return " ".join(words[:_WORD_LIMIT])
