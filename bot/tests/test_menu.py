"""Testes herméticos dos helpers e da persistência do fluxo do menu (`menu.py`).

Não exercitam o Telegram diretamente: cobrem as funções puras (parse/validação de
texto, resolução de seção, preview, teclado) e a aplicação/persistência sobre um
`ReadmeDoc` real, usando `tmp_path` (sem rede, sem produção).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from telegram.ext import ConversationHandler

from bot.config import Config
from bot.handlers import menu
from bot.handlers.menu import (
    CB_CANCELAR,
    CB_EDITAR,
    CB_OK,
    CB_SECAO,
    aplicar_no_doc,
    lista_secoes_editaveis,
    parse_links,
    persistir,
    resolver_secao,
    teclado_aprovacao,
    teclado_candidatos,
    texto_candidatos,
    texto_lista_secoes,
    texto_preview,
    texto_resumo_comunidade,
)
from bot.handlers.state_manager import Acao, ConversaUsuario, EstadoConversa, gerenciador
from bot.models.comunidade import Comunidade, Link
from bot.services import escrita_service, historico_service
from bot.services.readme_service import parse_readme

README_FIXTURE = """# 💻 Comunidades

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

---

<a name="mulheres"></a>
## 👩 Mulheres

| Comunidade | Links |
|---|---|
| **Divas Digitais** | <a href="https://instagram.com/divas" title="Instagram"><img src="x" alt="Instagram"/></a> |

---

<a name="observatorio"></a>
## 🌐 Observatório

| Serviço | Link |
|---|---|
| **NexAmazônia** | <a href="https://nex.com" title="Site"><img src="x" alt="Site"/></a> |
"""


@pytest.fixture
def doc():
    return parse_readme(README_FIXTURE)


@pytest.fixture
def readme_path(tmp_path):
    caminho = tmp_path / "repositorio" / "README.md"
    caminho.parent.mkdir(parents=True)
    caminho.write_text(README_FIXTURE, encoding="utf-8")
    return caminho


class TestParseLinks:
    def test_formato_espaco(self):
        links, invalidas = parse_links("Instagram https://instagram.com/x")
        assert links == [Link("Instagram", "https://instagram.com/x")]
        assert invalidas == []

    def test_formato_dois_pontos(self):
        links, _ = parse_links("Site: https://x.com")
        assert links == [Link("Site", "https://x.com")]

    def test_multiplas_linhas(self):
        links, invalidas = parse_links("Site https://x.com\nTelegram https://t.me/x")
        assert [l.tipo for l in links] == ["Site", "Telegram"]
        assert invalidas == []

    def test_linha_invalida(self):
        links, invalidas = parse_links("só-uma-coisa")
        assert links == []
        assert invalidas == ["só-uma-coisa"]

    def test_ignora_linhas_vazias(self):
        links, _ = parse_links("\n\nSite https://x.com\n\n")
        assert len(links) == 1

    def test_tipo_com_espacos_removido(self):
        links, _ = parse_links("Site   https://x.com")
        assert links[0].tipo == "Site"
        assert links[0].url == "https://x.com"


class TestSecoes:
    def test_lista_editaveis_exclui_observatorio_e_navegacao(self, doc):
        assert lista_secoes_editaveis(doc) == ["Linguagens", "Mulheres"]

    def test_texto_lista_numerado(self, doc):
        texto = texto_lista_secoes(doc)
        assert "1. Linguagens" in texto
        assert "2. Mulheres" in texto

    def test_resolver_por_numero(self, doc):
        assert resolver_secao(doc, "1") == "Linguagens"
        assert resolver_secao(doc, "2") == "Mulheres"

    def test_resolver_por_nome_case_insensitive(self, doc):
        assert resolver_secao(doc, "mulheres") == "Mulheres"

    def test_resolver_numero_fora_da_faixa(self, doc):
        assert resolver_secao(doc, "99") is None

    def test_resolver_nome_inexistente(self, doc):
        assert resolver_secao(doc, "Observatório") is None


class TestTeclado:
    def test_callbacks(self):
        teclado = teclado_aprovacao()
        callbacks = [botao.callback_data for linha in teclado.inline_keyboard for botao in linha]
        assert callbacks == [CB_OK, CB_EDITAR, CB_SECAO, CB_CANCELAR]


class TestCandidatos:
    def test_teclado_numerado_com_indices(self):
        teclado = teclado_candidatos(["Delphi", "Divas"], "edit_cand")
        botoes = [botao for linha in teclado.inline_keyboard for botao in linha]
        assert [b.text for b in botoes] == ["1. Delphi", "2. Divas"]
        assert [b.callback_data for b in botoes] == ["edit_cand_0", "edit_cand_1"]

    def test_texto_candidatos(self):
        texto = texto_candidatos(["Delphi", "Divas"], "remover")
        assert "remover" in texto
        assert "1. Delphi" in texto and "2. Divas" in texto


class TestPreview:
    def test_contem_nome_secao_e_linha(self, doc):
        conversa = ConversaUsuario(user_id=1)
        conversa.acao = Acao.NOVA
        conversa.rascunho = Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")])
        texto = texto_preview(conversa, "Linguagens")
        assert "GruPy Pará" in texto
        assert "Linguagens" in texto
        assert "**GruPy Pará**" in texto

    def test_resumo_comunidade(self):
        texto = texto_resumo_comunidade(Comunidade("X", [Link("Site", "https://x.com")]))
        assert "Site" in texto and "https://x.com" in texto

    def test_resumo_sem_links(self):
        assert "sem links" in texto_resumo_comunidade(Comunidade("X", []))


class TestAplicarNoDoc:
    def _conversa(self, acao, **kwargs):
        conversa = ConversaUsuario(user_id=1)
        conversa.acao = acao
        for chave, valor in kwargs.items():
            setattr(conversa, chave, valor)
        return conversa

    def test_nova_insere(self, doc):
        conversa = self._conversa(
            Acao.NOVA,
            rascunho=Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]),
            secao_alvo="Linguagens",
        )
        resumo = aplicar_no_doc(doc, conversa)
        assert "GruPy Pará" in resumo
        assert doc.buscar("GruPy Pará") is not None

    def test_nova_migra_marcador(self, doc):
        conversa = self._conversa(
            Acao.NOVA,
            rascunho=Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")]),
            secao_alvo="Linguagens",
        )
        aplicar_no_doc(doc, conversa)
        assert doc.buscar("Delphi").marcada is False
        assert doc.buscar("GruPy Pará").marcada is True

    def test_editar(self, doc):
        conversa = self._conversa(
            Acao.EDITAR,
            nome_original="Delphi",
            rascunho=Comunidade("Delphi", [Link("Site", "https://novo.dug.pa")]),
            secao_alvo="Linguagens",
        )
        resumo = aplicar_no_doc(doc, conversa)
        assert "Editada" in resumo
        assert doc.buscar("Delphi").comunidade.links[0].url == "https://novo.dug.pa"

    def test_remover(self, doc):
        conversa = self._conversa(Acao.REMOVER, nome_original="Delphi", secao_alvo="Linguagens")
        resumo = aplicar_no_doc(doc, conversa)
        assert "Removida" in resumo
        assert doc.buscar("Delphi") is None


class TestPersistir:
    def test_backup_grava_e_historia(self, readme_path, tmp_path):
        doc = parse_readme(README_FIXTURE)
        conversa = ConversaUsuario(user_id=7)
        conversa.acao = Acao.NOVA
        conversa.secao_alvo = "Linguagens"
        conversa.rascunho = Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")])
        resumo = aplicar_no_doc(doc, conversa)

        backup_dir = tmp_path / "backup"
        historico_path = tmp_path / "history" / "historico.jsonl"
        backup = persistir(
            doc,
            caminho=readme_path,
            backup_dir=backup_dir,
            historico_path=historico_path,
            usuario_id=7,
            conversa=conversa,
            resumo=resumo,
        )

        assert backup.is_file()
        assert "GruPy Pará" in readme_path.read_text(encoding="utf-8")
        assert backup.read_text(encoding="utf-8") == README_FIXTURE

        registros = historico_service.ler_historico(historico_path)
        assert len(registros) == 1
        assert registros[0].acao == "nova"
        assert registros[0].usuario_id == 7
        assert registros[0].comunidade == "GruPy Pará"
        assert registros[0].backup_path == str(backup)

    def test_backup_usa_um_timestamp(self, readme_path, tmp_path):
        doc = parse_readme(README_FIXTURE)
        conversa = ConversaoFake()
        persistir(
            doc,
            caminho=readme_path,
            backup_dir=tmp_path / "backup",
            historico_path=tmp_path / "h.jsonl",
            usuario_id=1,
            conversa=conversa,
            resumo="ok",
        )
        backups = list((tmp_path / "backup").glob("README_*.bak"))
        assert len(backups) == 1


class ConversaoFake:
    """Conversa mínima para testar a persistência sem alterar o documento."""

    acao = Acao.REMOVER
    nome_original = "Delphi"
    secao_alvo = "Linguagens"
    rascunho = None


class FakeUser:
    def __init__(self, uid=1):
        self.id = uid


class FakeMessage:
    def __init__(self, texto=""):
        self.text = texto
        self.chat_id = 1
        self.sent = []

    async def reply_text(self, texto, **kwargs):
        self.sent.append((texto, kwargs))


class FakeQuery:
    def __init__(self, data, uid=1):
        self.data = data
        self.from_user = FakeUser(uid)
        self.message = FakeMessage()
        self.answerado = False

    async def answer(self):
        self.answerado = True


class FakeUpdate:
    def __init__(self, data, uid=1):
        self.effective_user = FakeUser(uid)
        self.message = FakeMessage()
        self.callback_query = FakeQuery(data, uid=uid)


class FakeContext:
    def __init__(self):
        self.user_data = {}


def _update_texto(texto, uid=1):
    update = FakeUpdate(None, uid)
    update.callback_query = None
    update.message.text = texto
    return update


class FakeGit:
    def sincronizar(self):
        pass


@pytest.fixture
def ambiente_menu(tmp_path, monkeypatch):
    readme = tmp_path / "repositorio" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(README_FIXTURE, encoding="utf-8")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    monkeypatch.setattr(Config, "README_PATH", readme)
    monkeypatch.setattr(Config, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [1])
    gerenciador.conversas.clear()
    yield readme
    gerenciador.conversas.clear()


class TestAprovacaoSeguranca:
    @pytest.mark.asyncio
    async def test_hash_mudou_exige_novo_preview(self, ambiente_menu, monkeypatch):
        monkeypatch.setattr(menu.GitService, "from_config", staticmethod(lambda: FakeGit()))
        conversa = gerenciador.iniciar(
            1, Acao.NOVA, rascunho=Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")])
        )
        conversa.secao_alvo = "Linguagens"
        conversa.hash_base = "hash-antigo"
        update = FakeUpdate(CB_OK)
        estado = await menu.aprovacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any(
            escrita_service.MENSAGEM_HASH_MUDOU in t for t, _ in update.callback_query.message.sent
        )

    @pytest.mark.asyncio
    async def test_ocupado_avisa(self, ambiente_menu):
        update = FakeUpdate(CB_OK)
        async with escrita_service.lock_escrita():
            estado = await menu.aprovacao(update, FakeContext())
        assert estado is EstadoConversa.APROVACAO
        assert any(
            escrita_service.MENSAGEM_OCUPADO in t for t, _ in update.callback_query.message.sent
        )


class TestBuscaFuzzyHandlers:
    @pytest.mark.asyncio
    async def test_editar_fuzzy_lista_candidatos(self, ambiente_menu):
        gerenciador.iniciar(1, Acao.EDITAR)
        update = _update_texto("d")
        estado = await menu.editar_nome(update, FakeContext())
        assert estado is EstadoConversa.EDITAR_CANDIDATOS
        conversa = gerenciador.obter(1)
        assert len(conversa.candidatos) >= 2
        assert update.message.sent

    @pytest.mark.asyncio
    async def test_editar_candidato_escolhido(self, ambiente_menu):
        gerenciador.iniciar(1, Acao.EDITAR)
        await menu.editar_nome(_update_texto("d"), FakeContext())
        update = FakeUpdate("edit_cand_0")
        estado = await menu.editar_candidato(update, FakeContext())
        assert estado is EstadoConversa.EDITAR_ESCOLHA
        conversa = gerenciador.obter(1)
        assert conversa.rascunho.nome == "Delphi"
        assert conversa.candidatos == []

    @pytest.mark.asyncio
    async def test_editar_candidato_unico_nao_lista(self, ambiente_menu):
        gerenciador.iniciar(1, Acao.EDITAR)
        estado = await menu.editar_nome(_update_texto("delph"), FakeContext())
        assert estado is EstadoConversa.EDITAR_ESCOLHA
        assert gerenciador.obter(1).nome_original == "Delphi"

    @pytest.mark.asyncio
    async def test_remover_fuzzy_lista_e_confirmacao(self, ambiente_menu):
        gerenciador.iniciar(1, Acao.REMOVER)
        estado = await menu.remover_nome(_update_texto("d"), FakeContext())
        assert estado is EstadoConversa.REMOVER_CANDIDATOS
        update = FakeUpdate("rem_cand_0")
        estado = await menu.remover_candidato(update, FakeContext())
        assert estado is EstadoConversa.REMOVER_CONFIRMACAO
        conversa = gerenciador.obter(1)
        assert conversa.nome_original == "Delphi"
        assert conversa.hash_base

    @pytest.mark.asyncio
    async def test_remover_candidato_invalido(self, ambiente_menu):
        gerenciador.iniciar(1, Acao.REMOVER)
        await menu.remover_nome(_update_texto("d"), FakeContext())
        update = FakeUpdate("rem_cand_99")
        estado = await menu.remover_candidato(update, FakeContext())
        assert estado == ConversationHandler.END
        assert gerenciador.obter(1).estado is EstadoConversa.IDLE

    def test_candidato_desempata_pela_url(self, tmp_path, monkeypatch):
        readme = tmp_path / "README.md"
        readme.write_text(
            """<a name="c"></a>
## 🏙️ Capítulos

| Comunidade | Links |
|---|---|
| **Comunidade X** | <a href="https://x.com/primeira" title="Site"><img src="x"/></a> |
| **Comunidade X** | <a href="https://x.com/segunda" title="Site"><img src="x"/></a> |
""",
            encoding="utf-8",
        )
        monkeypatch.setattr(Config, "README_PATH", readme)
        conversa = ConversaUsuario(user_id=1)
        conversa.candidatos = [("Comunidade X", "Capítulos", "https://x.com/segunda")]
        ocorrencia = menu._candidato_escolhido(conversa, 0)
        assert ocorrencia.comunidade.links[0].url == "https://x.com/segunda"

    @pytest.mark.asyncio
    async def test_buscar_fuzzy_mostra_candidatos(self, ambiente_menu):
        update = _update_texto("d")
        estado = await menu.buscar_nome(update, FakeContext())
        assert estado == ConversationHandler.END
        texto = update.message.sent[0][0]
        assert "Delphi" in texto and "Divas Digitais" in texto


class TestEscapeMarkdown:
    """Correção do erro `Can't parse entities` (URL com `_` em Markdown v1)."""

    def test_resumo_escapa_url_com_underscore(self):
        texto = texto_resumo_comunidade(
            Comunidade("Elug PA", [Link("Telegram", "https://t.me/elug_pa")])
        )
        assert "https://t.me/elug\\_pa" in texto

    def test_preview_escapa_nome_e_secao_e_preserva_codigo(self):
        conversa = ConversaUsuario(user_id=1)
        conversa.acao = Acao.NOVA
        conversa.rascunho = Comunidade("GruPy_Pará", [Link("Site", "https://t.me/grupy_pa")])
        texto = texto_preview(conversa, "Linguagens_2026")
        assert "GruPy\\_Pará" in texto
        assert "Linguagens\\_2026" in texto
        assert "**GruPy_Pará**" in texto

    def test_persistir_nao_corrompe_readme(self, readme_path, tmp_path):
        doc = parse_readme(README_FIXTURE)
        conversa = ConversaUsuario(user_id=7)
        conversa.acao = Acao.NOVA
        conversa.secao_alvo = "Linguagens"
        conversa.rascunho = Comunidade("GruPy_Pará", [Link("Telegram", "https://t.me/grupy_pa")])
        resumo = aplicar_no_doc(doc, conversa)
        persistir(
            doc,
            caminho=readme_path,
            backup_dir=tmp_path / "backup",
            historico_path=tmp_path / "h.jsonl",
            usuario_id=7,
            conversa=conversa,
            resumo=resumo,
        )
        conteudo = readme_path.read_text(encoding="utf-8")
        assert "GruPy_Pará" in conteudo
        assert "\\" not in conteudo
        assert "GruPy\\_Pará" in resumo
