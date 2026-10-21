"""Testes herméticos do módulo de templates de links (`link_template.py`)."""

from __future__ import annotations

import pytest

from bot.services import link_template


class TestMontarUrl:
    def test_handle_aplica_template(self):
        assert link_template.montar_url("Instagram", "usuario") == "https://instagram.com/usuario"

    def test_handle_remove_arroba_e_barra(self):
        assert link_template.montar_url("Telegram", "@canal") == "https://t.me/canal"
        assert link_template.montar_url("X", "/user") == "https://x.com/user"

    def test_url_completa_tem_precedencia(self):
        assert link_template.montar_url("Site", "https://meusite.com") == "https://meusite.com"
        assert (
            link_template.montar_url("Instagram", "https://instagram.com/x")
            == "https://instagram.com/x"
        )

    def test_tipos_sem_template_exigem_url(self):
        with pytest.raises(ValueError):
            link_template.montar_url("Site", "meusite")
        with pytest.raises(ValueError):
            link_template.montar_url("Discord", "discord.gg/abc")

    def test_tipo_outros_exige_url(self):
        with pytest.raises(ValueError):
            link_template.montar_url("Outros", "qualquer")

    def test_valor_vazio(self):
        with pytest.raises(ValueError):
            link_template.montar_url("Instagram", "   ")


class TestPrecisaUrlCompleta:
    def test_com_template(self):
        assert link_template.precisa_url_completa("Instagram") is False

    def test_sem_template(self):
        assert link_template.precisa_url_completa("Site") is True
        assert link_template.precisa_url_completa("Outros") is True
