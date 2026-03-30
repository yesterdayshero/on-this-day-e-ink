from __future__ import annotations

import base64
import logging
import time

import requests

logger = logging.getLogger(__name__)

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)
_PRIMARY_MODEL = "gemini-3.1-flash-image-preview"
_FALLBACK_MODEL = "gemini-2.5-flash-image"

_STYLE_PROMPTS: dict[str, str] = {
    "woodcut": (
        "A highly detailed vintage woodcut print depicting {scene}. "
        "Style: classic editorial woodcut — dense crosshatching, fine linework, rich tonal gradations, realistic human figures and environments. "
        "Cinematic full-bleed composition: the subject fills every corner of the frame with no background visible, no borders, no margins, no white space. "
        "High contrast black and white with detailed shading through crosshatch and parallel line work. "
        "Sophisticated and dramatic, like a fine art print from a 1960s magazine. "
        "NO text, letters, numbers, captions, or words anywhere in the image."
    ),
    "sketch": (
        "A highly detailed pencil sketch depicting {scene}. "
        "Style: expressive graphite pencil drawing — varied line weight, loose hatching, soft tonal gradations, realistic human figures and environments. "
        "Cinematic full-bleed composition: the subject fills every corner of the frame with no background visible, no borders, no margins, no white space. "
        "Black and white with detailed shading through pencil strokes and hatching, ranging from delicate light lines to dense dark areas. "
        "Sophisticated and dramatic, like a fine art illustration from a literary magazine. "
        "16:9 landscape format, wide cinematic framing. "
        "NO text, letters, numbers, captions, or words anywhere in the image."
    ),
}
_DEFAULT_STYLE = "sketch"

_MAX_RETRIES = 3
_BASE_DELAY_S = 5
_RETRY_STATUS_CODES = {429, 500, 503}


def generate_image(scene_description: str, api_key: str, style: str = _DEFAULT_STYLE) -> bytes | None:
    """Call Gemini REST API to generate a styled PNG. Returns PNG bytes or None on failure."""
    template = _STYLE_PROMPTS.get(style) or _STYLE_PROMPTS[_DEFAULT_STYLE]
    prompt = template.format(scene=scene_description)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["image"],
            "imageConfig": {"aspectRatio": "16:9"},
        },
    }
    headers = {"Content-Type": "application/json"}

    for attempt in range(_MAX_RETRIES):
        model = _PRIMARY_MODEL if attempt < 2 else _FALLBACK_MODEL
        if attempt == 2:
            logger.warning("Falling back to %s", _FALLBACK_MODEL)
        url = _API_URL.format(model=model, api_key=api_key)
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=(10, 120))
            response.raise_for_status()
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"])
            logger.error("Gemini response contained no inlineData image part")
            return None

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in _RETRY_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY_S * (2 ** attempt)
                logger.warning("Gemini HTTP %s on attempt %d/%d — retrying in %ds", status, attempt + 1, _MAX_RETRIES, delay)
                time.sleep(delay)
            else:
                logger.error("Gemini HTTP %s — fatal", status)
                return None

        except requests.RequestException as exc:
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY_S * (2 ** attempt)
                logger.warning("Gemini network error on attempt %d/%d: %s — retrying in %ds", attempt + 1, _MAX_RETRIES, exc, delay)
                time.sleep(delay)
            else:
                logger.error("Gemini network error after all retries: %s", exc)
                return None

    logger.error("Gemini image generation failed after %d attempts", _MAX_RETRIES)
    return None
