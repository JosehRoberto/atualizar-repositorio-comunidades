"""Testes do modelo de domínio."""

from bot.models.comunidade import Comunidade, Link


class TestNomeNormalizado:
    def test_remove_acentos_e_caixa(self):
        assert Comunidade("Árdua Ção").nome_normalizado() == "ardua cao"

    def test_colapsa_espacos(self):
        assert Comunidade("  Foo   Bar ").nome_normalizado() == "foo bar"

    def test_comunidade_com_links(self):
        c = Comunidade("Norte4j", [Link("Site", "https://norte4j.com")])
        assert c.links[0].tipo == "Site"
        assert c.nome_normalizado() == "norte4j"
