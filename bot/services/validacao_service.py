"""Serviço de validações (docs/requisitos.md §2.8).

Cobre:
- campos obrigatórios e URLs sintaticamente válidas (`http`/`https`/`tg`);
- duplicidade de nome/URL contra o README e contra o fluxo em andamento;
- existência/editabilidade da seção;
- varredura completa do arquivo (`🧩 Validar README`): integridade das tabelas, âncoras da
  navegação × seções, duplicidades, URLs inválidas e coerência do marcador;
- comparação de estrutura antes/depois (garante edição cirúrgica).

Sem rede e sem I/O: opera sobre um `ReadmeDoc` já parseado, mantendo os testes herméticos.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bot.models.comunidade import Comunidade
from bot.services.readme_service import (
    COLUNAS_NAO_EDITAVEIS,
    ReadmeDoc,
    Secao,
    SecaoNaoEncontrada,
    _norm,
)

ERRO = "erro"
AVISO = "aviso"

LIMITE_SIMILARIDADE = 0.85
_ESQUEMA_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


@dataclass
class Problema:
    """Um achado de validação, com severidade e contexto."""

    severidade: str
    codigo: str
    mensagem: str
    secao: str | None = None
    comunidade: str | None = None

    def __str__(self) -> str:
        onde = f" [{self.comunidade or self.secao}]" if (self.comunidade or self.secao) else ""
        return f"{self.severidade.upper()} ({self.codigo}){onde}: {self.mensagem}"


@dataclass
class Relatorio:
    """Coleção de problemas com atalhos por severidade."""

    problemas: list[Problema] = field(default_factory=list)

    @property
    def erros(self) -> list[Problema]:
        return [p for p in self.problemas if p.severidade == ERRO]

    @property
    def avisos(self) -> list[Problema]:
        return [p for p in self.problemas if p.severidade == AVISO]

    @property
    def ok(self) -> bool:
        """True quando não há nenhum erro bloqueante."""
        return not self.erros

    def adicionar(self, problema: Problema) -> None:
        self.problemas.append(problema)

    def __bool__(self) -> bool:
        return self.ok

    def __len__(self) -> int:
        return len(self.problemas)


def normalizar_url(url: str) -> str:
    """Remove todos os espaços e garante um esquema (usa `https` quando ausente)."""
    limpo = "".join(url.split())
    if not limpo:
        return limpo
    if _ESQUEMA_RE.match(limpo):
        return limpo
    return "https://" + limpo


def _norm_url(url: str) -> str:
    return normalizar_url(url).rstrip("/").lower()


def url_valida(url: str) -> bool:
    """Validação sintática: aceita `http`/`https` (domínio) e `tg` (Telegram)."""
    u = normalizar_url(url)
    if not u:
        return False
    partes = urlsplit(u)
    if partes.scheme == "tg":
        return True
    if partes.scheme not in ("http", "https"):
        return False
    host = partes.hostname or ""
    return "." in host


def similares(doc: ReadmeDoc, nome: str, limite: float = LIMITE_SIMILARIDADE) -> list[str]:
    """Nomes de comunidades já no README parecidos com `nome` (exclui o idêntico)."""
    alvo = _norm(nome)
    achados: list[str] = []
    for oc in doc.comunidades():
        outro = oc.comunidade.nome_normalizado()
        if outro == alvo:
            continue
        if difflib.SequenceMatcher(None, alvo, outro).ratio() >= limite:
            achados.append(oc.comunidade.nome)
    return achados


def buscar_por_url(doc: ReadmeDoc, url: str):
    """Localiza a ocorrência que já usa determinada URL (comparação normalizada)."""
    chave = _norm_url(url)
    for oc in doc.comunidades():
        for link in oc.comunidade.links:
            if _norm_url(link.url) == chave:
                return oc
    return None


def validar_secao(doc: ReadmeDoc, nome_secao: str) -> Relatorio:
    """Verifica se a seção existe e aceita comunidades."""
    try:
        secao = doc.encontrar_secao(nome_secao)
    except SecaoNaoEncontrada:
        return Relatorio([Problema(ERRO, "secao_inexistente", f"Seção '{nome_secao}' não encontrada.")])
    if secao.coluna_nome and _norm(secao.coluna_nome) in COLUNAS_NAO_EDITAVEIS:
        return Relatorio(
            [Problema(ERRO, "secao_nao_editavel", f"A seção '{secao.titulo}' não aceita comunidades.")]
        )
    return Relatorio()


def validar_comunidade(
    doc: ReadmeDoc,
    comunidade: Comunidade,
    *,
    ignorar: str | None = None,
    pendentes: Iterable[str] | None = None,
) -> Relatorio:
    """Valida uma comunidade antes de inserir/editar (campos, URL e duplicidade).

    `ignorar` é o nome atual da comunidade em edição (não a acusa de duplicata consigo).
    `pendentes` são nomes já em preparação no fluxo da conversa.
    """
    problemas: list[Problema] = []
    nome = comunidade.nome.strip()
    if not nome:
        problemas.append(Problema(ERRO, "nome_vazio", "O nome da comunidade não pode ser vazio."))
    if not comunidade.links:
        problemas.append(Problema(ERRO, "sem_links", "Informe ao menos 1 link."))

    urls_vistas: set[str] = set()
    for link in comunidade.links:
        if not link.tipo.strip():
            problemas.append(
                Problema(ERRO, "tipo_vazio", "O tipo do link não pode ser vazio.", comunidade=nome)
            )
        if not url_valida(link.url):
            problemas.append(
                Problema(ERRO, "url_invalida", f"URL inválida: {link.url}", comunidade=nome)
            )
        chave = _norm_url(link.url)
        if chave in urls_vistas:
            problemas.append(
                Problema(ERRO, "url_repetida", f"URL repetida: {link.url}", comunidade=nome)
            )
        urls_vistas.add(chave)

    alvo = _norm(nome)
    ignorar_norm = _norm(ignorar) if ignorar else None
    for oc in doc.comunidades():
        outro = oc.comunidade.nome_normalizado()
        if ignorar_norm and outro == ignorar_norm:
            continue
        if outro == alvo:
            problemas.append(
                Problema(
                    ERRO,
                    "nome_duplicado",
                    f"Já existe '{oc.comunidade.nome}' na seção '{oc.secao.nome}'.",
                    secao=oc.secao.nome,
                    comunidade=nome,
                )
            )
        elif difflib.SequenceMatcher(None, alvo, outro).ratio() >= LIMITE_SIMILARIDADE:
            problemas.append(
                Problema(
                    AVISO,
                    "nome_similar",
                    f"Nome similar a '{oc.comunidade.nome}' (seção '{oc.secao.nome}').",
                    secao=oc.secao.nome,
                    comunidade=nome,
                )
            )

    for link in comunidade.links:
        oc = buscar_por_url(doc, link.url)
        if oc is None:
            continue
        if ignorar_norm and oc.comunidade.nome_normalizado() == ignorar_norm:
            continue
        problemas.append(
            Problema(
                ERRO,
                "url_duplicada",
                f"URL já usada por '{oc.comunidade.nome}'.",
                secao=oc.secao.nome,
                comunidade=nome,
            )
        )

    if pendentes:
        pendentes_norm = {_norm(p) for p in pendentes}
        if alvo in pendentes_norm:
            problemas.append(
                Problema(ERRO, "nome_duplicado_fluxo", f"'{nome}' já está pendente no fluxo atual.")
            )

    return Relatorio(problemas)


def _limite_secao(doc: ReadmeDoc, secao: Secao) -> int:
    indice = doc.secoes.index(secao)
    if indice + 1 < len(doc.secoes):
        proxima = doc.secoes[indice + 1]
        return proxima.idx_ancora if proxima.idx_ancora is not None else proxima.idx_titulo
    return len(doc.linhas)


def _colunas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _validar_tabelas(doc: ReadmeDoc) -> list[Problema]:
    problemas: list[Problema] = []
    for secao in doc.secoes:
        if secao.idx_tabela_cabecalho is None:
            continue
        esperado = len(_colunas(doc.linhas[secao.idx_tabela_cabecalho]))
        for i in range(secao.idx_tabela_cabecalho, _limite_secao(doc, secao)):
            linha = doc.linhas[i]
            if not linha.strip().startswith("|"):
                continue
            colunas = len(_colunas(linha))
            if colunas != esperado:
                problemas.append(
                    Problema(
                        ERRO,
                        "tabela_inconsistente",
                        f"Linha {i + 1} da seção '{secao.titulo}' tem {colunas} colunas "
                        f"(esperado {esperado}).",
                        secao=secao.nome,
                    )
                )
    return problemas


def _validar_ancoras(doc: ReadmeDoc) -> list[Problema]:
    ancoras = {secao.ancora for secao in doc.secoes if secao.ancora}
    problemas: list[Problema] = []
    for item in doc.navegacao:
        if item.slug not in ancoras:
            problemas.append(
                Problema(
                    ERRO,
                    "ancora_ausente",
                    f"Navegação aponta para âncora inexistente: #{item.slug} ('{item.texto}').",
                )
            )
    return problemas


def _validar_duplicidades(doc: ReadmeDoc) -> list[Problema]:
    problemas: list[Problema] = []
    vistos_nome: dict[str, str] = {}
    vistos_url: dict[str, str] = {}
    for oc in doc.comunidades():
        chave = oc.comunidade.nome_normalizado()
        if chave in vistos_nome:
            problemas.append(
                Problema(
                    ERRO,
                    "nome_duplicado",
                    f"Nome duplicado: '{oc.comunidade.nome}' nas seções "
                    f"'{vistos_nome[chave]}' e '{oc.secao.nome}'.",
                    secao=oc.secao.nome,
                    comunidade=oc.comunidade.nome,
                )
            )
        else:
            vistos_nome[chave] = oc.secao.nome
        for link in oc.comunidade.links:
            chave_url = _norm_url(link.url)
            if chave_url in vistos_url:
                problemas.append(
                    Problema(
                        ERRO,
                        "url_duplicada",
                        f"URL duplicada: {link.url} ('{vistos_url[chave_url]}' e "
                        f"'{oc.comunidade.nome}').",
                        secao=oc.secao.nome,
                        comunidade=oc.comunidade.nome,
                    )
                )
            else:
                vistos_url[chave_url] = oc.comunidade.nome
    return problemas


def _validar_urls(doc: ReadmeDoc) -> list[Problema]:
    problemas: list[Problema] = []
    for oc in doc.comunidades():
        for link in oc.comunidade.links:
            if not url_valida(link.url):
                problemas.append(
                    Problema(
                        ERRO,
                        "url_invalida",
                        f"URL inválida em '{oc.comunidade.nome}': {link.url}",
                        secao=oc.secao.nome,
                        comunidade=oc.comunidade.nome,
                    )
                )
    return problemas


def _validar_marcador(doc: ReadmeDoc) -> list[Problema]:
    marcadas = [oc.comunidade.nome for oc in doc.comunidades() if oc.marcada]
    if len(marcadas) > 1:
        return [
            Problema(
                ERRO,
                "marcador_multiplo",
                f"Mais de uma comunidade marcada: {', '.join(marcadas)}.",
            )
        ]
    if not marcadas:
        return [Problema(AVISO, "marcador_ausente", "Nenhuma comunidade marcada com o destaque.")]
    return []


def validar_readme(doc: ReadmeDoc) -> Relatorio:
    """Varredura completa do README (`🧩 Validar README`), por severidade."""
    problemas: list[Problema] = []
    problemas += _validar_tabelas(doc)
    problemas += _validar_ancoras(doc)
    problemas += _validar_duplicidades(doc)
    problemas += _validar_urls(doc)
    problemas += _validar_marcador(doc)
    return Relatorio(problemas)


def comparar_estrutura(antes: ReadmeDoc, depois: ReadmeDoc) -> Relatorio:
    """Confere se a edição preservou seções, âncoras e navegação (edição cirúrgica)."""
    problemas: list[Problema] = []
    if antes.listar_secoes() != depois.listar_secoes():
        problemas.append(Problema(ERRO, "secoes_alteradas", "A lista de seções foi alterada."))
    if [item.slug for item in antes.navegacao] != [item.slug for item in depois.navegacao]:
        problemas.append(Problema(ERRO, "navegacao_alterada", "A navegação rápida foi alterada."))
    ancoras_antes = [(secao.nome, secao.ancora) for secao in antes.secoes]
    ancoras_depois = [(secao.nome, secao.ancora) for secao in depois.secoes]
    if ancoras_antes != ancoras_depois:
        problemas.append(Problema(ERRO, "ancoras_alteradas", "Âncoras das seções foram alteradas."))
    return Relatorio(problemas)
