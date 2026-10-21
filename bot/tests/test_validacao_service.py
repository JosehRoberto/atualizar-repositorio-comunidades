"""Testes herméticos do serviço de validações (sem rede; fixtures em memória)."""

import pytest

from bot.models.comunidade import Comunidade, Link
from bot.services.readme_service import parse_readme
from bot.services.validacao_service import (
    AVISO,
    ERRO,
    Relatorio,
    buscar_por_url,
    comparar_estrutura,
    normalizar_url,
    similares,
    url_valida,
    validar_comunidade,
    validar_readme,
    validar_secao,
)

README_VALIDO = """# 💻 Comunidades

---

## 🗂️ Navegação Rápida

- [💻 Linguagens](#linguagens)
- [👩 Mulheres](#mulheres)

---

<a name="linguagens"></a>
## 💻 Linguagens

| Comunidade | Links |
|---|---|
| **Delphi** :triangular_flag_on_post: | <a href="https://dug-pa.com.br/" title="Site"><img src="x" alt="Site"/></a> |
| **Elixir** | <a href="https://www.instagram.com/elixir" title="Instagram"><img src="x" alt="Instagram"/></a> |

---

<a name="mulheres"></a>
## 👩 Mulheres

| Comunidade | Links |
|---|---|
| **Divas Digitais** | <a href="https://www.instagram.com/divas" title="Instagram"><img src="x" alt="Instagram"/></a> |
"""


@pytest.fixture
def doc():
    return parse_readme(README_VALIDO)


class TestUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://example.com/path",
            "https://www.instagram.com/x",
            "tg://resolve?domain=grupo",
            "telegram.me/grupo",
            "t.me/grupo",
            "www.exemplo.com.br",
        ],
    )
    def test_validas(self, url):
        assert url_valida(url) is True

    @pytest.mark.parametrize(
        "url",
        ["", "   ", "nao-e-url", "https://", "http://sem-ponto", "ftp://example.com", "mailto:a@b.com"],
    )
    def test_invalidas(self, url):
        assert url_valida(url) is False

    def test_normaliza_sem_esquema(self):
        assert normalizar_url("telegram.me/grupo") == "https://telegram.me/grupo"

    def test_remove_espacos(self):
        assert normalizar_url(" https://x.com/a b ") == "https://x.com/ab"

    def test_preserva_esquema_existente(self):
        assert normalizar_url("tg://resolve?domain=x") == "tg://resolve?domain=x"


class TestSimilares:
    def test_encontra_parecido(self, doc):
        assert "Elixir" in similares(doc, "Elixirr")

    def test_nao_inclui_identico(self, doc):
        assert similares(doc, "Elixir") == []

    def test_sem_parecidos(self, doc):
        assert similares(doc, "Comunidade Totalmente Diferente") == []


class TestBuscarPorUrl:
    def test_encontra_por_url(self, doc):
        assert buscar_por_url(doc, "https://www.instagram.com/elixir").comunidade.nome == "Elixir"

    def test_normaliza_barra_final(self, doc):
        assert buscar_por_url(doc, "https://www.instagram.com/elixir/").comunidade.nome == "Elixir"

    def test_ausente(self, doc):
        assert buscar_por_url(doc, "https://nao-existe.com") is None


class TestValidarSecao:
    def test_ok(self, doc):
        assert validar_secao(doc, "Linguagens").ok

    def test_inexistente(self, doc):
        rel = validar_secao(doc, "Não Existe")
        assert [p.codigo for p in rel.erros] == ["secao_inexistente"]

    def test_nao_editavel(self):
        texto = README_VALIDO + """
<a name="obs"></a>
## 🌐 Observatório

| Serviço | Link |
|---|---|
| **NexAmazônia** | <a href="https://nex.com" title="Site"><img src="x" alt="Site"/></a> |
"""
        doc = parse_readme(texto)
        rel = validar_secao(doc, "Observatório")
        assert [p.codigo for p in rel.erros] == ["secao_nao_editavel"]


class TestValidarComunidade:
    def _ok(self):
        return Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")])

    def test_ok(self, doc):
        assert validar_comunidade(doc, self._ok()).ok

    def test_nome_vazio(self, doc):
        rel = validar_comunidade(doc, Comunidade("   ", [Link("Site", "https://x.com")]))
        assert "nome_vazio" in [p.codigo for p in rel.erros]

    def test_sem_links(self, doc):
        rel = validar_comunidade(doc, Comunidade("Nova", []))
        assert "sem_links" in [p.codigo for p in rel.erros]

    def test_url_invalida(self, doc):
        rel = validar_comunidade(doc, Comunidade("Nova", [Link("Site", "nao-e-url")]))
        assert "url_invalida" in [p.codigo for p in rel.erros]

    def test_tipo_vazio(self, doc):
        rel = validar_comunidade(doc, Comunidade("Nova", [Link("  ", "https://x.com")]))
        assert "tipo_vazio" in [p.codigo for p in rel.erros]

    def test_nome_duplicado(self, doc):
        rel = validar_comunidade(doc, Comunidade("Elixir", [Link("Site", "https://novo.x")]))
        assert "nome_duplicado" in [p.codigo for p in rel.erros]

    def test_nome_similar_gera_aviso(self, doc):
        rel = validar_comunidade(doc, Comunidade("Elixirr", [Link("Site", "https://novo.x")]))
        assert "nome_similar" in [p.codigo for p in rel.avisos]
        assert rel.ok is True

    def test_url_duplicada(self, doc):
        rel = validar_comunidade(
            doc, Comunidade("Nova", [Link("Instagram", "https://www.instagram.com/elixir")])
        )
        assert "url_duplicada" in [p.codigo for p in rel.erros]

    def test_url_repetida_na_mesma_comunidade(self, doc):
        rel = validar_comunidade(
            doc,
            Comunidade("Nova", [Link("Site", "https://x.com"), Link("Site", "https://x.com/")]),
        )
        assert "url_repetida" in [p.codigo for p in rel.erros]

    def test_ignorar_na_edicao(self, doc):
        rel = validar_comunidade(
            doc,
            Comunidade("Elixir", [Link("Instagram", "https://www.instagram.com/elixir")]),
            ignorar="Elixir",
        )
        assert rel.ok is True

    def test_pendente_no_fluxo(self, doc):
        rel = validar_comunidade(doc, Comunidade("Nova", [Link("Site", "https://x.com")]), pendentes=["Nova"])
        assert "nome_duplicado_fluxo" in [p.codigo for p in rel.erros]


class TestValidarReadme:
    def test_fixture_valida(self, doc):
        rel = validar_readme(doc)
        assert rel.ok is True
        assert rel.avisos == []

    def test_url_duplicada_entre_secoes(self, doc):
        doc.inserir("Mulheres", Comunidade("Clone", [Link("Instagram", "https://www.instagram.com/elixir")]))
        rel = validar_readme(doc)
        assert "url_duplicada" in [p.codigo for p in rel.erros]

    def test_nome_duplicado(self, doc):
        doc.inserir("Mulheres", Comunidade("Delphi", [Link("Site", "https://outro.com")]))
        rel = validar_readme(doc)
        assert "nome_duplicado" in [p.codigo for p in rel.erros]

    def test_ancora_ausente(self):
        texto = README_VALIDO.replace("#mulheres", "#nao-existe")
        rel = validar_readme(parse_readme(texto))
        assert "ancora_ausente" in [p.codigo for p in rel.erros]

    def test_url_invalida(self):
        texto = README_VALIDO.replace("https://dug-pa.com.br/", "https://")
        rel = validar_readme(parse_readme(texto))
        assert "url_invalida" in [p.codigo for p in rel.erros]

    def test_tabela_inconsistente(self):
        texto = README_VALIDO.replace(
            "| **Elixir** | <a href=\"https://www.instagram.com/elixir\" title=\"Instagram\">"
            "<img src=\"x\" alt=\"Instagram\"/></a> |",
            "| **Elixir** | <a href=\"https://www.instagram.com/elixir\" title=\"Instagram\">"
            "<img src=\"x\" alt=\"Instagram\"/></a> | coluna-extra |",
        )
        rel = validar_readme(parse_readme(texto))
        assert "tabela_inconsistente" in [p.codigo for p in rel.erros]

    def test_marcador_multiplo(self):
        texto = README_VALIDO.replace(
            "| **Divas Digitais** |",
            "| **Divas Digitais** :triangular_flag_on_post: |",
        )
        rel = validar_readme(parse_readme(texto))
        assert "marcador_multiplo" in [p.codigo for p in rel.erros]

    def test_marcador_ausente_gera_aviso(self):
        texto = README_VALIDO.replace(" :triangular_flag_on_post:", "")
        rel = validar_readme(parse_readme(texto))
        assert "marcador_ausente" in [p.codigo for p in rel.avisos]
        assert rel.ok is True


class TestCompararEstrutura:
    def test_insercao_preserva_estrutura(self, doc):
        antes = parse_readme(doc.render())
        doc.inserir("Linguagens", Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]))
        rel = comparar_estrutura(antes, doc)
        assert rel.ok is True

    def test_detecta_secao_alterada(self, doc):
        antes = parse_readme(doc.render())
        depois = parse_readme(doc.render().replace("## 👩 Mulheres", "## 👩 Mulheres Tech"))
        rel = comparar_estrutura(antes, depois)
        assert "secoes_alteradas" in [p.codigo for p in rel.erros]


class TestRelatorio:
    def test_ok_sem_erros(self):
        rel = Relatorio()
        assert rel.ok is True and bool(rel) is True and len(rel) == 0

    def test_erro_quebra_ok(self):
        from bot.services.validacao_service import Problema

        rel = Relatorio([Problema(ERRO, "x", "msg")])
        assert rel.ok is False and len(rel.erros) == 1

    def test_aviso_nao_quebra_ok(self):
        from bot.services.validacao_service import Problema

        rel = Relatorio([Problema(AVISO, "y", "msg")])
        assert rel.ok is True and len(rel.avisos) == 1
