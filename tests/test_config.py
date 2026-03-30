import os
import pytest
from unittest.mock import patch


def test_load_config_raises_on_missing_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("TRMNL_WEBHOOK_URL", "https://example.com")
    with patch("on_this_day.config.load_dotenv"):
        from on_this_day.config import load_config
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            load_config()


def test_load_config_raises_on_missing_webhook_url(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("TRMNL_WEBHOOK_URL", raising=False)
    with patch("on_this_day.config.load_dotenv"):
        from on_this_day.config import load_config
        with pytest.raises(ValueError, match="TRMNL_WEBHOOK_URL"):
            load_config()


def test_load_config_returns_config_with_valid_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_SCORING_API_KEY", "scoring-key")
    monkeypatch.setenv("TRMNL_WEBHOOK_URL", "https://example.com")
    with patch("on_this_day.config.load_dotenv"):
        from on_this_day.config import load_config
        c = load_config()
        assert c.gemini_api_key == "test-key"
        assert c.gemini_scoring_api_key == "scoring-key"
        assert c.trmnl_webhook_url == "https://example.com"
        assert c.log_level == "INFO"


def test_load_config_today_is_a_date(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("GEMINI_SCORING_API_KEY", "s")
    monkeypatch.setenv("TRMNL_WEBHOOK_URL", "https://example.com")
    from datetime import date
    with patch("on_this_day.config.load_dotenv"):
        from on_this_day.config import load_config
        c = load_config()
        assert isinstance(c.today, date)
