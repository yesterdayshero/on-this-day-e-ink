import pytest
from unittest.mock import patch, MagicMock


MOCK_API_RESPONSE = {
    "events": [
        {"year": "1969", "text": "Apollo 11 Moon landing", "pages": [{"title": "Apollo 11"}, {"title": "Moon"}]},
        {"year": "1815", "text": "Battle of Waterloo ended", "pages": [{"title": "Waterloo"}]},
    ],
    "births": [
        {"year": "1879", "text": "Albert Einstein was born", "pages": [{"title": "Einstein"}]},
    ],
    "deaths": [],
    "selected": [],
    "holidays": [],
}


def test_fetch_events_returns_combined_list():
    from on_this_day.fetcher import fetch_events
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE
    mock_resp.raise_for_status.return_value = None
    with patch("on_this_day.fetcher.requests.get", return_value=mock_resp) as mock_get:
        events = fetch_events(7, 20)
    mock_get.assert_called_once()
    call_url = mock_get.call_args[0][0]
    assert "07/20" in call_url
    # events + selected + holidays = 2 + 0 + 0 = 2
    assert len(events) == 2


def test_fetch_events_raises_on_http_error():
    from on_this_day.fetcher import fetch_events
    import requests
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
    with patch("on_this_day.fetcher.requests.get", return_value=mock_resp):
        with pytest.raises(requests.HTTPError):
            fetch_events(1, 1)


def test_fetch_events_retries_once_on_failure():
    from on_this_day.fetcher import fetch_events
    import requests as req
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = req.HTTPError("503")
    ok_resp = MagicMock()
    ok_resp.json.return_value = {"events": [{"year": "1969", "text": "Moon", "pages": []}], "selected": [], "holidays": []}
    ok_resp.raise_for_status.return_value = None
    with patch("on_this_day.fetcher.requests.get", side_effect=[fail_resp, ok_resp]) as mock_get:
        with patch("on_this_day.fetcher.time.sleep") as mock_sleep:
            events = fetch_events(7, 20)
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(2)
    assert len(events) == 1


def test_fetch_events_url_format():
    from on_this_day.fetcher import fetch_events
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"events": [], "selected": [], "holidays": []}
    mock_resp.raise_for_status.return_value = None
    with patch("on_this_day.fetcher.requests.get", return_value=mock_resp) as mock_get:
        fetch_events(3, 5)
    url = mock_get.call_args[0][0]
    assert url.endswith("03/05")
