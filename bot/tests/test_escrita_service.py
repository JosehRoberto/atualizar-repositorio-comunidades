"""Testes herméticos do serviço de escrita (lock, sincronização e hash — §2.12)."""

import hashlib

import pytest

from bot.services import escrita_service
from bot.services.git_service import GitError


class FakeGit:
    def __init__(self, erro=None):
        self._erro = erro
        self.sincronizou = False

    def sincronizar(self):
        if self._erro:
            raise self._erro
        self.sincronizou = True


class TestHash:
    def test_hash_atual(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text("abc", encoding="utf-8")
        assert escrita_service.hash_atual(arquivo) == hashlib.sha256(b"abc").hexdigest()

    def test_conferir_hash_igual(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text("abc", encoding="utf-8")
        esperado = escrita_service.hash_atual(arquivo)
        assert escrita_service.conferir_hash(arquivo, esperado) is None

    def test_conferir_hash_mudou(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text("abc", encoding="utf-8")
        arquivo.write_text("xyz", encoding="utf-8")
        assert escrita_service.conferir_hash(arquivo, "hash-antigo") == escrita_service.MENSAGEM_HASH_MUDOU

    def test_conferir_hash_sem_esperado(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text("abc", encoding="utf-8")
        assert escrita_service.conferir_hash(arquivo, None) is None

    def test_conferir_hash_arquivo_ausente(self, tmp_path):
        assert "não foi encontrado" in escrita_service.conferir_hash(tmp_path / "x.md", "h")


class TestSincronizacao:
    def test_ok(self):
        servico = FakeGit()
        assert escrita_service.sincronizar_seguro(servico) is None
        assert servico.sincronizou is True

    def test_erro_vira_mensagem(self):
        mensagem = escrita_service.sincronizar_seguro(FakeGit(erro=GitError("conflito")))
        assert "sincronizar" in mensagem
        assert "conflito" in mensagem


class TestLock:
    def test_inicialmente_livre(self):
        assert escrita_service.ocupado() is False

    @pytest.mark.asyncio
    async def test_ocupado_durante_uso(self):
        async with escrita_service.lock_escrita():
            assert escrita_service.ocupado() is True
        assert escrita_service.ocupado() is False

    def test_lock_e_singleton(self):
        assert escrita_service.lock_escrita() is escrita_service.lock_escrita()
