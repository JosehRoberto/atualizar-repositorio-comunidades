"""Testes dos schemas (pydantic)."""

import pytest
from pydantic import ValidationError

from bot.schemas.comunidade import ComunidadeSchema, LinkSchema


class TestComunidadeSchema:
    def test_valido(self):
        c = ComunidadeSchema(nome="Açaí com Dados", links=[{"tipo": "Site", "url": "https://x.com"}])
        assert c.nome == "Açaí com Dados"
        assert len(c.links) == 1

    def test_nome_vazio(self):
        with pytest.raises(ValidationError):
            ComunidadeSchema(nome="   ")

    def test_url_invalida(self):
        with pytest.raises(ValidationError):
            LinkSchema(tipo="Site", url="nao-e-url")
