"""Máquina de estados do fluxo conversacional (ordem dos estados).

Define os estados, a ação em andamento e o rascunho por usuário, além da ordem
de transição de cada fluxo (nova/editar/remover). É lógica pura — sem I/O e sem
dependência do Telegram —, o que mantém os testes herméticos. Os handlers do
Telegram (`bot/handlers/menu.py`) consomem esta API.

Região protegida (AGENTS.md §3.1): ao alterar a ordem dos estados, registre o
comentário ``# ALTERADO [data]: ...``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from bot.models.comunidade import Comunidade


class EstadoConversa(Enum):
    """Estados possíveis de uma conversa com o bot."""

    IDLE = "idle"
    # Nova comunidade
    NOVA_NOME = "nova_nome"
    NOVA_LINKS = "nova_links"
    NOVA_SECAO = "nova_secao"
    # ALTERADO [21/10/2026]: estados de candidatos para busca fuzzy (§2.10).
    # Editar comunidade
    EDITAR_NOME = "editar_nome"
    EDITAR_CANDIDATOS = "editar_candidatos"
    # ALTERADO [21/10/2026]: desvio opcional — seleção por lista (seções/comunidades).
    EDITAR_LISTA = "editar_lista"
    EDITAR_ESCOLHA = "editar_escolha"
    EDITAR_NOVO_NOME = "editar_novo_nome"
    EDITAR_LINKS = "editar_links"
    # ALTERADO [21/10/2026]: desvio opcional — gerenciador de links (valor/remoção).
    LINK_VALOR = "link_valor"
    LINK_REMOCAO_CONFIRMACAO = "link_remocao_confirmacao"
    # Remover comunidade
    REMOVER_NOME = "remover_nome"
    REMOVER_CANDIDATOS = "remover_candidatos"
    REMOVER_CONFIRMACAO = "remover_confirmacao"
    # Buscar comunidade
    BUSCAR_NOME = "buscar_nome"
    # Publicação
    PUBLICAR_CONFIRMACAO = "publicar_confirmacao"
    # Restauração de backup
    RESTAURAR_ESCOLHA = "restaurar_escolha"
    RESTAURAR_CONFIRMACAO = "restaurar_confirmacao"
    # Comuns a nova/editar
    PREVIEW = "preview"
    APROVACAO = "aprovacao"


class Acao(Enum):
    """Ação do menu em andamento."""

    NOVA = "nova"
    EDITAR = "editar"
    REMOVER = "remover"
    BUSCAR = "buscar"
    PUBLICAR = "publicar"
    RESTAURAR = "restaurar"


# Escolha do que editar no estado EDITAR_ESCOLHA.
CAMPO_NOME = "nome"
CAMPO_LINKS = "links"
CAMPO_AMBOS = "ambos"

# Ordem canônica dos estados por ação (PREVIEW/APROVACAO são comuns a nova/editar).
ORDEM_POR_ACAO: dict[Acao, list[EstadoConversa]] = {
    Acao.NOVA: [
        EstadoConversa.NOVA_NOME,
        EstadoConversa.NOVA_LINKS,
        EstadoConversa.NOVA_SECAO,
        EstadoConversa.PREVIEW,
        EstadoConversa.APROVACAO,
    ],
    Acao.EDITAR: [
        EstadoConversa.EDITAR_NOME,
        EstadoConversa.EDITAR_CANDIDATOS,
        EstadoConversa.EDITAR_LISTA,
        EstadoConversa.EDITAR_ESCOLHA,
        EstadoConversa.EDITAR_NOVO_NOME,
        EstadoConversa.EDITAR_LINKS,
        EstadoConversa.LINK_VALOR,
        EstadoConversa.LINK_REMOCAO_CONFIRMACAO,
        EstadoConversa.PREVIEW,
        EstadoConversa.APROVACAO,
    ],
    Acao.REMOVER: [
        EstadoConversa.REMOVER_NOME,
        EstadoConversa.REMOVER_CANDIDATOS,
        EstadoConversa.REMOVER_CONFIRMACAO,
    ],
    Acao.BUSCAR: [EstadoConversa.BUSCAR_NOME],
    Acao.PUBLICAR: [EstadoConversa.PUBLICAR_CONFIRMACAO],
    Acao.RESTAURAR: [
        EstadoConversa.RESTAURAR_ESCOLHA,
        EstadoConversa.RESTAURAR_CONFIRMACAO,
    ],
}


@dataclass
class ConversaUsuario:
    """Rascunho e posição no fluxo de um usuário."""

    user_id: int
    estado: EstadoConversa = EstadoConversa.IDLE
    acao: Acao | None = None
    rascunho: Comunidade | None = None
    nome_original: str | None = None
    secao_alvo: str | None = None
    campo_editar: str | None = None
    candidatos: list[tuple[str, str, str]] = field(default_factory=list)
    link_indice: int | None = None
    link_tipo: str | None = None
    backup_escolhido: str | None = None
    hash_base: str | None = None
    iniciada_em: datetime | None = None

    def ativa(self) -> bool:
        """True se há uma ação em andamento."""
        return self.acao is not None and self.estado is not EstadoConversa.IDLE

    def reset(self) -> None:
        """Volta a conversa ao estado ocioso, limpando o rascunho."""
        self.estado = EstadoConversa.IDLE
        self.acao = None
        self.rascunho = None
        self.nome_original = None
        self.secao_alvo = None
        self.campo_editar = None
        self.candidatos = []
        self.link_indice = None
        self.link_tipo = None
        self.backup_escolhido = None
        self.hash_base = None
        self.iniciada_em = None


class GerenciadorEstado:
    """Guarda uma `ConversaUsuario` por usuário e calcula a ordem dos estados."""

    def __init__(self) -> None:
        self.conversas: dict[int, ConversaUsuario] = {}

    def obter(self, user_id: int) -> ConversaUsuario:
        """Retorna (criando se preciso) a conversa do usuário."""
        if user_id not in self.conversas:
            self.conversas[user_id] = ConversaUsuario(user_id=user_id)
        return self.conversas[user_id]

    def iniciar(
        self, user_id: int, acao: Acao, rascunho: Comunidade | None = None
    ) -> ConversaUsuario:
        """Reinicia a conversa do usuário no primeiro estado da ação."""
        conversa = self.obter(user_id)
        conversa.reset()
        conversa.acao = acao
        conversa.rascunho = rascunho
        conversa.iniciada_em = datetime.now()
        conversa.estado = ORDEM_POR_ACAO[acao][0]
        return conversa

    def encerrar(self, user_id: int) -> None:
        """Encerra a conversa, voltando ao estado ocioso."""
        self.obter(user_id).reset()

    def proximo_estado(self, conversa: ConversaUsuario) -> EstadoConversa | None:
        """Próximo estado na ordem da ação; ``None`` quando o fluxo termina.

        O fluxo de edição ramifica em `EDITAR_ESCOLHA` conforme `campo_editar`:
        - ``nome``  → ``EDITAR_NOVO_NOME`` → ``PREVIEW``
        - ``links`` → ``EDITAR_LINKS`` → ``PREVIEW``
        - ``ambos`` → ``EDITAR_NOVO_NOME`` → ``EDITAR_LINKS`` → ``PREVIEW``
        """
        if conversa.acao is None:
            return None
        ordem = ORDEM_POR_ACAO[conversa.acao]
        if conversa.estado not in ordem:
            return None

        if conversa.acao is Acao.EDITAR:
            # ALTERADO [21/10/2026]: candidatos são um desvio opcional da busca fuzzy.
            if conversa.estado is EstadoConversa.EDITAR_NOME:
                return EstadoConversa.EDITAR_ESCOLHA
            if conversa.estado is EstadoConversa.EDITAR_ESCOLHA:
                if conversa.campo_editar == CAMPO_LINKS:
                    return EstadoConversa.EDITAR_LINKS
                return EstadoConversa.EDITAR_NOVO_NOME
            if conversa.estado is EstadoConversa.EDITAR_NOVO_NOME:
                if conversa.campo_editar == CAMPO_AMBOS:
                    return EstadoConversa.EDITAR_LINKS
                return EstadoConversa.PREVIEW
            # ALTERADO [21/10/2026]: gerenciador de links é desvio opcional.
            if conversa.estado is EstadoConversa.EDITAR_LINKS:
                return EstadoConversa.PREVIEW
            if conversa.estado in (
                EstadoConversa.LINK_VALOR,
                EstadoConversa.LINK_REMOCAO_CONFIRMACAO,
            ):
                return EstadoConversa.EDITAR_LINKS

        if conversa.acao is Acao.REMOVER and conversa.estado is EstadoConversa.REMOVER_NOME:
            return EstadoConversa.REMOVER_CONFIRMACAO

        indice = ordem.index(conversa.estado)
        if indice + 1 < len(ordem):
            return ordem[indice + 1]
        return None


# Instância única usada pelos handlers.
gerenciador = GerenciadorEstado()
