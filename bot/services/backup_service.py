"""Serviço de backup — pré-condição de toda escrita no README (AGENTS.md §2).

Cria cópias `backup/<nome>_YYYYMMDD_HHMMSS.bak` no fuso `America/Belem` e oferece
listagem, limpeza das últimas N sessões, diff e restauração (com backup prévio do
estado atual). Não lê `.env` nem acessa a rede: recebe os caminhos explicitamente,
o que mantém os testes herméticos.
"""

from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

from bot.services.tempo import timestamp_belem

SUFIXO_PRE_RESTAURACAO = "pre-restauracao"

_NOME_RE = re.compile(r"^(?P<stem>.+)_(?P<ts>\d{8}_\d{6})\.bak$")


class BackupError(Exception):
    """Erro base do serviço de backup."""


class BackupNaoEncontrado(BackupError):
    """O arquivo de backup solicitado não existe."""


def _nome_backup(origem: Path, timestamp: str, sufixo: str | None = None) -> str:
    partes = [origem.stem]
    if sufixo:
        partes.append(sufixo)
    partes.append(timestamp)
    return "_".join(partes) + ".bak"


def criar_backup(
    origem: str | Path,
    backup_dir: str | Path,
    timestamp: str | None = None,
    sufixo: str | None = None,
) -> Path:
    """Copia `origem` para `backup_dir` e devolve o caminho do backup.

    Sem `timestamp`, usa o horário atual em `America/Belem`.
    """
    origem = Path(origem)
    if not origem.is_file():
        raise BackupNaoEncontrado(f"arquivo de origem inexistente: {origem}")
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp or timestamp_belem()
    destino = backup_dir / _nome_backup(origem, ts, sufixo)
    shutil.copy2(origem, destino)
    return destino


def _chave_recencia(caminho: Path) -> tuple[str, str]:
    """Chave de ordenação pelo timestamp embutido no nome (fallback: vazio)."""
    m = _NOME_RE.match(caminho.name)
    return (m.group("ts") if m else "", caminho.name)


def listar_backups(backup_dir: str | Path, prefixo: str | None = None) -> list[Path]:
    """Lista os backups (`*.bak`), do mais recente para o mais antigo.

    `prefixo` filtra pelo início do nome (ex.: `"README"`).
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.is_dir():
        return []
    itens = sorted(backup_dir.glob("*.bak"), key=_chave_recencia, reverse=True)
    if prefixo is not None:
        itens = [p for p in itens if p.name.startswith(prefixo)]
    return itens


def ultimo_backup(backup_dir: str | Path, prefixo: str | None = None) -> Path | None:
    """O backup mais recente (ou `None` se não houver)."""
    itens = listar_backups(backup_dir, prefixo)
    return itens[0] if itens else None


def limpar_antigos(
    backup_dir: str | Path,
    manter: int = 5,
    prefixo: str | None = None,
) -> list[Path]:
    """Remove backups além dos `manter` mais recentes; devolve os removidos."""
    if manter < 0:
        raise BackupError("'manter' deve ser >= 0")
    itens = listar_backups(backup_dir, prefixo)
    removidos = itens[manter:]
    for caminho in removidos:
        caminho.unlink()
    return removidos


def diff_backup(backup: str | Path, atual: str | Path) -> str:
    """Diff unificado (`backup` → `atual`) para preview de restauração."""
    backup = Path(backup)
    atual = Path(atual)
    if not backup.is_file():
        raise BackupNaoEncontrado(f"backup inexistente: {backup}")
    if not atual.is_file():
        raise BackupNaoEncontrado(f"arquivo atual inexistente: {atual}")
    antigas = backup.read_text(encoding="utf-8").splitlines(keepends=True)
    novas = atual.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(antigas, novas, fromfile=backup.name, tofile=atual.name)
    )


def restaurar_backup(
    backup: str | Path,
    destino: str | Path,
    backup_dir: str | Path,
    timestamp: str | None = None,
) -> Path | None:
    """Restaura `backup` sobre `destino`, preservando o estado atual antes (AGENTS.md §2.11).

    Cria `backup/<stem>_pre-restauracao_<ts>.bak` do `destino` atual e devolve esse
    caminho (ou `None` se o destino ainda não existia).
    """
    backup = Path(backup)
    if not backup.is_file():
        raise BackupNaoEncontrado(f"backup inexistente: {backup}")
    destino = Path(destino)
    ts = timestamp or timestamp_belem()
    pre_backup: Path | None = None
    if destino.is_file():
        pre_backup = criar_backup(destino, backup_dir, timestamp=ts, sufixo=SUFIXO_PRE_RESTAURACAO)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, destino)
    return pre_backup
