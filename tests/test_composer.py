import io
import pytest
from PIL import Image


def _make_test_png(width=1000, height=1000, color=(180, 180, 180)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_compose_image_output_is_800x480():
    from on_this_day.composer import compose_image
    raw = _make_test_png()
    result = compose_image(raw, "1969", "Astronauts landed on the Moon")
    img = Image.open(io.BytesIO(result))
    assert img.size == (800, 480)


def test_compose_image_is_grayscale_with_4_levels():
    from on_this_day.composer import compose_image
    raw = _make_test_png()
    result = compose_image(raw, "1969", "First Moon landing")
    img = Image.open(io.BytesIO(result)).convert("L")
    pixel_values = set(img.getdata())
    # Must only contain values from {0, 85, 170, 255}
    assert pixel_values.issubset({0, 85, 170, 255})


def test_compose_image_returns_png_bytes():
    from on_this_day.composer import compose_image
    raw = _make_test_png()
    result = compose_image(raw, "1900", "Something happened")
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


def test_compose_image_overlay_adds_white_region():
    """The overlay box should add white pixels in the bottom-right area."""
    from on_this_day.composer import compose_image
    # Use a pure black source image so any white must be from overlay
    raw = _make_test_png(color=(0, 0, 0))
    result = compose_image(raw, "1969", "Test overlay text here")
    img = Image.open(io.BytesIO(result)).convert("L")
    # Check bottom-right quadrant has some white pixels (value 255)
    w, h = img.size
    bottom_right = img.crop((w // 2, h // 2, w, h))
    assert 255 in set(bottom_right.getdata())


def test_compose_image_handles_wide_source():
    """Center-crop should handle images wider than 800:480 ratio."""
    from on_this_day.composer import compose_image
    raw = _make_test_png(width=2000, height=500)  # wider than 800:480
    result = compose_image(raw, "1900", "Test event")
    img = Image.open(io.BytesIO(result))
    assert img.size == (800, 480)


def test_compose_image_handles_tall_source():
    """Center-crop should handle images taller than 800:480 ratio (e.g. square)."""
    from on_this_day.composer import compose_image
    raw = _make_test_png(width=800, height=800)  # taller than 800:480
    result = compose_image(raw, "1900", "Test event")
    img = Image.open(io.BytesIO(result))
    assert img.size == (800, 480)
