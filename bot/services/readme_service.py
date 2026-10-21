"""Parser e editor do `README.md` do repositório alvo.

Região protegida (AGENTS.md §3.1): preserva a estrutura e a formatação Markdown
existentes. A edição é cirúrgica — apenas as linhas alvo são reescritas; o restante
do arquivo permanece byte a byte idêntico.

O serviço é puro em relação a I/O: `parse_readme()` recebe o texto e devolve um
`ReadmeDoc`; `render()` devolve o texto. `carregar_readme()` e `salvar_readme()` são
atalhos finos de leitura/escrita (usados com `tmp_path` nos testes).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from bot.models.comunidade import Comunidade, Link

MARCADOR = ":triangular_flag_on_post:"

# Ordem canônica dos badges (docs/requisitos.md §2.4).
ORDEM_BADGES: tuple[str, ...] = (
    "Site",
    "GitHub",
    "GitLab",
    "Instagram",
    "Facebook",
    "LinkedIn",
    "X",
    "YouTube",
    "Meetup",
    "Slack",
    "Discord",
    "Telegram",
    "WhatsApp",
    "LinkTree",
    "Google Drive",
)

# Cor e logo de cada serviço (formato shields.io).
BADGES: dict[str, tuple[str, str]] = {
    "Site": ("4285F4", "googlechrome"),
    "GitHub": ("181717", "github"),
    "GitLab": ("FC6D26", "gitlab"),
    "Instagram": ("E4405F", "instagram"),
    "Facebook": ("1877F2", "facebook"),
    "LinkedIn": ("0A66C2", "linkedin"),
    "X": ("000000", "x"),
    "YouTube": ("FF0000", "youtube"),
    "Meetup": ("ED1C40", "meetup"),
    "Slack": ("4A154B", "slack"),
    "Discord": ("5865F2", "discord"),
    "Telegram": ("2CA5E0", "telegram"),
    "WhatsApp": ("25D366", "whatsapp"),
    "LinkTree": ("43E55E", "linktree"),
    "Google Drive": ("4285F4", "googledrive"),
}

# Fallback para tipos não catalogados ("Outros" e afins).
BADGE_PADRAO: tuple[str, str] = ("808080", "link")

COLUNAS_COMUNIDADE = {"comunidade"}
COLUNAS_NAO_EDITAVEIS = {"servico", "serviço"}

_TITULO_RE = re.compile(r"^##\s+(?P<titulo>.+?)\s*$")
_ANCORA_RE = re.compile(r'^<a\s+name="(?P<slug>[^"]+)"></a>$')
_LINHA_TABELA_RE = re.compile(r"^\s*\|(?P<c1>[^|]*)\|(?P<resto>.*)\|\s*$")
_SEPARADOR_RE = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
_NAV_RE = re.compile(r"^-\s*\[(?P<texto>.+?)\]\(#(?P<slug>[^)]+)\)\s*$")
_A_HREF_RE = re.compile(r'<a\s+href="(?P<url>[^"]+)"\s+title="(?P<tipo>[^"]+)"')


class ReadmeError(Exception):
    """Erro base do serviço de README."""


class SecaoNaoEncontrada(ReadmeError):
    """A seção alvo não existe no README."""


class ComunidadeNaoEncontrada(ReadmeError):
    """A comunidade alvo não foi localizada."""


class SecaoNaoEditavel(ReadmeError):
    """A seção usa schema não editável para comunidades (ex.: Observatório)."""


@dataclass
class NavItem:
    """Item da lista "Navegação Rápida"."""

    texto: str
    slug: str
    idx: int


@dataclass
class Secao:
    """Seção `##` do README com sua âncora e tabela."""

    titulo: str
    emoji: str
    nome: str
    ancora: str | None
    idx_titulo: int
    idx_ancora: int | None
    idx_tabela_cabecalho: int | None = None
    idx_tabela_separador: int | None = None
    coluna_nome: str | None = None


@dataclass
class Ocorrencia:
    """Uma linha de comunidade localizada no README."""

    secao: Secao
    idx: int
    comunidade: Comunidade
    marcada: bool


def _norm(valor: str) -> str:
    """Chave canônica: minúsculas, sem acentos, espaços colapsados."""
    base = unicodedata.normalize("NFKD", valor)
    sem_acento = "".join(c for c in base if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def _separa_emoji(titulo: str) -> tuple[str, str]:
    """Separa o emoji inicial do restante do título (se houver)."""
    partes = titulo.split(" ", 1)
    if len(partes) == 2 and partes[0] and not partes[0][0].isalnum():
        return partes[0], partes[1].strip()
    return "", titulo


def badge_para(tipo: str) -> tuple[str, str]:
    """Cor e logo do badge para um tipo de link."""
    return BADGES.get(tipo, BADGE_PADRAO)


def ordenar_links(links: list[Link]) -> list[Link]:
    """Ordena os links na ordem canônica; tipos desconhecidos preservam a ordem de cadastro."""

    def chave(item: tuple[int, Link]) -> tuple[int, int]:
        i, link = item
        if link.tipo in ORDEM_BADGES:
            return (ORDEM_BADGES.index(link.tipo), i)
        return (len(ORDEM_BADGES), i)

    return [link for _, link in sorted(enumerate(links), key=chave)]


def render_badge(link: Link) -> str:
    """Renderiza um badge no formato shields.io usado pelo README."""
    cor, logo = badge_para(link.tipo)
    rotulo = link.tipo.replace(" ", "%20")
    return (
        f'<a href="{link.url}" title="{link.tipo}">'
        f'<img src="https://img.shields.io/badge/{rotulo}-{cor}?logo={logo}&logoColor=white" '
        f'alt="{link.tipo}"/></a>'
    )


def render_linha(comunidade: Comunidade, marcada: bool = False) -> str:
    """Renderiza a linha de tabela `| **NOME** [marcador] | badges |`."""
    celula = f"**{comunidade.nome}**"
    if marcada:
        celula += f" {MARCADOR}"
    badges = " ".join(render_badge(link) for link in ordenar_links(comunidade.links))
    return f"| {celula} | {badges} |"


def _toggle_marcador(linha: str, marcada: bool) -> str:
    """Adiciona/remove o marcador da linha preservando o restante do conteúdo."""
    tem = MARCADOR in linha
    if marcada == tem:
        return linha
    if not marcada:
        return re.sub(r"\s*" + re.escape(MARCADOR), "", linha, count=1)
    m = re.search(r"\*\*.+?\*\*", linha)
    if not m:
        return linha
    return linha[: m.end()] + f" {MARCADOR}" + linha[m.end():]


def _parse_celula_nome(celula: str) -> tuple[str, bool]:
    """Extrai o nome e o estado do marcador da primeira célula de uma linha."""
    texto = celula.strip()
    marcada = MARCADOR in texto
    texto = texto.replace(MARCADOR, "").strip()
    m = re.match(r"^\*\*(?P<nome>.+?)\*\*$", texto)
    nome = m.group("nome").strip() if m else texto
    return nome, marcada


def _parse_links(resto: str) -> list[Link]:
    """Extrai os links (`href` + `title`) da célula de badges."""
    return [Link(tipo=m.group("tipo"), url=m.group("url")) for m in _A_HREF_RE.finditer(resto)]


def _parse_secoes(linhas: list[str]) -> list[Secao]:
    secoes: list[Secao] = []
    for i, linha in enumerate(linhas):
        m = _TITULO_RE.match(linha)
        if not m:
            continue
        emoji, nome = _separa_emoji(m.group("titulo").strip())
        ancora = None
        idx_ancora = None
        for j in range(i - 1, max(-1, i - 4), -1):
            ma = _ANCORA_RE.match(linhas[j].strip())
            if ma:
                ancora = ma.group("slug")
                idx_ancora = j
                break
            if linhas[j].strip() and not linhas[j].lstrip().startswith(">"):
                break
        secoes.append(
            Secao(
                titulo=m.group("titulo").strip(),
                emoji=emoji,
                nome=nome,
                ancora=ancora,
                idx_titulo=i,
                idx_ancora=idx_ancora,
            )
        )

    for k, secao in enumerate(secoes):
        if k + 1 < len(secoes):
            prox = secoes[k + 1]
            fim = prox.idx_ancora if prox.idx_ancora is not None else prox.idx_titulo
        else:
            fim = len(linhas)
        _detectar_tabela(secao, linhas, secao.idx_titulo + 1, fim)
    return secoes


def _detectar_tabela(secao: Secao, linhas: list[str], inicio: int, fim: int) -> None:
    for i in range(inicio, fim):
        m = _LINHA_TABELA_RE.match(linhas[i])
        if not m:
            continue
        cabecalho = m.group("c1").strip()
        if _norm(cabecalho) not in COLUNAS_COMUNIDADE | COLUNAS_NAO_EDITAVEIS:
            continue
        secao.idx_tabela_cabecalho = i
        secao.coluna_nome = cabecalho
        if i + 1 < len(linhas) and _SEPARADOR_RE.match(linhas[i + 1]):
            secao.idx_tabela_separador = i + 1
        return


def _parse_navegacao(linhas: list[str]) -> list[NavItem]:
    itens: list[NavItem] = []
    dentro = False
    for i, linha in enumerate(linhas):
        m = _TITULO_RE.match(linha)
        if m:
            dentro = "navegacao rapida" in _norm(m.group("titulo"))
            continue
        if not dentro:
            continue
        mn = _NAV_RE.match(linha.strip())
        if mn:
            itens.append(NavItem(texto=mn.group("texto"), slug=mn.group("slug"), idx=i))
        elif linha.strip() and not linha.lstrip().startswith("-"):
            dentro = False
    return itens


class ReadmeDoc:
    """Representação editável do README, preservando as linhas originais."""

    def __init__(self, texto: str):
        self.linhas: list[str] = texto.split("\n")
        self.secoes: list[Secao] = []
        self.navegacao: list[NavItem] = []
        self._recalcular_estrutura()

    def _recalcular_estrutura(self) -> None:
        self.secoes = _parse_secoes(self.linhas)
        self.navegacao = _parse_navegacao(self.linhas)

    def render(self) -> str:
        """Devolve o texto do README."""
        return "\n".join(self.linhas)

    def listar_secoes(self) -> list[str]:
        """Títulos (`## ...`) de todas as seções."""
        return [secao.titulo for secao in self.secoes]

    def _fim_da_secao(self, secao: Secao) -> int:
        i = self.secoes.index(secao)
        if i + 1 < len(self.secoes):
            prox = self.secoes[i + 1]
            return prox.idx_ancora if prox.idx_ancora is not None else prox.idx_titulo
        return len(self.linhas)

    def _ocorrencias_da_secao(self, secao: Secao) -> list[Ocorrencia]:
        ocorrencias: list[Ocorrencia] = []
        for i in range(secao.idx_titulo + 1, self._fim_da_secao(secao)):
            m = _LINHA_TABELA_RE.match(self.linhas[i])
            if not m or "**" not in m.group("c1"):
                continue
            nome, marcada = _parse_celula_nome(m.group("c1"))
            ocorrencias.append(
                Ocorrencia(
                    secao=secao,
                    idx=i,
                    comunidade=Comunidade(nome=nome, links=_parse_links(m.group("resto"))),
                    marcada=marcada,
                )
            )
        return ocorrencias

    def comunidades(self) -> list[Ocorrencia]:
        """Todas as comunidades (linhas `| **Nome** | ... |`) do README."""
        resultado: list[Ocorrencia] = []
        for secao in self.secoes:
            resultado.extend(self._ocorrencias_da_secao(secao))
        return resultado

    def _secao_corresponde(self, secao: Secao, alvo: str) -> bool:
        return _norm(secao.nome) == _norm(alvo) or _norm(secao.titulo) == _norm(alvo)

    def encontrar_secao(self, alvo: str) -> Secao:
        """Localiza uma seção pelo nome ou título (normalizados)."""
        for secao in self.secoes:
            if self._secao_corresponde(secao, alvo):
                return secao
        raise SecaoNaoEncontrada(alvo)

    def buscar(self, nome: str, secao_alvo: str | None = None) -> Ocorrencia | None:
        """Localiza a comunidade pelo nome normalizado (exato)."""
        alvo = _norm(nome)
        for oc in self.comunidades():
            if oc.comunidade.nome_normalizado() != alvo:
                continue
            if secao_alvo is not None and not self._secao_corresponde(oc.secao, secao_alvo):
                continue
            return oc
        return None

    def _garantir_tabela(self, secao: Secao) -> None:
        if secao.idx_tabela_separador is not None:
            return
        idx = secao.idx_titulo + 1
        while idx < len(self.linhas) and (
            not self.linhas[idx].strip() or self.linhas[idx].lstrip().startswith(">")
        ):
            idx += 1
        coluna = secao.coluna_nome or "Comunidade"
        self.linhas[idx:idx] = [f"| {coluna} | Links |", "|---|---|"]
        self._recalcular_estrutura()

    def _indice_insercao(self, secao: Secao, nome_norm: str) -> int:
        ocorrencias = self._ocorrencias_da_secao(secao)
        for oc in ocorrencias:
            if nome_norm < oc.comunidade.nome_normalizado():
                return oc.idx
        if ocorrencias:
            return ocorrencias[-1].idx + 1
        if secao.idx_tabela_separador is not None:
            return secao.idx_tabela_separador + 1
        return secao.idx_titulo + 1

    def _remover_marcadores(self) -> None:
        for oc in self.comunidades():
            self.linhas[oc.idx] = _toggle_marcador(self.linhas[oc.idx], False)

    def inserir(self, secao_alvo: str, comunidade: Comunidade, marcar: bool = True) -> None:
        """Insere a comunidade na seção, em ordem alfabética.

        Com `marcar=True` (padrão), o marcador migra para a nova comunidade — a que
        o possuía antes perde o marcador (docs/requisitos.md §2.5).
        """
        secao = self.encontrar_secao(secao_alvo)
        if secao.coluna_nome and _norm(secao.coluna_nome) in COLUNAS_NAO_EDITAVEIS:
            raise SecaoNaoEditavel(secao.titulo)
        self._garantir_tabela(secao)
        secao = self.encontrar_secao(secao_alvo)
        if marcar:
            self._remover_marcadores()
        idx = self._indice_insercao(secao, comunidade.nome_normalizado())
        self.linhas.insert(idx, render_linha(comunidade, marcada=marcar))
        self._recalcular_estrutura()

    def editar(self, nome: str, nova: Comunidade, secao_alvo: str | None = None) -> None:
        """Substitui os dados de uma comunidade, preservando o marcador atual."""
        oc = self.buscar(nome, secao_alvo)
        if oc is None:
            raise ComunidadeNaoEncontrada(nome)
        linha = render_linha(nova, marcada=oc.marcada)
        if nova.nome_normalizado() == oc.comunidade.nome_normalizado():
            self.linhas[oc.idx] = linha
            self._recalcular_estrutura()
            return
        secao_nome = oc.secao.nome
        del self.linhas[oc.idx]
        self._recalcular_estrutura()
        secao = self.encontrar_secao(secao_nome)
        idx = self._indice_insercao(secao, nova.nome_normalizado())
        self.linhas.insert(idx, linha)
        self._recalcular_estrutura()

    def remover(self, nome: str, secao_alvo: str | None = None) -> None:
        """Remove a linha da comunidade."""
        oc = self.buscar(nome, secao_alvo)
        if oc is None:
            raise ComunidadeNaoEncontrada(nome)
        del self.linhas[oc.idx]
        self._recalcular_estrutura()

    def normalizar_marcador(self, nome_referencia: str = "Divas Digitais") -> None:
        """Garante no máximo 1 marcador, atribuindo-o à comunidade de referência."""
        ocorrencias = self.comunidades()
        ref = _norm(nome_referencia)
        if not any(oc.comunidade.nome_normalizado() == ref for oc in ocorrencias):
            raise ComunidadeNaoEncontrada(nome_referencia)
        for oc in ocorrencias:
            desejada = oc.comunidade.nome_normalizado() == ref
            self.linhas[oc.idx] = _toggle_marcador(self.linhas[oc.idx], desejada)


def parse_readme(texto: str) -> ReadmeDoc:
    """Analisa o texto do README e devolve um documento editável."""
    return ReadmeDoc(texto)


def carregar_readme(caminho: str | Path) -> ReadmeDoc:
    """Lê o README do disco e devolve o documento editável."""
    return ReadmeDoc(Path(caminho).read_text(encoding="utf-8"))


def salvar_readme(doc: ReadmeDoc, caminho: str | Path) -> None:
    """Grava o documento no disco (UTF-8). O backup é responsabilidade do chamador."""
    Path(caminho).write_text(doc.render(), encoding="utf-8")
