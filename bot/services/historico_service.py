"""Serviço de histórico — registro append-only das operações (docs/requisitos.md §2.9).

Grava um objeto JSON por linha (JSONL) em `bot/history/historico.jsonl`, com os campos
`timestamp`, `usuario_id`, `acao`, `secao`, `comunidade`, `antes`, `depois`,
`backup_path` e `commit`. Transparente, versionável e sem dependência extra.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bot.services.tempo import agora_iso

CAMPOS: tuple[str, ...] = (
    "timestamp",
    "usuario_id",
    "acao",
    "secao",
    "comunidade",
    "antes",
    "depois",
    "backup_path",
    "commit",
)


class HistoricoError(Exception):
    """Erro base do serviço de histórico."""


class HistoricoCorrompido(HistoricoError):
    """Uma linha do JSONL não é um objeto JSON válido."""


@dataclass
class RegistroHistorico:
    """Um registro de operação no histórico."""

    acao: str
    timestamp: str = field(default_factory=agora_iso)
    usuario_id: int | None = None
    secao: str | None = None
    comunidade: str | None = None
    antes: str | None = None
    depois: str | None = None
    backup_path: str | None = None
    commit: str | None = None

    def para_dict(self) -> dict:
        """Dicionário com os campos na ordem canônica."""
        dados = asdict(self)
        return {campo: dados[campo] for campo in CAMPOS}

    @classmethod
    def de_dict(cls, dados: dict) -> "RegistroHistorico":
        """Reconstrói o registro a partir de um dicionário (ignora campos extras)."""
        if not dados.get("acao"):
            raise HistoricoCorrompido("registro sem campo 'acao'")
        valores = {campo: dados[campo] for campo in CAMPOS if campo in dados}
        return cls(**valores)


def registrar(caminho: str | Path, registro: RegistroHistorico) -> RegistroHistorico:
    """Anexa um registro ao histórico, criando o arquivo/pasta se necessário."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linha = json.dumps(registro.para_dict(), ensure_ascii=False)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(linha + "\n")
    return registro


def ler_historico(caminho: str | Path) -> list[RegistroHistorico]:
    """Lê todos os registros em ordem cronológica (arquivo ausente → lista vazia)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        return []
    registros: list[RegistroHistorico] = []
    with caminho.open(encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            if not linha.strip():
                continue
            try:
                dados = json.loads(linha)
            except json.JSONDecodeError as erro:
                raise HistoricoCorrompido(f"linha {numero} inválida em {caminho}") from erro
            if not isinstance(dados, dict):
                raise HistoricoCorrompido(f"linha {numero} não é um objeto JSON em {caminho}")
            registros.append(RegistroHistorico.de_dict(dados))
    return registros


def ultimos(caminho: str | Path, n: int) -> list[RegistroHistorico]:
    """Os `n` registros mais recentes, em ordem cronológica."""
    if n <= 0:
        return []
    return ler_historico(caminho)[-n:]


def contar(caminho: str | Path) -> int:
    """Quantidade de registros no histórico."""
    return len(ler_historico(caminho))
