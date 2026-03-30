from __future__ import annotations

import io
import textwrap

from PIL import Image, ImageDraw, ImageFont

_TARGET_W = 800
_TARGET_H = 480
_TARGET_RATIO = _TARGET_W / _TARGET_H

_FONT_PATHS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
]
_FONT_SIZE = 15
_OVERLAY_MAX_WIDTH = 380
_OVERLAY_PADDING = 6
_OVERLAY_MARGIN = 10
_LINE_SPACING = 2


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    if isinstance(font, ImageFont.ImageFont):
        return textwrap.wrap(text, width=max_width // 6)
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        w = font.getlength(test) if hasattr(font, "getlength") else font.getmask(test).getbbox()[2]
        if w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def compose_image(raw_png: bytes, year: str, description: str) -> bytes:
    """Crop to 800x480, posterise to 4 grayscale levels, add text overlay. Returns PNG bytes."""
    img = Image.open(io.BytesIO(raw_png)).convert("RGB")

    # Center-crop to 800:480 ratio
    w, h = img.size
    if w / h > _TARGET_RATIO:
        new_w = int(h * _TARGET_RATIO)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / _TARGET_RATIO)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    img = img.resize((_TARGET_W, _TARGET_H), Image.Resampling.LANCZOS)

    # Add overlay before posterising (font rendering needs full colour range)
    _add_overlay(img, year, description)

    # Convert to grayscale and posterise to 4 levels
    img = img.convert("L")
    img = img.point(lambda x: (x // 64) * 85)

    # Convert to 2-bit palette PNG (required by TRMNL OG e-ink display)
    img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _add_overlay(img: Image.Image, year: str, description: str) -> None:
    draw = ImageDraw.Draw(img)
    font = _load_font(_FONT_SIZE)
    full_text = f"On this day in {year}: {description}"
    lines = _wrap_text(full_text, font, _OVERLAY_MAX_WIDTH)

    line_heights = []
    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
        max_line_w = max(max_line_w, bbox[2] - bbox[0])

    total_h = sum(line_heights) + _LINE_SPACING * max(len(lines) - 1, 0)
    box_w = max_line_w + _OVERLAY_PADDING * 2
    box_h = total_h + _OVERLAY_PADDING * 2

    iw, ih = img.size
    x1 = max(iw - box_w - _OVERLAY_MARGIN, 0)
    y1 = max(ih - box_h - _OVERLAY_MARGIN, 0)
    x2 = iw - _OVERLAY_MARGIN
    y2 = ih - _OVERLAY_MARGIN

    draw.rectangle([x1, y1, x2, y2], fill="white", outline="black", width=2)

    cy = y1 + _OVERLAY_PADDING
    for i, line in enumerate(lines):
        draw.text((x1 + _OVERLAY_PADDING, cy), line, fill="black", font=font)
        cy += line_heights[i] + _LINE_SPACING
