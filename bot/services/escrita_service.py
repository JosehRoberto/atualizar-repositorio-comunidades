"""Serialização de escrita e proteção de sincronização (docs/requisitos.md §2.12).

- **Concorrência:** um `asyncio.Lock` global por arquivo — apenas um fluxo de escrita no
  README por vez; os demais recebem "aguarde, há uma edição em andamento".
- **Sincronização:** `fetch` + `pull --ff-only` antes de gravar; divergência/conflito aborta.
- **Proteção adicional:** hash do README lido no preview é reconferido antes de gravar; se
  mudou, exige novo preview.

Lógica testável sem Telegram; o `GitService` é injetado (mockável nos testes).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from bot.services.git_service import GitError, GitService, hash_arquivo

_lock = asyncio.Lock()

MENSAGEM_OCUPADO = "⏳ Há uma edição em andamento. Aguarde e tente novamente em instantes."
MENSAGEM_HASH_MUDOU = (
    "⚠️ O README mudou desde a pré-visualização. Refaça a operação para ver as mudanças."
)
MENSAGEM_PUBLICACAO_PENDENTE = (
    "⚠️ Há alterações não publicadas. Use /publicar ou /restaurar antes de editar."
)


def lock_escrita() -> asyncio.Lock:
    """Lock global de escrita no README."""
    return _lock


def ocupado() -> bool:
    """True se há uma escrita em andamento."""
    return _lock.locked()


def hash_atual(caminho: str | Path) -> str:
    """Hash SHA-256 do arquivo no estado atual."""
    return hash_arquivo(caminho)


def sincronizar_seguro(servico: GitService) -> str | None:
    """Sincroniza com o remoto (`fetch` + `pull --ff-only`).

    Devolve a mensagem de erro (para abortar) ou ``None`` se tudo certo.
    """
    try:
        servico.sincronizar()
    except GitError as erro:
        return f"⚠️ Não foi possível sincronizar com o remoto: {erro}"
    return None


# ALTERADO [21/10/2026]: sincronização da publicação via rebase (planejamento
# guarda-publicacao-pendente, R1/R2) — permite publicar com o remoto à frente.
def sincronizar_publicacao_seguro(servico: GitService) -> str | None:
    """Sincroniza para publicação (`fetch` + `pull --rebase`).

    Devolve a mensagem de erro (para abortar) ou ``None`` se tudo certo.
    """
    try:
        servico.sincronizar_publicacao()
    except GitError as erro:
        return f"⚠️ Não foi possível sincronizar para publicar: {erro}"
    return None


def conferir_hash(caminho: str | Path, hash_esperado: str | None) -> str | None:
    """Reconfere o hash do arquivo; devolve mensagem de erro se mudou (ou ``None``)."""
    if hash_esperado is None:
        return None
    try:
        atual = hash_arquivo(caminho)
    except FileNotFoundError:
        return "⚠️ O README não foi encontrado no caminho esperado."
    if atual != hash_esperado:
        return MENSAGEM_HASH_MUDOU
    return None
