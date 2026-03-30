import pytest
from unittest.mock import patch, MagicMock
import requests


def test_post_to_trmnl_sends_raw_png():
    from on_this_day.poster import post_to_trmnl
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("on_this_day.poster.requests.post", return_value=mock_resp) as mock_post:
        post_to_trmnl(b"fake-png-bytes", "https://example.com/webhook")
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["data"] == b"fake-png-bytes"
    assert kwargs["headers"]["Content-Type"] == "image/png"
    assert kwargs["timeout"] == 15


def test_post_to_trmnl_raises_on_http_error():
    from on_this_day.poster import post_to_trmnl
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    with patch("on_this_day.poster.requests.post", return_value=mock_resp):
        with pytest.raises(requests.HTTPError):
            post_to_trmnl(b"bytes", "https://example.com/webhook")


def test_post_to_trmnl_retries_once_on_failure():
    from on_this_day.poster import post_to_trmnl
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = requests.HTTPError("503")
    ok_resp = MagicMock()
    ok_resp.raise_for_status.return_value = None
    with patch("on_this_day.poster.requests.post", side_effect=[fail_resp, ok_resp]) as mock_post:
        with patch("on_this_day.poster.time.sleep") as mock_sleep:
            post_to_trmnl(b"bytes", "https://example.com/webhook")
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(2)


def test_post_to_trmnl_uses_correct_url():
    from on_this_day.poster import post_to_trmnl
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("on_this_day.poster.requests.post", return_value=mock_resp) as mock_post:
        post_to_trmnl(b"bytes", "https://trmnl.com/api/plugin_settings/abc/image")
    url = mock_post.call_args[0][0]
    assert url == "https://trmnl.com/api/plugin_settings/abc/image"
