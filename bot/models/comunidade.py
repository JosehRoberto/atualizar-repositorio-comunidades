"""Modelo de domínio da comunidade: nome + links."""

import unicodedata
from dataclasses import dataclass, field


@dataclass
class Link:
    """Um link oficial de uma comunidade (tipo + URL)."""

    tipo: str
    url: str


@dataclass
class Comunidade:
    """Comunidade de tecnologia: nome oficial e links oficiais."""

    nome: str
    links: list[Link] = field(default_factory=list)

    def nome_normalizado(self) -> str:
        """Chave canônica para ordenação/dup: minúsculas, sem acentos e sem espaços extras."""
        base = unicodedata.normalize("NFKD", self.nome)
        sem_acento = "".join(c for c in base if not unicodedata.combining(c))
        return " ".join(sem_acento.lower().split())
