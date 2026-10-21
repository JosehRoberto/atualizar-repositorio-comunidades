"""Testes herméticos da publicação e restauração (`publicacao.py`).

Git (`subprocess`) é substituído por um duplo; backups/histórico usam `tmp_path`.
Sem rede, sem `.env` real e sem tocar em produção.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from telegram.ext import ConversationHandler

from bot.config import Config
from bot.handlers import publicacao
from bot.handlers.state_manager import Acao, EstadoConversa, gerenciador
from bot.services import escrita_service, historico_service


@pytest.fixture(autouse=True)
def limpar_gerenciador():
    gerenciador.conversas.clear()
    yield
    gerenciador.conversas.clear()


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    readme = tmp_path / "repositorio" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# v1\n", encoding="utf-8")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    monkeypatch.setattr(Config, "README_PATH", readme)
    monkeypatch.setattr(Config, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(Config, "TELEGRAM_ALLOWED_USER_IDS", [1])
    return SimpleNamespace(readme=readme, backup_dir=backup_dir)


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


class FakeUpdate:
    def __init__(self, texto="", uid=1):
        self.effective_user = FakeUser(uid)
        self.message = FakeMessage(texto)
        self.callback_query = None


class FakeQuery:
    def __init__(self, data, uid=1):
        self.data = data
        self.from_user = FakeUser(uid)
        self.message = FakeMessage()
        self.answerado = False

    async def answer(self):
        self.answerado = True


class FakeContext:
    def __init__(self):
        self.user_data = {}


def callback_update(data, uid=1):
    update = FakeUpdate(uid=uid)
    update.callback_query = FakeQuery(data, uid=uid)
    return update


class FakeGit:
    def __init__(self, alteracoes=(), commits=(), commit_hash="abc12345", erro=None, pendente=False):
        self._alteracoes = list(alteracoes)
        self._commits = list(commits)
        self._commit_hash = commit_hash
        self._erro = erro
        self._pendente = pendente
        self.chamadas = []

    def alteracoes(self):
        if self._erro:
            raise self._erro
        return self._alteracoes

    def commits_pendentes(self):
        if self._erro:
            raise self._erro
        return self._commits

    def readme_pendente(self, caminho=None):
        if self._erro:
            raise self._erro
        return self._pendente or bool(self._alteracoes)

    def sincronizar(self):
        self.chamadas.append("sincronizar")

    def sincronizar_publicacao(self):
        self.chamadas.append("sincronizar_publicacao")

    def commit(self, arquivo, mensagem):
        self.chamadas.append("commit")
        return self._commit_hash

    def push(self):
        self.chamadas.append("push")


def usar_git(monkeypatch, fake):
    monkeypatch.setattr(publicacao.GitService, "from_config", staticmethod(lambda: fake))


def criar_backup(ambiente, nome, conteudo="# antigo\n"):
    caminho = ambiente.backup_dir / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


class TestBackups:
    def test_lista_exclui_pre_restauracao_e_ordena(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        criar_backup(ambiente, "README_20260102_000000.bak")
        criar_backup(ambiente, "README_pre-restauracao_20260103_000000.bak")
        nomes = [p.name for p in publicacao.backups_restauraveis(ambiente.backup_dir)]
        assert nomes == ["README_20260102_000000.bak", "README_20260101_000001.bak"]

    def test_vazio(self, ambiente):
        assert publicacao.backups_restauraveis(ambiente.backup_dir) == []

    def test_texto_numerado(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        backups = publicacao.backups_restauraveis(ambiente.backup_dir)
        texto = publicacao.texto_backups(backups)
        assert "1. `README_20260101_000001.bak`" in texto

    def test_resolver_por_numero(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        backups = publicacao.backups_restauraveis(ambiente.backup_dir)
        assert publicacao.resolver_backup(backups, "1").name == "README_20260101_000001.bak"

    def test_resolver_invalido(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        backups = publicacao.backups_restauraveis(ambiente.backup_dir)
        assert publicacao.resolver_backup(backups, "9") is None
        assert publicacao.resolver_backup(backups, "abc") is None


class TestTextosETeclados:
    def test_texto_publicacao(self):
        texto = publicacao.texto_publicacao([" M repositorio/README.md"])
        assert "Alterações pendentes" in texto
        assert "M repositorio/README.md" in texto

    def test_texto_restauracao_com_diff(self):
        texto = publicacao.texto_restauracao("README_x.bak", "-antigo\n+novo")
        assert "README_x.bak" in texto
        assert "-antigo" in texto

    def test_texto_restauracao_sem_diff(self):
        assert "sem diferenças" in publicacao.texto_restauracao("README_x.bak", "")

    def test_teclado_publicacao(self):
        teclado = publicacao.teclado_publicacao()
        callbacks = [b.callback_data for linha in teclado.inline_keyboard for b in linha]
        assert callbacks == [publicacao.CB_PUB_OK, publicacao.CB_PUB_CANCELAR]

    def test_teclado_restauracao(self):
        teclado = publicacao.teclado_restauracao()
        callbacks = [b.callback_data for linha in teclado.inline_keyboard for b in linha]
        assert callbacks == [publicacao.CB_REST_OK, publicacao.CB_REST_CANCELAR]


class TestPublicar:
    @pytest.mark.asyncio
    async def test_sem_alteracoes(self, ambiente, monkeypatch):
        usar_git(monkeypatch, FakeGit(alteracoes=[]))
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_publicar(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("Nada a publicar" in t for t, _ in update.message.sent)

    @pytest.mark.asyncio
    async def test_com_alteracoes(self, ambiente, monkeypatch):
        usar_git(monkeypatch, FakeGit(alteracoes=[" M repositorio/README.md"]))
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_publicar(update, FakeContext())
        assert estado is EstadoConversa.PUBLICAR_CONFIRMACAO
        texto, kwargs = update.message.sent[-1]
        assert "Alterações pendentes" in texto
        assert "reply_markup" in kwargs

    @pytest.mark.asyncio
    async def test_erro_git(self, ambiente, monkeypatch):
        usar_git(monkeypatch, FakeGit(erro=publicacao.GitError("falhou")))
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_publicar(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("Não foi possível inspecionar" in t for t, _ in update.message.sent)

    @pytest.mark.asyncio
    async def test_cancelar(self, ambiente):
        update = callback_update(publicacao.CB_PUB_CANCELAR)
        estado = await publicacao.publicar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("cancelada" in t for t, _ in update.callback_query.message.sent)

    @pytest.mark.asyncio
    async def test_confirmar(self, ambiente, monkeypatch):
        fake = FakeGit(pendente=True)
        usar_git(monkeypatch, fake)
        update = callback_update(publicacao.CB_PUB_OK)
        estado = await publicacao.publicar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert fake.chamadas == ["commit", "sincronizar_publicacao", "push"]
        registros = historico_service.ler_historico(publicacao._historico_path())
        assert registros[-1].acao == "publicar"
        assert registros[-1].commit == "abc12345"

    @pytest.mark.asyncio
    async def test_confirmar_commits_a_frente_sem_sujidade(self, ambiente, monkeypatch):
        # R1: há commits à frente (push anterior falhou) mas a árvore está limpa.
        fake = FakeGit(commits=["abc1234 chore: msg"], pendente=False)
        usar_git(monkeypatch, fake)
        update = callback_update(publicacao.CB_PUB_OK)
        estado = await publicacao.publicar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert fake.chamadas == ["sincronizar_publicacao", "push"]

    @pytest.mark.asyncio
    async def test_publicar_com_dirty_detecta_pendencia(self, ambiente, monkeypatch):
        # cmd_publicar considera commits à frente + arquivos sujos.
        usar_git(monkeypatch, FakeGit(alteracoes=[" M README.md"], commits=["abc commit"]))
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_publicar(update, FakeContext())
        assert estado is EstadoConversa.PUBLICAR_CONFIRMACAO
        texto, _ = update.message.sent[-1]
        assert "commit: abc commit" in texto

    @pytest.mark.asyncio
    async def test_publicar_bloqueado_por_lock(self, ambiente, monkeypatch):
        # R11: restauração/publicação serializadas.
        usar_git(monkeypatch, FakeGit(alteracoes=[" M README.md"]))
        update = callback_update(publicacao.CB_PUB_OK)
        async with escrita_service.lock_escrita():
            estado = await publicacao.publicar_confirmacao(update, FakeContext())
        assert estado is EstadoConversa.PUBLICAR_CONFIRMACAO

    @pytest.mark.asyncio
    async def test_restaurar_bloqueado_por_lock(self, ambiente):
        # R11: restaurar recusa quando há edição em andamento.
        backup = criar_backup(ambiente, "README_20260101_000001.bak", conteudo="# antigo\n")
        gerenciador.obter(1).backup_escolhido = str(backup)
        update = callback_update(publicacao.CB_REST_OK)
        async with escrita_service.lock_escrita():
            estado = await publicacao.restaurar_confirmacao(update, FakeContext())
        assert estado is EstadoConversa.RESTAURAR_CONFIRMACAO
        assert any(
            escrita_service.MENSAGEM_OCUPADO in t
            for t, _ in update.callback_query.message.sent
        )
        assert not list(ambiente.backup_dir.glob("README_pre-restauracao_*.bak"))


class TestRestaurar:
    @pytest.mark.asyncio
    async def test_sem_backups(self, ambiente):
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_restaurar(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("Nenhum backup" in t for t, _ in update.message.sent)

    @pytest.mark.asyncio
    async def test_lista_backups(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        update = FakeUpdate(uid=1)
        estado = await publicacao.cmd_restaurar(update, FakeContext())
        assert estado is EstadoConversa.RESTAURAR_ESCOLHA

    @pytest.mark.asyncio
    async def test_escolha_invalida(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak")
        update = FakeUpdate("9", uid=1)
        estado = await publicacao.restaurar_escolha(update, FakeContext())
        assert estado is EstadoConversa.RESTAURAR_ESCOLHA
        assert any("inválido" in t for t, _ in update.message.sent)

    @pytest.mark.asyncio
    async def test_escolha_valida(self, ambiente):
        criar_backup(ambiente, "README_20260101_000001.bak", conteudo="# antigo\n")
        update = FakeUpdate("1", uid=1)
        estado = await publicacao.restaurar_escolha(update, FakeContext())
        assert estado is EstadoConversa.RESTAURAR_CONFIRMACAO
        assert gerenciador.obter(1).backup_escolhido.endswith("README_20260101_000001.bak")

    @pytest.mark.asyncio
    async def test_cancelar(self, ambiente):
        update = callback_update(publicacao.CB_REST_CANCELAR)
        estado = await publicacao.restaurar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("cancelada" in t for t, _ in update.callback_query.message.sent)

    @pytest.mark.asyncio
    async def test_confirmar_restaura(self, ambiente):
        backup = criar_backup(ambiente, "README_20260101_000001.bak", conteudo="# antigo\n")
        gerenciador.obter(1).backup_escolhido = str(backup)
        update = callback_update(publicacao.CB_REST_OK)
        estado = await publicacao.restaurar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert ambiente.readme.read_text(encoding="utf-8") == "# antigo\n"
        pres = list(ambiente.backup_dir.glob("README_pre-restauracao_*.bak"))
        assert len(pres) == 1
        registros = historico_service.ler_historico(publicacao._historico_path())
        assert registros[-1].acao == "restaurar"

    @pytest.mark.asyncio
    async def test_confirmar_sem_backup_escolhido(self, ambiente):
        update = callback_update(publicacao.CB_REST_OK)
        estado = await publicacao.restaurar_confirmacao(update, FakeContext())
        assert estado == ConversationHandler.END
        assert any("não encontrado" in t for t, _ in update.callback_query.message.sent)


class TestIntegracao:
    def test_entradas_e_estados(self):
        entradas = publicacao.entradas_publicacao()
        assert len(entradas) == 2
        estados = publicacao.estados_publicacao()
        assert set(estados) == {
            EstadoConversa.PUBLICAR_CONFIRMACAO,
            EstadoConversa.RESTAURAR_ESCOLHA,
            EstadoConversa.RESTAURAR_CONFIRMACAO,
        }
