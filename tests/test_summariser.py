from unittest.mock import patch, MagicMock


def _mock_response(summary: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": summary}]}}]
    }
    return mock


def test_short_text_returned_unchanged():
    from on_this_day.summariser import summarise_description
    text = "Apollo 11 landed on the Moon."
    with patch("on_this_day.summariser.requests.post") as mock_post:
        result = summarise_description(text, "fake-key")
    assert result == text
    mock_post.assert_not_called()


def test_long_text_calls_api_and_returns_summary():
    from on_this_day.summariser import summarise_description
    long_text = " ".join(["word"] * 25)
    summary = "Apollo 11 landed on the Moon in 1969, marking humanity's first lunar landing."
    with patch("on_this_day.summariser.requests.post", return_value=_mock_response(summary)):
        result = summarise_description(long_text, "fake-key")
    assert result == summary


def test_api_failure_falls_back_to_truncation():
    from on_this_day.summariser import summarise_description
    long_text = " ".join(str(i) for i in range(30))
    with patch("on_this_day.summariser.requests.post", side_effect=Exception("network error")):
        result = summarise_description(long_text, "fake-key")
    assert result == " ".join(str(i) for i in range(20))


def test_exactly_20_words_returned_unchanged():
    from on_this_day.summariser import summarise_description
    text = " ".join(["word"] * 20)
    with patch("on_this_day.summariser.requests.post") as mock_post:
        result = summarise_description(text, "fake-key")
    assert result == text
    mock_post.assert_not_called()
