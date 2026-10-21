"""Testes herméticos do serviço de busca fuzzy (`busca_service`)."""

from __future__ import annotations

import pytest

from bot.services.busca_service import (
    MAX_CANDIDATOS,
    candidatos,
    chave_busca,
    nomes_duplicados,
    pontuar,
    rotulo_candidato,
)
from bot.services.readme_service import parse_readme

README = """# Comunidades

---

## 🗂️ Navegação Rápida

- [Capítulos](#capitulos)

---

<a name="capitulos"></a>
## 🏙️ Capítulos

| Comunidade | Links |
|---|---|
| **AWS Student Builder Groups** | <a href="https://aws.student" title="Site"><img src="x"/></a> |
| **AWS User Group Castanhal** | <a href="https://aws.castanhal" title="Site"><img src="x"/></a> |
| **Delphi Users Group Pará** | <a href="https://dug.pa" title="Site"><img src="x"/></a> |

---

<a name="mulheres"></a>
## 👩 Mulheres

| Comunidade | Links |
|---|---|
| **Divas Digitais** | <a href="https://instagram.com/divas" title="Instagram"><img src="x"/></a> |
| **Comunidade X** | <a href="https://x.com/primeira" title="Site"><img src="x"/></a> |

---

<a name="outra"></a>
## 🎓 Outra

| Comunidade | Links |
|---|---|
| **Comunidade X** | <a href="https://x.com/segunda" title="Site"><img src="x"/></a> |
"""


@pytest.fixture
def doc():
    return parse_readme(README)


class TestChaveBusca:
    def test_remove_acentos_emojis_e_pontuacao(self):
        assert chave_busca("  👩 Divas Digitais!!!  ") == "divas digitais"
        assert chave_busca("Delphi Users Group Pará") == "delphi users group para"

    def test_texto_vazio(self):
        assert chave_busca("🚀 !!!") == ""


class TestPontuar:
    def test_igualdade_maxima(self):
        assert pontuar("Divas Digitais", "divas digitais") == 2.0

    def test_substring_recebe_bonus(self):
        assert pontuar("castanha", "AWS User Group Castanhal") >= 0.9

    def test_erro_de_digitacao_fica_acima_do_limite(self):
        assert pontuar("Delph Users", "Delphi Users Group Pará") >= 0.6

    def test_termo_sem_relacao_fica_abaixo_do_limite(self):
        assert pontuar("kubernetes", "Divas Digitais") < 0.6


class TestCandidatos:
    def test_encontra_por_erro_de_digitacao(self, doc):
        nomes = [oc.comunidade.nome for oc in candidatos(doc, "AWS User Group Castanha")]
        assert "AWS User Group Castanhal" in nomes

    def test_ordena_do_mais_similar(self, doc):
        nomes = [oc.comunidade.nome for oc in candidatos(doc, "delphi users group para")]
        assert nomes[0] == "Delphi Users Group Pará"

    def test_respeita_limite_de_candidatos(self, doc):
        assert len(candidatos(doc, "a", maximo=2)) == 2

    def test_sem_candidatos(self, doc):
        assert candidatos(doc, "kubernetes") == []

    def test_nao_excede_maximo_padrao(self, doc):
        assert len(candidatos(doc, "a")) <= MAX_CANDIDATOS


class TestDesempatePorUrl:
    def test_detecta_nomes_duplicados(self, doc):
        assert nomes_duplicados(doc) == {"comunidade x"}

    def test_rotulo_usa_url_em_homonimos(self, doc):
        ocorrencia = doc.buscar("Comunidade X", "Outra")
        rotulo = rotulo_candidato(ocorrencia, nomes_duplicados(doc))
        assert rotulo == "Comunidade X — https://x.com/segunda"

    def test_rotulo_simples_para_nome_unico(self, doc):
        ocorrencia = doc.buscar("Divas Digitais")
        assert rotulo_candidato(ocorrencia, nomes_duplicados(doc)) == "Divas Digitais"
