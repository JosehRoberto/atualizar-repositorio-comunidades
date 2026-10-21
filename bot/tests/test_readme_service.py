"""Testes herméticos do parser/editor do README (sem rede, sem arquivos de produção)."""

import pytest

from bot.models.comunidade import Comunidade, Link
from bot.services.readme_service import (
    MARCADOR,
    ComunidadeNaoEncontrada,
    SecaoNaoEditavel,
    SecaoNaoEncontrada,
    carregar_readme,
    ordenar_links,
    parse_readme,
    render_linha,
    salvar_readme,
)

README_FIXTURE = """# 💻 Comunidades Paraenses de Tecnologia e Inovação

---

## 🗂️ Navegação Rápida

- [💻 Linguagens de Programação](#linguagens-de-programacao)
- [👩‍💻 Mulheres & Diversidade](#mulheres)
- [🌐 Observatório](#observatorio)
- [🤝 Como Contribuir](#como-contribuir)

---

<a name="linguagens-de-programacao"></a>
## 💻 Linguagens de Programação

| Comunidade | Links |
|---|---|
| **Delphi Users Group Pará** :triangular_flag_on_post: | <a href="https://dug-pa.com.br/" title="Site"><img src="x" alt="Site"/></a> |
| **Elixir Carajás** | <a href="https://www.instagram.com/elixircarajas" title="Instagram"><img src="x" alt="Instagram"/></a> |

---

<a name="mulheres"></a>
## 👩‍💻 Mulheres & Diversidade

| Comunidade | Links |
|---|---|
| **Divas Digitais** | <a href="https://www.instagram.com/divassdigitais/" title="Instagram"><img src="x" alt="Instagram"/></a> |
| **PyLadies Belém** | <a href="https://www.facebook.com/pyladiesbelem" title="Facebook"><img src="x" alt="Facebook"/></a> |

---

<a name="observatorio"></a>
## 🌐 Observatório

| Serviço | Link |
|---|---|
| **NexAmazônia** | <a href="https://nexamazonia.com.br/" title="Site"><img src="x" alt="Site"/></a> |

---

## 🤝 Como Contribuir

1. Faça um fork.
"""


@pytest.fixture
def doc():
    return parse_readme(README_FIXTURE)


class TestParse:
    def test_round_trip_identico(self):
        assert parse_readme(README_FIXTURE).render() == README_FIXTURE

    def test_secoes_detectadas(self, doc):
        assert doc.listar_secoes() == [
            "🗂️ Navegação Rápida",
            "💻 Linguagens de Programação",
            "👩‍💻 Mulheres & Diversidade",
            "🌐 Observatório",
            "🤝 Como Contribuir",
        ]

    def test_ancora_e_emoji(self, doc):
        secao = doc.encontrar_secao("Linguagens de Programação")
        assert secao.ancora == "linguagens-de-programacao"
        assert secao.emoji == "💻"

    def test_schema_observatorio(self, doc):
        secao = doc.encontrar_secao("Observatório")
        assert secao.coluna_nome == "Serviço"

    def test_navegacao_rapida(self, doc):
        slugs = [item.slug for item in doc.navegacao]
        assert slugs == ["linguagens-de-programacao", "mulheres", "observatorio", "como-contribuir"]

    def test_comunidades_parseadas(self, doc):
        nomes = [oc.comunidade.nome for oc in doc.comunidades()]
        assert nomes == [
            "Delphi Users Group Pará",
            "Elixir Carajás",
            "Divas Digitais",
            "PyLadies Belém",
            "NexAmazônia",
        ]

    def test_links_parseados(self, doc):
        oc = doc.buscar("Divas Digitais")
        assert oc.comunidade.links == [
            Link(tipo="Instagram", url="https://www.instagram.com/divassdigitais/")
        ]

    def test_marcada(self, doc):
        assert doc.buscar("Delphi Users Group Pará").marcada is True
        assert doc.buscar("Divas Digitais").marcada is False


class TestRender:
    def test_ordenar_links_ordem_canonica(self):
        links = [
            Link("Telegram", "https://t.me/x"),
            Link("Site", "https://x.com"),
            Link("Instagram", "https://instagram.com/x"),
        ]
        assert [l.tipo for l in ordenar_links(links)] == ["Site", "Instagram", "Telegram"]

    def test_ordenar_links_desconhecido_preserva_cadastro(self):
        links = [Link("Zzz", "https://a.com"), Link("Site", "https://b.com"), Link("Aaa", "https://c.com")]
        assert [l.tipo for l in ordenar_links(links)] == ["Site", "Zzz", "Aaa"]

    def test_render_linha_sem_marcador(self):
        c = Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa"), Link("Telegram", "https://t.me/grupy")])
        linha = render_linha(c)
        assert linha.startswith("| **GruPy Pará** | ")
        assert MARCADOR not in linha
        assert '<a href="https://grupy.pa" title="Site">' in linha
        assert linha.index('title="Site"') < linha.index('title="Telegram"')

    def test_render_linha_com_marcador(self):
        c = Comunidade("Nova", [Link("Site", "https://nova.dev")])
        assert render_linha(c, marcada=True).startswith(f"| **Nova** {MARCADOR} |")


class TestInserir:
    def test_ordem_alfabetica(self, doc):
        doc.inserir("Linguagens de Programação", Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]))
        nomes = [
            oc.comunidade.nome
            for oc in doc._ocorrencias_da_secao(doc.encontrar_secao("Linguagens de Programação"))
        ]
        assert nomes == ["Delphi Users Group Pará", "Elixir Carajás", "GruPy Pará"]

    def test_insere_no_meio(self, doc):
        doc.inserir(
            "Linguagens de Programação",
            Comunidade("Egua", [Link("Site", "https://egua.dev")]),
        )
        nomes = [
            oc.comunidade.nome
            for oc in doc._ocorrencias_da_secao(doc.encontrar_secao("Linguagens de Programação"))
        ]
        assert nomes == ["Delphi Users Group Pará", "Egua", "Elixir Carajás"]

    def test_marcador_migra_para_nova(self, doc):
        doc.inserir("Linguagens de Programação", Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]))
        assert doc.buscar("Delphi Users Group Pará").marcada is False
        assert doc.buscar("GruPy Pará").marcada is True

    def test_secao_inexistente(self, doc):
        with pytest.raises(SecaoNaoEncontrada):
            doc.inserir("Não Existe", Comunidade("X", [Link("Site", "https://x.com")]))

    def test_observatorio_nao_editavel(self, doc):
        with pytest.raises(SecaoNaoEditavel):
            doc.inserir("Observatório", Comunidade("X", [Link("Site", "https://x.com")]))

    def test_alteracao_cirurgica(self, doc):
        antes = doc.render().split("\n")
        doc.inserir("Linguagens de Programação", Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]))
        depois = doc.render().split("\n")
        # Uma linha nova e uma linha alterada (marcador migrou do Delphi para a GruPy).
        assert len(depois) == len(antes) + 1
        linhas_intocadas = [l for l in antes if not l.startswith("| **Delphi")]
        assert all(l in depois for l in linhas_intocadas)
        assert any(l.startswith("| **GruPy Pará**") and MARCADOR in l for l in depois)


class TestEditar:
    def test_atualiza_links_e_preserva_marcador(self, doc):
        doc.editar(
            "Delphi Users Group Pará",
            Comunidade("Delphi Users Group Pará", [Link("Site", "https://novo.dug.pa")]),
        )
        oc = doc.buscar("Delphi Users Group Pará")
        assert oc.marcada is True
        assert oc.comunidade.links[0].url == "https://novo.dug.pa"

    def test_renomear_reordena(self, doc):
        doc.editar("Elixir Carajás", Comunidade("Zulu", [Link("Site", "https://zulu.dev")]))
        nomes = [
            oc.comunidade.nome
            for oc in doc._ocorrencias_da_secao(doc.encontrar_secao("Linguagens de Programação"))
        ]
        assert nomes == ["Delphi Users Group Pará", "Zulu"]

    def test_inexistente(self, doc):
        with pytest.raises(ComunidadeNaoEncontrada):
            doc.editar("Fantasma", Comunidade("Fantasma", [Link("Site", "https://x.com")]))


class TestRemover:
    def test_remove_linha(self, doc):
        doc.remover("Elixir Carajás")
        assert doc.buscar("Elixir Carajás") is None
        nomes = [
            oc.comunidade.nome
            for oc in doc._ocorrencias_da_secao(doc.encontrar_secao("Linguagens de Programação"))
        ]
        assert nomes == ["Delphi Users Group Pará"]

    def test_inexistente(self, doc):
        with pytest.raises(ComunidadeNaoEncontrada):
            doc.remover("Fantasma")


class TestNormalizarMarcador:
    def test_apenas_referencia_marcada(self, doc):
        doc.normalizar_marcador("Divas Digitais")
        marcadas = [oc.comunidade.nome for oc in doc.comunidades() if oc.marcada]
        assert marcadas == ["Divas Digitais"]
        assert doc.render().count(MARCADOR) == 1

    def test_referencia_ausente(self, doc):
        with pytest.raises(ComunidadeNaoEncontrada):
            doc.normalizar_marcador("Inexistente")


class TestIO:
    def test_carregar_e_salvar(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text(README_FIXTURE, encoding="utf-8")
        doc = carregar_readme(arquivo)
        doc.inserir("Linguagens de Programação", Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]))
        salvar_readme(doc, arquivo)
        assert "GruPy Pará" in arquivo.read_text(encoding="utf-8")
