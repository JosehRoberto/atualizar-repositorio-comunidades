"""Testes da configuração."""

from bot.config import Config, _parse_ids


class TestParseIds:
    def test_lista_simples(self):
        assert _parse_ids("1,2,3") == [1, 2, 3]

    def test_com_espacos(self):
        assert _parse_ids("1, 2 ,3") == [1, 2, 3]

    def test_vazio(self):
        assert _parse_ids("") == []


class TestValidar:
    def test_sem_token(self, monkeypatch):
        monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [1])
        assert "TELEGRAM_BOT_TOKEN ausente" in Config.validar()

    def test_sem_usuarios(self, monkeypatch):
        monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "x")
        monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [])
        assert "TELEGRAM_ALLOWED_USER_IDS ausente" in Config.validar()

    def test_ok(self, monkeypatch):
        monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "x")
        monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [1])
        assert Config.validar() == []
