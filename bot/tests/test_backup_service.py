"""Testes herméticos do serviço de backup (tmp_path; sem rede nem produção)."""

import re
from datetime import datetime, timezone

import pytest

from bot.services.backup_service import (
    BackupError,
    BackupNaoEncontrado,
    criar_backup,
    diff_backup,
    limpar_antigos,
    listar_backups,
    restaurar_backup,
    timestamp_belem,
    ultimo_backup,
)


@pytest.fixture
def origem(tmp_path):
    arquivo = tmp_path / "repositorio" / "README.md"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("# README v1\n", encoding="utf-8")
    return arquivo


@pytest.fixture
def backup_dir(tmp_path):
    return tmp_path / "backup"


class TestTimestamp:
    def test_formato(self):
        assert re.fullmatch(r"\d{8}_\d{6}", timestamp_belem())

    def test_converte_para_fuso_belem(self):
        momento = datetime(2026, 10, 21, 15, 8, 59, tzinfo=timezone.utc)
        assert timestamp_belem(momento) == "20261021_120859"


class TestCriarBackup:
    def test_nome_e_conteudo(self, origem, backup_dir):
        destino = criar_backup(origem, backup_dir, timestamp="20261021_150859")
        assert destino.name == "README_20261021_150859.bak"
        assert destino.parent == backup_dir
        assert destino.read_text(encoding="utf-8") == "# README v1\n"

    def test_timestamp_automatico(self, origem, backup_dir):
        destino = criar_backup(origem, backup_dir)
        assert re.fullmatch(r"README_\d{8}_\d{6}\.bak", destino.name)

    def test_com_sufixo(self, origem, backup_dir):
        destino = criar_backup(origem, backup_dir, timestamp="20261021_150859", sufixo="pre-restauracao")
        assert destino.name == "README_pre-restauracao_20261021_150859.bak"

    def test_cria_diretorio(self, origem, tmp_path):
        destino = criar_backup(origem, tmp_path / "novo" / "backup", timestamp="20261021_150859")
        assert destino.is_file()

    def test_origem_inexistente(self, backup_dir, tmp_path):
        with pytest.raises(BackupNaoEncontrado):
            criar_backup(tmp_path / "nao_existe.md", backup_dir)


class TestListar:
    def _semear(self, backup_dir):
        backup_dir.mkdir(parents=True, exist_ok=True)
        for ts in ("20260101_000001", "20260101_000002", "20260101_000003"):
            (backup_dir / f"README_{ts}.bak").write_text(ts, encoding="utf-8")
        (backup_dir / "CHANGELOG_20260101_000004.bak").write_text("c", encoding="utf-8")

    def test_ordem_decrescente(self, backup_dir):
        self._semear(backup_dir)
        nomes = [p.name for p in listar_backups(backup_dir)]
        assert nomes[0] == "CHANGELOG_20260101_000004.bak"
        assert nomes[1:] == [
            "README_20260101_000003.bak",
            "README_20260101_000002.bak",
            "README_20260101_000001.bak",
        ]

    def test_filtro_prefixo(self, backup_dir):
        self._semear(backup_dir)
        nomes = [p.name for p in listar_backups(backup_dir, prefixo="README")]
        assert nomes == [
            "README_20260101_000003.bak",
            "README_20260101_000002.bak",
            "README_20260101_000001.bak",
        ]

    def test_diretorio_inexistente(self, tmp_path):
        assert listar_backups(tmp_path / "nao_existe") == []

    def test_ultimo_backup(self, backup_dir):
        self._semear(backup_dir)
        assert ultimo_backup(backup_dir, prefixo="README").name == "README_20260101_000003.bak"

    def test_ultimo_backup_vazio(self, backup_dir):
        assert ultimo_backup(backup_dir) is None


class TestLimparAntigos:
    def _semear(self, backup_dir, total=7):
        backup_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, total + 1):
            (backup_dir / f"README_2026010{i}_000000.bak").write_text(str(i), encoding="utf-8")

    def test_mantem_os_mais_recentes(self, backup_dir):
        self._semear(backup_dir)
        removidos = limpar_antigos(backup_dir, manter=5, prefixo="README")
        assert [p.name for p in removidos] == [
            "README_20260102_000000.bak",
            "README_20260101_000000.bak",
        ]
        assert len(listar_backups(backup_dir)) == 5

    def test_manter_zero(self, backup_dir):
        self._semear(backup_dir)
        assert len(limpar_antigos(backup_dir, manter=0)) == 7

    def test_manter_negativo(self, backup_dir):
        with pytest.raises(BackupError):
            limpar_antigos(backup_dir, manter=-1)


class TestDiff:
    def test_mostra_diferenca(self, origem, backup_dir):
        backup = criar_backup(origem, backup_dir, timestamp="20261021_150859")
        origem.write_text("# README v2\n", encoding="utf-8")
        diff = diff_backup(backup, origem)
        assert "-# README v1" in diff
        assert "+# README v2" in diff

    def test_backup_inexistente(self, origem, backup_dir):
        with pytest.raises(BackupNaoEncontrado):
            diff_backup(backup_dir / "nao.bak", origem)


class TestRestaurar:
    def test_cria_backup_previo_e_restaura(self, origem, backup_dir):
        backup = criar_backup(origem, backup_dir, timestamp="20260101_000001")
        origem.write_text("# README v2\n", encoding="utf-8")
        pre = restaurar_backup(backup, origem, backup_dir, timestamp="20260101_000002")
        assert origem.read_text(encoding="utf-8") == "# README v1\n"
        assert pre.name == "README_pre-restauracao_20260101_000002.bak"
        assert pre.read_text(encoding="utf-8") == "# README v2\n"

    def test_destino_inexistente_nao_cria_previo(self, tmp_path, backup_dir):
        backup = tmp_path / "README_20260101_000001.bak"
        backup.write_text("conteudo", encoding="utf-8")
        destino = tmp_path / "novo" / "README.md"
        pre = restaurar_backup(backup, destino, backup_dir, timestamp="20260101_000002")
        assert pre is None
        assert destino.read_text(encoding="utf-8") == "conteudo"

    def test_backup_inexistente(self, origem, backup_dir):
        with pytest.raises(BackupNaoEncontrado):
            restaurar_backup(backup_dir / "nao.bak", origem, backup_dir)
