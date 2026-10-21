"""Fixtures compartilhadas dos testes (herméticos — sem `.env` real nem rede)."""

import pytest

from bot.config import Config


@pytest.fixture
def config_ok(monkeypatch):
    """Configura a `Config` com valores fictícios para testes."""
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [111, 222])
    return Config
