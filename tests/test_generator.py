import base64
import io
import pytest
from unittest.mock import patch, MagicMock, call
from PIL import Image


def _make_fake_png_b64() -> str:
    """Create a tiny valid PNG and return as base64 string."""
    img = Image.new("RGB", (10, 10), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _mock_success_response(b64_data: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"inlineData": {"data": b64_data}}]
            }
        }]
    }
    return mock


def test_generate_image_returns_png_bytes():
    from on_this_day.generator import generate_image
    b64 = _make_fake_png_b64()
    mock_resp = _mock_success_response(b64)
    with patch("on_this_day.generator.requests.post", return_value=mock_resp):
        result = generate_image("a woodcut scene", "fake-key")
    assert isinstance(result, bytes)
    # Should be valid PNG
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


def test_generate_image_retries_on_429():
    from on_this_day.generator import generate_image
    import requests as req
    b64 = _make_fake_png_b64()
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = req.HTTPError(response=MagicMock(status_code=429))
    success_resp = _mock_success_response(b64)
    with patch("on_this_day.generator.requests.post", side_effect=[fail_resp, success_resp]):
        with patch("on_this_day.generator.time.sleep"):  # skip actual sleep
            result = generate_image("a scene", "fake-key")
    assert result is not None


def test_generate_image_returns_none_after_all_retries_fail():
    from on_this_day.generator import generate_image
    import requests as req
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = req.HTTPError(response=MagicMock(status_code=500))
    with patch("on_this_day.generator.requests.post", return_value=fail_resp):
        with patch("on_this_day.generator.time.sleep"):
            result = generate_image("a scene", "fake-key")
    assert result is None


def test_generate_image_falls_back_to_secondary_model():
    from on_this_day.generator import generate_image, _PRIMARY_MODEL, _FALLBACK_MODEL
    import requests as req
    b64 = _make_fake_png_b64()
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = req.HTTPError(response=MagicMock(status_code=500))
    success_resp = _mock_success_response(b64)
    with patch("on_this_day.generator.requests.post", side_effect=[fail_resp, fail_resp, success_resp]) as mock_post:
        with patch("on_this_day.generator.time.sleep"):
            result = generate_image("a scene", "fake-key")
    assert result is not None
    urls = [c[0][0] for c in mock_post.call_args_list]
    assert _PRIMARY_MODEL in urls[0]
    assert _PRIMARY_MODEL in urls[1]
    assert _FALLBACK_MODEL in urls[2]


def test_generate_image_url_contains_api_key():
    from on_this_day.generator import generate_image
    b64 = _make_fake_png_b64()
    mock_resp = _mock_success_response(b64)
    with patch("on_this_day.generator.requests.post", return_value=mock_resp) as mock_post:
        generate_image("a scene", "my-secret-key")
    url = mock_post.call_args[0][0]
    assert "my-secret-key" in url
