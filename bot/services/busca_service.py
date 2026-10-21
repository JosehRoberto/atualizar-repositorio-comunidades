"""Busca de comunidades por nome: exata, por substring e fuzzy.

Lógica pura, sem I/O e sem dependência do Telegram. A chave de busca remove
acentos, emojis, pontuação decorativa e colapsa espaços. O `ReadmeDoc.buscar`
continua sendo o caminho exato; este serviço gera candidatos ranqueados para
quando não há correspondência exata (docs/requisitos.md §2.10).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter

from bot.services.readme_service import Ocorrencia, ReadmeDoc

LIMITE_FUZZY = 0.6
MAX_CANDIDATOS = 5

_NAO_ALFANUMERICO = re.compile(r"[^0-9a-z\s]")


def chave_busca(nome: str) -> str:
    """Chave canônica para comparação: sem acentos, emojis e pontuação."""
    base = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in base if not unicodedata.combining(c))
    limpo = _NAO_ALFANUMERICO.sub(" ", sem_acento.lower())
    return " ".join(limpo.split())


def pontuar(termo: str, nome: str) -> float:
    """Similaridade em [0, 2]: 2 para igualdade, com bônus para substring."""
    alvo = chave_busca(termo)
    chave = chave_busca(nome)
    if not alvo or not chave:
        return 0.0
    if alvo == chave:
        return 2.0
    similaridade = difflib.SequenceMatcher(None, alvo, chave).ratio()
    if alvo in chave or chave in alvo:
        return max(similaridade, 0.9)
    tokens_alvo = set(alvo.split())
    tokens_nome = set(chave.split())
    if tokens_alvo:
        cobertura = len(tokens_alvo & tokens_nome) / len(tokens_alvo)
        similaridade = max(similaridade, cobertura * 0.85)
    return similaridade


def candidatos(
    doc: ReadmeDoc,
    termo: str,
    limite: float = LIMITE_FUZZY,
    maximo: int = MAX_CANDIDATOS,
) -> list[Ocorrencia]:
    """Ocorrências similares a `termo`, da mais para a menos parecida."""
    pontuados = []
    for oc in doc.comunidades():
        score = pontuar(termo, oc.comunidade.nome)
        if score >= limite:
            pontuados.append((score, oc))
    pontuados.sort(key=lambda item: (-item[0], item[1].comunidade.nome_normalizado()))
    return [oc for _, oc in pontuados[:maximo]]


def nomes_duplicados(doc: ReadmeDoc) -> set[str]:
    """Chaves normalizadas que aparecem em mais de uma ocorrência."""
    contagem = Counter(oc.comunidade.nome_normalizado() for oc in doc.comunidades())
    return {chave for chave, total in contagem.items() if total > 1}


def rotulo_candidato(ocorrencia: Ocorrencia, duplicados: set[str]) -> str:
    """Nome do candidato; nomes homônimos recebem o primeiro link como desempate."""
    comunidade = ocorrencia.comunidade
    if comunidade.nome_normalizado() in duplicados and comunidade.links:
        return f"{comunidade.nome} — {comunidade.links[0].url}"
    return comunidade.nome
