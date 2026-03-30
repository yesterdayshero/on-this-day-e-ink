from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent?key={api_key}"
)
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

    try:
        payload = {
            "contents": [{"parts": [{"text": _PROMPT.format(text=text)}]}],
            "generationConfig": {"temperature": 0.2},
        }
        response = requests.post(
            _API_URL.format(api_key=api_key),
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
        logger.warning("Description summarisation failed, falling back to truncation: %s", exc)
        return " ".join(words[:_WORD_LIMIT])
