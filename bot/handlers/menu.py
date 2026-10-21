"""Handlers do menu e dos fluxos conversacionais (nova/buscar/editar/remover/listar).

Consome a máquina de estados (`bot/handlers/state_manager.py`) e os serviços de
domínio (`readme_service`, `backup_service`, `historico_service`, `validacao_service`).
O preview é mostrado antes de gravar e a decisão usa os botões ``✅`` / ``✏️`` / ``🔀`` / ``❌``.

Os helpers de texto/parse são puros (testáveis de forma hermética); os handlers
falam com o Telegram.
"""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.helpers import escape_markdown
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import Config
from bot.handlers import publicacao
from bot.handlers.state_manager import (
    CAMPO_AMBOS,
    CAMPO_LINKS,
    CAMPO_NOME,
    Acao,
    EstadoConversa,
    gerenciador,
)
from bot.models.comunidade import Comunidade, Link
from bot.services import backup_service, busca_service, escrita_service, historico_service, link_template
from bot.services.git_service import GitError, GitService
from bot.services.readme_service import (
    ORDEM_BADGES,
    ComunidadeNaoEncontrada,
    SecaoNaoEditavel,
    SecaoNaoEncontrada,
    carregar_readme,
    render_linha,
    salvar_readme,
)
from bot.services.tempo import timestamp_belem
from bot.services.validacao_service import validar_comunidade, validar_readme

logger = logging.getLogger(__name__)

# Callback data do preview/aprovação.
CB_OK = "aprov_ok"
CB_EDITAR = "aprov_editar"
CB_SECAO = "aprov_secao"
CB_CANCELAR = "aprov_cancelar"
PADRAO_APROVACAO = f"^({CB_OK}|{CB_EDITAR}|{CB_SECAO}|{CB_CANCELAR})$"
PADRAO_CANDIDATOS_EDITAR = r"^edit_cand_(\d+)$"
PADRAO_CANDIDATOS_REMOVER = r"^rem_cand_(\d+)$"
# ALTERADO [21/10/2026]: seleção por lista (seções/comunidades) no /editar.
PADRAO_LISTAR = "^edit_listar$"
PADRAO_SECAO_LISTA = r"^edit_sec_(\d+)$"
PADRAO_LISTA_PAGINA = r"^edit_lista_pg_(\d+)$"
PADRAO_LISTA_VOLTAR = "^edit_lista_voltar$"
PADRAO_LISTA_CANDIDATO = r"^edit_lst_(\d+)$"
CB_LISTAR = "edit_listar"
CB_LISTA_VOLTAR = "edit_lista_voltar"
LIMITE_LISTA = 8
# ALTERADO [21/10/2026]: gerenciador de links por botões no /editar.
PADRAO_LINK_ABRIR = r"^edit_lk_(\d+)$"
PADRAO_LINK_ALTERAR = r"^edit_lk_set_(\d+)$"
PADRAO_LINK_REMOVER = r"^edit_lk_rm_(\d+)$"
PADRAO_LINK_ADICIONAR = "^edit_lk_add$"
PADRAO_LINK_TIPO = r"^edit_lk_tp_(\d+)$"
PADRAO_LINK_CONCLUIR = "^edit_lk_ok$"
PADRAO_LINK_VOLTAR = "^edit_lk_back$"
PADRAO_LINK_REMOCAO = "^edit_lk_rm(ok|no)$"
CB_LINK_VOLTAR = "edit_lk_back"
TIPOS_LINK = (*ORDEM_BADGES, "Outros")

PRONTO = "pronto"

PERGUNTA_NOVA_NOME = "➕ Qual é o *nome* da nova comunidade?"
PERGUNTA_NOVA_LINKS = (
    "🔗 Envie os *links* no formato `<Tipo> <URL>`, um por linha.\n"
    "Ex.: `Instagram https://instagram.com/exemplo`\n"
    "Quando terminar, envie *pronto*."
)
PERGUNTA_NOVA_SECAO = "📚 Em qual *seção* inserir? Envie o número da lista."
PERGUNTA_EDITAR_NOME = "✏️ Qual comunidade você quer editar? (nome)"
PERGUNTA_EDITAR_NOVO_NOME = "✏️ Qual é o *novo nome*?"
PERGUNTA_EDITAR_LINKS = (
    "🔗 Envie os *novos links* no formato `<Tipo> <URL>`, um por linha.\n"
    "Quando terminar, envie *pronto*."
)
PERGUNTA_REMOVER_NOME = "🗑️ Qual comunidade você quer remover? (nome)"
PERGUNTA_BUSCAR_NOME = "🔍 Qual comunidade você quer buscar? (nome)"


def _autorizado(update: Update) -> bool:
    """True se o usuário está na lista de autorizados (ou lista vazia em dev)."""
    user = update.effective_user
    if user is None:
        return False
    if not Config.TELEGRAM_ALLOWED_USER_IDS:
        return True
    return user.id in Config.TELEGRAM_ALLOWED_USER_IDS


# ALTERADO [21/10/2026]: guarda de edição com publicação pendente
# (planejamento guarda-publicacao-pendente, R3/R4/R10).
def _publicacao_pendente() -> str | None:
    """Mensagem se houver edição não publicada no README; ``None`` se a árvore estiver limpa."""
    try:
        if GitService.from_config().readme_pendente(Config.README_PATH):
            return escrita_service.MENSAGEM_PUBLICACAO_PENDENTE
    except GitError as erro:
        return f"⚠️ Não foi possível inspecionar o repositório: {erro}"
    return None


def _chat_id(update: Update) -> int:
    if update.callback_query is not None:
        return update.callback_query.message.chat_id
    return update.message.chat_id


def _mensagem(update: Update):
    """Mensagem de resposta, seja atualização por texto ou por callback."""
    if update.callback_query is not None:
        return update.callback_query.message
    return update.message


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------


def _md(texto) -> str:
    """Escapa texto dinâmico para Markdown legado (v1) do Telegram."""
    return escape_markdown(str(texto), version=1)


def parse_links(texto: str) -> tuple[list[Link], list[str]]:
    """Converte linhas ``<Tipo> <URL>`` em `Link`s; devolve (links, linhas_invalidas)."""
    links: list[Link] = []
    invalidas: list[str] = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if ":" in linha.split("http")[0] and "://" not in linha.split(":")[0]:
            tipo, _, url = linha.partition(":")
        else:
            partes = linha.split(None, 1)
            if len(partes) < 2:
                invalidas.append(linha)
                continue
            tipo, url = partes
        tipo = tipo.strip(" :")
        url = url.strip()
        if not tipo or not url:
            invalidas.append(linha)
            continue
        links.append(Link(tipo, url))
    return links, invalidas


def linhas_para_texto(links: list[Link]) -> str:
    """Renderiza links como linhas ``Tipo URL`` (entrada de edição)."""
    return "\n".join(f"{link.tipo} {link.url}" for link in links)


def lista_secoes_editaveis(doc) -> list[str]:
    """Nomes das seções que aceitam comunidades (exclui Observatório)."""
    return [secao.nome for secao in doc.secoes if secao.coluna_nome not in (None, "Serviço")]


def texto_lista_secoes(doc) -> str:
    """Lista numerada de seções editáveis para o usuário escolher."""
    nomes = lista_secoes_editaveis(doc)
    linhas = ["📚 *Seções disponíveis:*"]
    linhas += [f"{i}. {_md(nome)}" for i, nome in enumerate(nomes, start=1)]
    linhas.append("\nEnvie o *número* correspondente.")
    return "\n".join(linhas)


def resolver_secao(doc, escolha: str) -> str | None:
    """Resolve a escolha do usuário (número ou nome) para o nome de uma seção."""
    escolha = escolha.strip()
    nomes = lista_secoes_editaveis(doc)
    if escolha.isdigit():
        indice = int(escolha)
        if 1 <= indice <= len(nomes):
            return nomes[indice - 1]
        return None
    alvo = " ".join(escolha.lower().split())
    for nome in nomes:
        if " ".join(nome.lower().split()) == alvo:
            return nome
    return None


def teclado_aprovacao() -> InlineKeyboardMarkup:
    """Teclado de preview/aprovação: ✅ aplicar, ✏️ editar, 🔀 seção, ❌ cancelar."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Aplicar", callback_data=CB_OK),
                InlineKeyboardButton("✏️ Editar", callback_data=CB_EDITAR),
            ],
            [
                InlineKeyboardButton("🔀 Trocar seção", callback_data=CB_SECAO),
                InlineKeyboardButton("❌ Cancelar", callback_data=CB_CANCELAR),
            ],
        ]
    )


def teclado_candidatos(rotulos: list[str], prefixo: str) -> InlineKeyboardMarkup:
    """Teclado numerado de candidatos; o callback carrega o índice do candidato."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{i}. {rotulo}", callback_data=f"{prefixo}_{i - 1}")]
            for i, rotulo in enumerate(rotulos, start=1)
        ]
    )


def texto_candidatos(rotulos: list[str], verbo: str) -> str:
    """Mensagem com a lista numerada de candidatos similares."""
    linhas = [f"🔍 Não encontrei exatamente. Selecione a comunidade que deseja {verbo}:"]
    linhas += [f"{i}. {rotulo}" for i, rotulo in enumerate(rotulos, start=1)]
    return "\n".join(linhas)


# ALTERADO [21/10/2026]: teclados/texto da seleção por lista (seções → comunidades).
def teclado_secoes(secoes: list[str]) -> InlineKeyboardMarkup:
    """Teclado com as seções editáveis; o callback carrega o índice da seção."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(nome, callback_data=f"edit_sec_{i}")] for i, nome in enumerate(secoes)]
    )


def teclado_lista(rotulos: list[str], pagina: int) -> InlineKeyboardMarkup:
    """Teclado paginado das comunidades de uma seção (índice absoluto no callback)."""
    inicio = pagina * LIMITE_LISTA
    fatia = rotulos[inicio:inicio + LIMITE_LISTA]
    linhas = [
        [InlineKeyboardButton(f"{inicio + i + 1}. {rotulo}", callback_data=f"edit_lst_{inicio + i}")]
        for i, rotulo in enumerate(fatia)
    ]
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"edit_lista_pg_{pagina - 1}"))
    if inicio + LIMITE_LISTA < len(rotulos):
        nav.append(InlineKeyboardButton("➡️ Próxima", callback_data=f"edit_lista_pg_{pagina + 1}"))
    nav.append(InlineKeyboardButton("↩️ Seções", callback_data=CB_LISTA_VOLTAR))
    linhas.append(nav)
    return InlineKeyboardMarkup(linhas)


def texto_lista(secao: str, pagina: int, total_paginas: int) -> str:
    """Mensagem com o cabeçalho da seção e a página atual."""
    linhas = [
        f"📋 *{_md(secao)}* — página {pagina + 1}/{total_paginas}",
        "Selecione a comunidade que deseja editar:",
    ]
    return "\n".join(linhas)


# ALTERADO [21/10/2026]: textos/teclados do gerenciador de links.
def texto_menu_links(conversa) -> str:
    """Cabeçalho do gerenciador de links com a lista atual."""
    nome = conversa.rascunho.nome if conversa.rascunho else ""
    linhas = [f"🔗 *Links* de *{_md(nome)}*:"]
    for i, link in enumerate(conversa.rascunho.links, start=1):
        linhas.append(f"{i}. {_md(link.tipo)} — {_md(link.url)}")
    if not conversa.rascunho.links:
        linhas.append("_(nenhum link — adicione ao menos 1)_")
    return "\n".join(linhas)


def teclado_links(links: list[Link]) -> InlineKeyboardMarkup:
    """Teclado do menu de links: um botão por link + adicionar/concluir."""
    linhas = [
        [InlineKeyboardButton(f"{i}. {link.tipo}", callback_data=f"edit_lk_{i - 1}")]
        for i, link in enumerate(links, start=1)
    ]
    linhas.append(
        [
            InlineKeyboardButton("➕ Adicionar link", callback_data="edit_lk_add"),
            InlineKeyboardButton("✅ Concluir", callback_data="edit_lk_ok"),
        ]
    )
    return InlineKeyboardMarkup(linhas)


def teclado_link_item(indice: int) -> InlineKeyboardMarkup:
    """Submenu de um link: alterar valor / remover / voltar."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Alterar valor", callback_data=f"edit_lk_set_{indice}"),
                InlineKeyboardButton("🗑️ Remover", callback_data=f"edit_lk_rm_{indice}"),
            ],
            [InlineKeyboardButton("↩️ Voltar", callback_data=CB_LINK_VOLTAR)],
        ]
    )


def teclado_tipos() -> InlineKeyboardMarkup:
    """Catálogo de tipos para adicionar um link."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tipo, callback_data=f"edit_lk_tp_{i}")]
            for i, tipo in enumerate(TIPOS_LINK)
        ]
    )


def texto_preview(conversa, secao: str) -> str:
    """Mensagem de pré-visualização antes de gravar."""
    comunidade = conversa.rascunho
    titulo = "nova comunidade" if conversa.acao is Acao.NOVA else "edição"
    linhas = [f"👀 *Pré-visualização* — {titulo}\n"]
    # ALTERADO [21/10/2026]: escapa nome/seção (fix Can't parse entities)
    linhas.append(f"*Nome:* {_md(comunidade.nome)}")
    linhas.append(f"*Seção:* {_md(secao)}")
    linhas.append("*Linha no README:*")
    linhas.append(f"`{render_linha(comunidade, marcada=True)}`")
    linhas.append("")
    linhas.append("Confirme com os botões abaixo.")
    return "\n".join(linhas)


def texto_resumo_comunidade(comunidade: Comunidade) -> str:
    """Resumo em texto de uma comunidade (para listar/buscar)."""
    links = ", ".join(f"{_md(link.tipo)} ({_md(link.url)})" for link in comunidade.links) or "sem links"
    return f"• *{_md(comunidade.nome)}* — {links}"


# ---------------------------------------------------------------------------
# Aplicação da alteração (regra de negócio + persistência)
# ---------------------------------------------------------------------------


def aplicar_no_doc(doc, conversa) -> str:
    """Aplica a alteração da conversa no documento; devolve um resumo textual."""
    acao = conversa.acao
    comunidade = conversa.rascunho
    if acao is Acao.NOVA:
        doc.inserir(conversa.secao_alvo, comunidade, marcar=True)
        return f"✅ Inserida *{_md(comunidade.nome)}* em *{_md(conversa.secao_alvo)}*."
    if acao is Acao.EDITAR:
        doc.editar(conversa.nome_original, comunidade)
        return f"✅ Editada *{_md(comunidade.nome)}*."
    if acao is Acao.REMOVER:
        doc.remover(conversa.nome_original)
        return f"✅ Removida *{_md(conversa.nome_original)}*."
    raise ValueError(f"ação inválida: {acao}")


def persistir(
    doc,
    *,
    caminho: str | Path,
    backup_dir: str | Path,
    historico_path: str | Path,
    usuario_id: int,
    conversa,
    resumo: str,
) -> Path:
    """Backup → grava o README → registra no histórico (AGENTS.md §2)."""
    caminho = Path(caminho)
    antes = caminho.read_text(encoding="utf-8") if caminho.is_file() else ""
    ts = timestamp_belem()
    backup = backup_service.criar_backup(caminho, backup_dir, timestamp=ts)
    salvar_readme(doc, caminho)
    depois = caminho.read_text(encoding="utf-8")
    historico_service.registrar(
        historico_path,
        historico_service.RegistroHistorico(
            acao=conversa.acao.value,
            usuario_id=usuario_id,
            secao=conversa.secao_alvo,
            comunidade=(conversa.rascunho.nome if conversa.rascunho else conversa.nome_original),
            antes=antes,
            depois=depois,
            backup_path=str(backup),
        ),
    )
    return backup


# ---------------------------------------------------------------------------
# Helpers de Telegram
# ---------------------------------------------------------------------------


async def _responder(update: Update, texto: str, **kwargs) -> None:
    if update.callback_query is not None:
        await update.callback_query.message.reply_text(texto, **kwargs)
    else:
        await update.message.reply_text(texto, **kwargs)


async def _enviar_preview(update: Update, conversa) -> EstadoConversa:
    """Envia o preview com o teclado de aprovação e avança o estado."""
    conversa.hash_base = escrita_service.hash_atual(Config.README_PATH)
    conversa.estado = EstadoConversa.APROVACAO
    await _responder(
        update,
        texto_preview(conversa, conversa.secao_alvo),
        parse_mode="Markdown",
        reply_markup=teclado_aprovacao(),
    )
    return EstadoConversa.APROVACAO


# ---------------------------------------------------------------------------
# Fluxo: NOVA
# ---------------------------------------------------------------------------


async def cmd_nova(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia o fluxo de nova comunidade."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    pendente = _publicacao_pendente()
    if pendente:
        await update.message.reply_text(pendente)
        return ConversationHandler.END
    gerenciador.iniciar(update.effective_user.id, Acao.NOVA)
    await update.message.reply_text(PERGUNTA_NOVA_NOME)
    return EstadoConversa.NOVA_NOME


async def nova_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o nome da nova comunidade."""
    conversa = gerenciador.obter(update.effective_user.id)
    conversa.rascunho = Comunidade(update.message.text.strip())
    await update.message.reply_text(PERGUNTA_NOVA_LINKS, parse_mode="Markdown")
    return EstadoConversa.NOVA_LINKS


async def nova_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Acumula links; ao receber `pronto`, pede a seção."""
    conversa = gerenciador.obter(update.effective_user.id)
    texto = update.message.text.strip()
    if texto.lower() == PRONTO:
        if not conversa.rascunho.links:
            await update.message.reply_text("⚠️ Informe ao menos 1 link antes de concluir.")
            return EstadoConversa.NOVA_LINKS
        await update.message.reply_text(texto_lista_secoes(carregar_readme(Config.README_PATH)), parse_mode="Markdown")
        return EstadoConversa.NOVA_SECAO
    links, invalidas = parse_links(texto)
    conversa.rascunho.links.extend(links)
    resposta = f"➕ {len(links)} link(s) adicionado(s)."
    if invalidas:
        resposta += "\n⚠️ Não entendi: " + "; ".join(invalidas)
    await update.message.reply_text(resposta)
    return EstadoConversa.NOVA_LINKS


async def nova_secao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Resolve a seção escolhida e mostra o preview."""
    conversa = gerenciador.obter(update.effective_user.id)
    doc = carregar_readme(Config.README_PATH)
    secao = resolver_secao(doc, update.message.text)
    if secao is None:
        await update.message.reply_text(
            "⚠️ Seção não encontrada. " + texto_lista_secoes(doc), parse_mode="Markdown"
        )
        return EstadoConversa.NOVA_SECAO
    conversa.secao_alvo = secao
    relatorio = validar_comunidade(doc, conversa.rascunho)
    if not relatorio.ok:
        await update.message.reply_text(
            "⚠️ Corrija antes de continuar:\n" + "\n".join(str(p) for p in relatorio.erros)
        )
        return EstadoConversa.NOVA_LINKS
    return await _enviar_preview(update, conversa)


# ---------------------------------------------------------------------------
# Fluxo: EDITAR
# ---------------------------------------------------------------------------


async def cmd_editar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia o fluxo de edição."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    pendente = _publicacao_pendente()
    if pendente:
        await update.message.reply_text(pendente)
        return ConversationHandler.END
    gerenciador.iniciar(update.effective_user.id, Acao.EDITAR)
    teclado = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Listar comunidades", callback_data=CB_LISTAR)]]
    )
    await update.message.reply_text(PERGUNTA_EDITAR_NOME, reply_markup=teclado)
    return EstadoConversa.EDITAR_NOME


def _guardar_candidatos(doc, conversa, ocorrencias) -> list[str]:
    """Guarda (nome, seção, primeiro link) e devolve os rótulos para exibição."""
    conversa.candidatos = [
        (
            oc.comunidade.nome,
            oc.secao.nome,
            oc.comunidade.links[0].url if oc.comunidade.links else "",
        )
        for oc in ocorrencias
    ]
    duplicados = busca_service.nomes_duplicados(doc)
    return [busca_service.rotulo_candidato(oc, duplicados) for oc in ocorrencias]


def _candidato_escolhido(conversa, indice: int):
    """Relê o README e resolve o candidato pelo índice, desempatando pela URL."""
    if not 0 <= indice < len(conversa.candidatos):
        return None
    nome, secao, url = conversa.candidatos[indice]
    doc = carregar_readme(Config.README_PATH)
    candidatos = [
        oc for oc in doc.comunidades() if oc.comunidade.nome == nome and oc.secao.nome == secao
    ]
    if len(candidatos) > 1 and url:
        candidatos = [
            oc
            for oc in candidatos
            if oc.comunidade.links and oc.comunidade.links[0].url == url
        ]
    return candidatos[0] if candidatos else None


async def _oferecer_edicao(update: Update, conversa, ocorrencia) -> EstadoConversa:
    """Preenche o rascunho e oferece nome/links/ambos para edição."""
    conversa.nome_original = ocorrencia.comunidade.nome
    conversa.rascunho = Comunidade(ocorrencia.comunidade.nome, list(ocorrencia.comunidade.links))
    conversa.secao_alvo = ocorrencia.secao.nome
    conversa.candidatos = []
    teclado = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Nome", callback_data="edit_nome")],
            [InlineKeyboardButton("Links", callback_data="edit_links")],
            [InlineKeyboardButton("Nome e links", callback_data="edit_ambos")],
        ]
    )
    await _mensagem(update).reply_text(
        f"✏️ Editando *{_md(ocorrencia.comunidade.nome)}*.\nO que deseja alterar?",
        parse_mode="Markdown",
        reply_markup=teclado,
    )
    return EstadoConversa.EDITAR_ESCOLHA


async def editar_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Localiza a comunidade a editar (exata ou fuzzy) e oferece o que editar."""
    conversa = gerenciador.obter(update.effective_user.id)
    doc = carregar_readme(Config.README_PATH)
    termo = update.message.text.strip()
    ocorrencia = doc.buscar(termo)
    if ocorrencia is None:
        lista = busca_service.candidatos(doc, termo)
        if len(lista) == 1:
            ocorrencia = lista[0]
        elif lista:
            rotulos = _guardar_candidatos(doc, conversa, lista)
            await update.message.reply_text(
                texto_candidatos(rotulos, "editar"),
                reply_markup=teclado_candidatos(rotulos, "edit_cand"),
            )
            return EstadoConversa.EDITAR_CANDIDATOS
        else:
            await update.message.reply_text("⚠️ Comunidade não encontrada. Tente outro nome.")
            return EstadoConversa.EDITAR_NOME
    return await _oferecer_edicao(update, conversa, ocorrencia)


async def editar_candidato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o candidato escolhido na lista fuzzy e segue para a edição."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    try:
        indice = int(query.data.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        indice = -1
    ocorrencia = _candidato_escolhido(conversa, indice)
    if ocorrencia is None:
        gerenciador.encerrar(query.from_user.id)
        await query.message.reply_text("⚠️ Candidato inválido. Use /editar para recomeçar.")
        return ConversationHandler.END
    return await _oferecer_edicao(update, conversa, ocorrencia)


# ALTERADO [21/10/2026]: /editar híbrido — seleção por lista (seções → comunidades).
async def _mostrar_lista(update: Update, conversa, rotulos: list[str], pagina: int) -> None:
    """Envia (ou reenvia) a página da lista de comunidades da seção escolhida."""
    total_paginas = max(1, (len(rotulos) + LIMITE_LISTA - 1) // LIMITE_LISTA)
    pagina = max(0, min(pagina, total_paginas - 1))
    await _mensagem(update).reply_text(
        texto_lista(conversa.secao_alvo, pagina, total_paginas),
        parse_mode="Markdown",
        reply_markup=teclado_lista(rotulos, pagina),
    )


def _ocorrencias_da_secao(doc, secao: str):
    """Comunidades de uma seção, na ordem do README."""
    return [oc for oc in doc.comunidades() if oc.secao.nome == secao]


async def editar_listar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Abre a lista de seções editáveis (nível 1)."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    doc = carregar_readme(Config.README_PATH)
    secoes = lista_secoes_editaveis(doc)
    if not secoes:
        gerenciador.encerrar(query.from_user.id)
        await query.message.reply_text("⚠️ Nenhuma seção editável encontrada.")
        return ConversationHandler.END
    await query.message.reply_text(
        "📚 *Escolha a seção:*", parse_mode="Markdown", reply_markup=teclado_secoes(secoes)
    )
    return EstadoConversa.EDITAR_LISTA


async def editar_lista_secao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe a seção escolhida e mostra as comunidades dela (nível 2)."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    try:
        indice = int(query.data.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        indice = -1
    doc = carregar_readme(Config.README_PATH)
    secoes = lista_secoes_editaveis(doc)
    if not 0 <= indice < len(secoes):
        gerenciador.encerrar(query.from_user.id)
        await query.message.reply_text("⚠️ Seção inválida. Use /editar para recomeçar.")
        return ConversationHandler.END
    secao = secoes[indice]
    ocorrencias = _ocorrencias_da_secao(doc, secao)
    if not ocorrencias:
        await query.message.reply_text(
            f"⚠️ A seção *{_md(secao)}* não tem comunidades.", parse_mode="Markdown"
        )
        return EstadoConversa.EDITAR_LISTA
    conversa.secao_alvo = secao
    rotulos = _guardar_candidatos(doc, conversa, ocorrencias)
    await _mostrar_lista(update, conversa, rotulos, pagina=0)
    return EstadoConversa.EDITAR_CANDIDATOS


async def editar_lista_pagina(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Navega entre as páginas da lista de comunidades."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    if not conversa.secao_alvo:
        gerenciador.encerrar(query.from_user.id)
        await query.message.reply_text("⚠️ Sessão expirada. Use /editar para recomeçar.")
        return ConversationHandler.END
    try:
        pagina = int(query.data.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        pagina = 0
    doc = carregar_readme(Config.README_PATH)
    ocorrencias = _ocorrencias_da_secao(doc, conversa.secao_alvo)
    rotulos = _guardar_candidatos(doc, conversa, ocorrencias)
    await _mostrar_lista(update, conversa, rotulos, pagina)
    return EstadoConversa.EDITAR_CANDIDATOS


async def editar_lista_voltar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Volta da lista de comunidades para a lista de seções."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    conversa.secao_alvo = None
    conversa.candidatos = []
    doc = carregar_readme(Config.README_PATH)
    secoes = lista_secoes_editaveis(doc)
    await query.message.reply_text(
        "📚 *Escolha a seção:*", parse_mode="Markdown", reply_markup=teclado_secoes(secoes)
    )
    return EstadoConversa.EDITAR_LISTA


async def _enviar_menu_links(update: Update, conversa) -> EstadoConversa:
    """Reenvia o menu de links (com o estado atual da lista)."""
    await _responder(
        update,
        texto_menu_links(conversa),
        parse_mode="Markdown",
        reply_markup=teclado_links(conversa.rascunho.links),
    )
    return EstadoConversa.EDITAR_LINKS


def _indice_callback(data: str) -> int:
    """Extrai o índice numérico do callback (último sufixo ``_<n>``)."""
    try:
        return int(data.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return -1


async def editar_escolha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe a escolha (nome/links/ambos) e direciona o próximo passo."""
    query = update.callback_query
    await query.answer()
    conversa = gerenciador.obter(query.from_user.id)
    mapa = {"edit_nome": CAMPO_NOME, "edit_links": CAMPO_LINKS, "edit_ambos": CAMPO_AMBOS}
    conversa.campo_editar = mapa.get(query.data, CAMPO_NOME)
    proximo = gerenciador.proximo_estado(conversa)
    conversa.estado = proximo
    if proximo is EstadoConversa.EDITAR_LINKS:
        return await _enviar_menu_links(update, conversa)
    await query.message.reply_text(PERGUNTA_EDITAR_NOVO_NOME, parse_mode="Markdown")
    return proximo


async def editar_novo_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o novo nome."""
    conversa = gerenciador.obter(update.effective_user.id)
    conversa.rascunho.nome = update.message.text.strip()
    proximo = gerenciador.proximo_estado(conversa)
    if proximo is EstadoConversa.EDITAR_LINKS:
        conversa.estado = proximo
        return await _enviar_menu_links(update, conversa)
    return await _enviar_preview(update, conversa)


async def editar_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Menu de links: aceita colar vários (texto) e ANEXA com dedupe (R14)."""
    conversa = gerenciador.obter(update.effective_user.id)
    texto = update.message.text.strip()
    if texto.lower() == PRONTO:
        if not conversa.rascunho.links:
            await update.message.reply_text("⚠️ Informe ao menos 1 link antes de concluir.")
            return EstadoConversa.EDITAR_LINKS
        return await _enviar_preview(update, conversa)
    links, invalidas = parse_links(texto)
    adicionados = 0
    for link in links:
        if not any(l.tipo == link.tipo and l.url == link.url for l in conversa.rascunho.links):
            conversa.rascunho.links.append(link)
            adicionados += 1
    if adicionados:
        await update.message.reply_text(f"🔗 {adicionados} link(s) adicionado(s).")
    if invalidas:
        await update.message.reply_text("⚠️ Não entendi: " + "; ".join(invalidas))
    return await _enviar_menu_links(update, conversa)


# ALTERADO [21/10/2026]: gerenciador de links por botões (alterar/remover/adicionar).
async def editar_link_abrir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Abre o submenu de um link (alterar/remover/voltar)."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    indice = _indice_callback(query.data)
    if not 0 <= indice < len(conversa.rascunho.links):
        await query.message.reply_text("⚠️ Link inválido. Use o menu novamente.")
        return await _enviar_menu_links(update, conversa)
    link = conversa.rascunho.links[indice]
    await query.message.reply_text(
        f"🔗 *{_md(link.tipo)}*: {_md(link.url)}\nO que deseja fazer?",
        parse_mode="Markdown",
        reply_markup=teclado_link_item(indice),
    )
    return EstadoConversa.EDITAR_LINKS


async def editar_link_alterar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Pede o novo valor (identifier/URL) de um link existente."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    indice = _indice_callback(query.data)
    if not 0 <= indice < len(conversa.rascunho.links):
        await query.message.reply_text("⚠️ Link inválido. Use o menu novamente.")
        return await _enviar_menu_links(update, conversa)
    link = conversa.rascunho.links[indice]
    conversa.link_indice = indice
    conversa.link_tipo = link.tipo
    await query.message.reply_text(
        f"✏️ Envie o novo valor para *{_md(link.tipo)}* (identificador ou URL completa).\n"
        f"Atual: {_md(link.url)}",
        parse_mode="Markdown",
    )
    return EstadoConversa.LINK_VALOR


async def editar_link_valor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Aplica o valor digitado (via template ou URL completa) e volta ao menu."""
    conversa = gerenciador.obter(update.effective_user.id)
    if conversa.link_tipo is None:
        await update.message.reply_text("⚠️ Sessão expirada. Use /editar para recomeçar.")
        return ConversationHandler.END
    try:
        url = link_template.montar_url(conversa.link_tipo, update.message.text)
    except ValueError as erro:
        await update.message.reply_text(f"⚠️ {erro}")
        return EstadoConversa.LINK_VALOR
    link = Link(conversa.link_tipo, url)
    if conversa.link_indice is None:
        conversa.rascunho.links.append(link)
    else:
        conversa.rascunho.links[conversa.link_indice] = link
    conversa.link_indice = None
    conversa.link_tipo = None
    return await _enviar_menu_links(update, conversa)


async def editar_link_remover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Pede confirmação para remover um link (bloqueia o último — R2)."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    indice = _indice_callback(query.data)
    if not 0 <= indice < len(conversa.rascunho.links):
        await query.message.reply_text("⚠️ Link inválido. Use o menu novamente.")
        return await _enviar_menu_links(update, conversa)
    if len(conversa.rascunho.links) == 1:
        await query.message.reply_text("⚠️ A comunidade precisa de ao menos 1 link.")
        return await _enviar_menu_links(update, conversa)
    conversa.link_indice = indice
    link = conversa.rascunho.links[indice]
    teclado = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🗑️ Remover", callback_data="edit_lk_rmok"),
            InlineKeyboardButton("❌ Cancelar", callback_data="edit_lk_rmno"),
        ]]
    )
    await query.message.reply_text(
        f"🗑️ Remover *{_md(link.tipo)}* ({_md(link.url)})?",
        parse_mode="Markdown",
        reply_markup=teclado,
    )
    return EstadoConversa.LINK_REMOCAO_CONFIRMACAO


async def editar_link_remocao_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Confirma ou cancela a remoção do link."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    if query.data == "edit_lk_rmno":
        conversa.link_indice = None
        return await _enviar_menu_links(update, conversa)
    indice = conversa.link_indice
    conversa.link_indice = None
    if indice is None or not 0 <= indice < len(conversa.rascunho.links):
        await query.message.reply_text("⚠️ Link inválido.")
        return await _enviar_menu_links(update, conversa)
    if len(conversa.rascunho.links) == 1:
        await query.message.reply_text("⚠️ A comunidade precisa de ao menos 1 link.")
        return await _enviar_menu_links(update, conversa)
    del conversa.rascunho.links[indice]
    return await _enviar_menu_links(update, conversa)


async def editar_link_adicionar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Mostra o catálogo de tipos para adicionar um link."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    await query.message.reply_text(
        "🔗 Escolha o *tipo* do novo link:", parse_mode="Markdown", reply_markup=teclado_tipos()
    )
    return EstadoConversa.EDITAR_LINKS


async def editar_link_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o tipo escolhido e pede o valor do novo link."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    indice = _indice_callback(query.data)
    if not 0 <= indice < len(TIPOS_LINK):
        await query.message.reply_text("⚠️ Tipo inválido.")
        return await _enviar_menu_links(update, conversa)
    conversa.link_indice = None
    conversa.link_tipo = TIPOS_LINK[indice]
    dica = (
        "URL completa"
        if link_template.precisa_url_completa(conversa.link_tipo)
        else "identificador (ex.: usuário) ou URL completa"
    )
    await query.message.reply_text(
        f"🔗 Envie o valor para *{_md(conversa.link_tipo)}* ({dica}).", parse_mode="Markdown"
    )
    return EstadoConversa.LINK_VALOR


async def editar_link_concluir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Conclui a edição de links (exige ao menos 1) e vai ao preview."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    if not conversa.rascunho.links:
        await query.message.reply_text("⚠️ Informe ao menos 1 link antes de concluir.")
        return EstadoConversa.EDITAR_LINKS
    return await _enviar_preview(update, conversa)


async def editar_link_voltar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Volta ao menu de links."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    conversa.link_indice = None
    return await _enviar_menu_links(update, conversa)



# ---------------------------------------------------------------------------
# Fluxo: REMOVER
# ---------------------------------------------------------------------------


async def cmd_remover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia o fluxo de remoção."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    pendente = _publicacao_pendente()
    if pendente:
        await update.message.reply_text(pendente)
        return ConversationHandler.END
    gerenciador.iniciar(update.effective_user.id, Acao.REMOVER)
    await update.message.reply_text(PERGUNTA_REMOVER_NOME)
    return EstadoConversa.REMOVER_NOME


async def _pedir_confirmacao_remocao(update: Update, conversa, ocorrencia) -> EstadoConversa:
    """Preenche a conversa e pede confirmação explícita da remoção."""
    conversa.nome_original = ocorrencia.comunidade.nome
    conversa.secao_alvo = ocorrencia.secao.nome
    conversa.candidatos = []
    conversa.hash_base = escrita_service.hash_atual(Config.README_PATH)
    teclado = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Remover", callback_data="rem_ok"),
            InlineKeyboardButton("❌ Cancelar", callback_data="rem_nao"),
        ]]
    )
    await _mensagem(update).reply_text(
        f"🗑️ Remover *{_md(ocorrencia.comunidade.nome)}* de *{_md(ocorrencia.secao.nome)}*?",
        parse_mode="Markdown",
        reply_markup=teclado,
    )
    return EstadoConversa.REMOVER_CONFIRMACAO


async def remover_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Localiza a comunidade (exata ou fuzzy) e pede confirmação."""
    conversa = gerenciador.obter(update.effective_user.id)
    doc = carregar_readme(Config.README_PATH)
    termo = update.message.text.strip()
    ocorrencia = doc.buscar(termo)
    if ocorrencia is None:
        lista = busca_service.candidatos(doc, termo)
        if len(lista) == 1:
            ocorrencia = lista[0]
        elif lista:
            rotulos = _guardar_candidatos(doc, conversa, lista)
            await update.message.reply_text(
                texto_candidatos(rotulos, "remover"),
                reply_markup=teclado_candidatos(rotulos, "rem_cand"),
            )
            return EstadoConversa.REMOVER_CANDIDATOS
        else:
            await update.message.reply_text("⚠️ Comunidade não encontrada. Tente outro nome.")
            return EstadoConversa.REMOVER_NOME
    return await _pedir_confirmacao_remocao(update, conversa, ocorrencia)


async def remover_candidato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o candidato escolhido na lista fuzzy e pede confirmação."""
    query = update.callback_query
    await query.answer()
    if not _autorizado(update):
        await query.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    conversa = gerenciador.obter(query.from_user.id)
    try:
        indice = int(query.data.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        indice = -1
    ocorrencia = _candidato_escolhido(conversa, indice)
    if ocorrencia is None:
        gerenciador.encerrar(query.from_user.id)
        await query.message.reply_text("⚠️ Candidato inválido. Use /remover para recomeçar.")
        return ConversationHandler.END
    return await _pedir_confirmacao_remocao(update, conversa, ocorrencia)


async def remover_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Confirma ou cancela a remoção."""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    conversa = gerenciador.obter(uid)
    if query.data == "rem_nao":
        gerenciador.encerrar(uid)
        await query.message.reply_text("❌ Remoção cancelada.")
        return ConversationHandler.END
    if escrita_service.ocupado():
        await query.message.reply_text(escrita_service.MENSAGEM_OCUPADO)
        return EstadoConversa.REMOVER_CONFIRMACAO
    async with escrita_service.lock_escrita():
        servico = GitService.from_config()
        try:
            if servico.readme_pendente(Config.README_PATH):
                gerenciador.encerrar(uid)
                await query.message.reply_text(escrita_service.MENSAGEM_PUBLICACAO_PENDENTE)
                return ConversationHandler.END
        except GitError as erro:
            gerenciador.encerrar(uid)
            await query.message.reply_text(f"⚠️ Não foi possível inspecionar o repositório: {erro}")
            return ConversationHandler.END
        erro = escrita_service.sincronizar_seguro(servico)
        if erro is None:
            erro = escrita_service.conferir_hash(Config.README_PATH, conversa.hash_base)
        if erro is not None:
            gerenciador.encerrar(uid)
            await query.message.reply_text(erro)
            return ConversationHandler.END
        doc = carregar_readme(Config.README_PATH)
        resumo = aplicar_no_doc(doc, conversa)
        persistir(
            doc,
            caminho=Config.README_PATH,
            backup_dir=Config.BACKUP_DIR,
            historico_path=_historico_path(),
            usuario_id=uid,
            conversa=conversa,
            resumo=resumo,
        )
    gerenciador.encerrar(uid)
    await query.message.reply_text(resumo, parse_mode="Markdown")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Fluxo: BUSCAR
# ---------------------------------------------------------------------------


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia o fluxo de busca."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    gerenciador.iniciar(update.effective_user.id, Acao.BUSCAR)
    await update.message.reply_text(PERGUNTA_BUSCAR_NOME)
    return EstadoConversa.BUSCAR_NOME


async def buscar_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Busca a comunidade e mostra o resultado."""
    doc = carregar_readme(Config.README_PATH)
    termo = update.message.text.strip()
    ocorrencia = doc.buscar(termo)
    if ocorrencia is None:
        lista = busca_service.candidatos(doc, termo)
        if lista:
            duplicados = busca_service.nomes_duplicados(doc)
            linhas = [
                f"• {busca_service.rotulo_candidato(oc, duplicados)} "
                f"(seção {oc.secao.nome})"
                for oc in lista
            ]
            await update.message.reply_text(
                "🔍 Não encontrei exatamente. Talvez:\n" + "\n".join(linhas)
            )
        else:
            await update.message.reply_text("🔍 Nenhuma comunidade encontrada.")
        gerenciador.encerrar(update.effective_user.id)
        return ConversationHandler.END
    await update.message.reply_text(
        f"🔍 *{_md(ocorrencia.comunidade.nome)}* (seção *{_md(ocorrencia.secao.nome)}*)\n"
        + texto_resumo_comunidade(ocorrencia.comunidade),
        parse_mode="Markdown",
    )
    gerenciador.encerrar(update.effective_user.id)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Fluxo: APROVAÇÃO (preview)
# ---------------------------------------------------------------------------


async def aprovacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Processa a decisão do preview: ✅ aplicar, ✏️ editar, 🔀 seção, ❌ cancelar."""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    conversa = gerenciador.obter(uid)
    acao = conversa.acao

    if query.data == CB_CANCELAR:
        gerenciador.encerrar(uid)
        await query.message.reply_text("❌ Operação cancelada.")
        return ConversationHandler.END

    if query.data == CB_SECAO:
        doc = carregar_readme(Config.README_PATH)
        conversa.estado = EstadoConversa.NOVA_SECAO
        await query.message.reply_text(texto_lista_secoes(doc), parse_mode="Markdown")
        return EstadoConversa.NOVA_SECAO

    if query.data == CB_EDITAR:
        if acao is Acao.NOVA:
            conversa.rascunho.links = []
            conversa.estado = EstadoConversa.NOVA_NOME
            await query.message.reply_text(PERGUNTA_NOVA_NOME)
            return EstadoConversa.NOVA_NOME
        conversa.estado = EstadoConversa.EDITAR_ESCOLHA
        await query.message.reply_text("✏️ O que deseja alterar? (nome/links/ambos)")
        return EstadoConversa.EDITAR_ESCOLHA

    # CB_OK → aplicar
    if escrita_service.ocupado():
        await query.message.reply_text(escrita_service.MENSAGEM_OCUPADO)
        return EstadoConversa.APROVACAO
    async with escrita_service.lock_escrita():
        servico = GitService.from_config()
        try:
            if servico.readme_pendente(Config.README_PATH):
                gerenciador.encerrar(uid)
                await query.message.reply_text(escrita_service.MENSAGEM_PUBLICACAO_PENDENTE)
                return ConversationHandler.END
        except GitError as erro:
            gerenciador.encerrar(uid)
            await query.message.reply_text(f"⚠️ Não foi possível inspecionar o repositório: {erro}")
            return ConversationHandler.END
        erro = escrita_service.sincronizar_seguro(servico)
        if erro is None:
            erro = escrita_service.conferir_hash(Config.README_PATH, conversa.hash_base)
        if erro is not None:
            gerenciador.encerrar(uid)
            await query.message.reply_text(erro)
            return ConversationHandler.END
        doc = carregar_readme(Config.README_PATH)
        try:
            resumo = aplicar_no_doc(doc, conversa)
        except (ComunidadeNaoEncontrada, SecaoNaoEncontrada, SecaoNaoEditavel) as erro_aplicar:
            gerenciador.encerrar(uid)
            await query.message.reply_text(f"⚠️ Não foi possível aplicar: {erro_aplicar}")
            return ConversationHandler.END
        persistir(
            doc,
            caminho=Config.README_PATH,
            backup_dir=Config.BACKUP_DIR,
            historico_path=_historico_path(),
            usuario_id=uid,
            conversa=conversa,
            resumo=resumo,
        )
    gerenciador.encerrar(uid)
    await query.message.reply_text(resumo, parse_mode="Markdown")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Comandos simples (fora do fluxo)
# ---------------------------------------------------------------------------


def _historico_path() -> Path:
    return Path(Config.README_PATH).parent.parent / "bot" / "history" / "historico.jsonl"


async def cmd_listar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todas as comunidades do README."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return
    doc = carregar_readme(Config.README_PATH)
    linhas = [f"📋 *{secao.nome}*" for secao in doc.secoes if lista_secoes_editaveis(doc)]
    for secao in doc.secoes:
        if secao.coluna_nome in (None, "Serviço"):
            continue
        ocorrencias = [oc for oc in doc.comunidades() if oc.secao.nome == secao.nome]
        if not ocorrencias:
            continue
        linhas.append(f"\n*{_md(secao.nome)}* ({len(ocorrencias)})")
        linhas += [f"• {_md(oc.comunidade.nome)}" for oc in ocorrencias]
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def cmd_validar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🧩 Validar README — varredura completa, por severidade."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return
    relatorio = validar_readme(carregar_readme(Config.README_PATH))
    if not relatorio.problemas:
        await update.message.reply_text("🧩 README íntegro — nenhum problema encontrado.")
        return
    linhas = [
        f"🧩 Validação do README — {len(relatorio.erros)} erro(s), "
        f"{len(relatorio.avisos)} aviso(s):"
    ]
    linhas += [f"• {problema}" for problema in relatorio.problemas[:40]]
    await update.message.reply_text("\n".join(linhas))


async def cmd_historico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📜 Histórico — últimas alterações registradas (JSONL)."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return
    registros = historico_service.ler_historico(_historico_path())
    if not registros:
        await update.message.reply_text("📜 Nenhuma alteração registrada.")
        return
    linhas = ["📜 Últimas alterações:"]
    for registro in reversed(registros[-10:]):
        alvo = registro.comunidade or registro.backup_path or registro.commit or ""
        linhas.append(f"• {registro.timestamp} — {registro.acao} — {alvo}")
    await update.message.reply_text("\n".join(linhas))


async def cancelar_fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Cancela o fluxo em andamento."""
    gerenciador.encerrar(update.effective_user.id)
    await update.message.reply_text("❌ Operação cancelada.")
    return ConversationHandler.END


def montar_conversation_handler() -> ConversationHandler:
    """Monta o `ConversationHandler` do fluxo conversacional (CRUD + publicação)."""
    estados = {
        EstadoConversa.NOVA_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_nome)],
        EstadoConversa.NOVA_LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_links)],
        EstadoConversa.NOVA_SECAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_secao)],
        EstadoConversa.EDITAR_NOME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, editar_nome),
            CallbackQueryHandler(editar_listar, pattern=PADRAO_LISTAR),
        ],
        EstadoConversa.EDITAR_CANDIDATOS: [
            CallbackQueryHandler(editar_candidato, pattern=PADRAO_CANDIDATOS_EDITAR),
            CallbackQueryHandler(editar_candidato, pattern=PADRAO_LISTA_CANDIDATO),
            CallbackQueryHandler(editar_lista_pagina, pattern=PADRAO_LISTA_PAGINA),
            CallbackQueryHandler(editar_lista_voltar, pattern=PADRAO_LISTA_VOLTAR),
            MessageHandler(filters.TEXT & ~filters.COMMAND, editar_nome),
        ],
        EstadoConversa.EDITAR_LISTA: [
            CallbackQueryHandler(editar_lista_secao, pattern=PADRAO_SECAO_LISTA),
            CallbackQueryHandler(editar_lista_voltar, pattern=PADRAO_LISTA_VOLTAR),
            MessageHandler(filters.TEXT & ~filters.COMMAND, editar_nome),
        ],
        EstadoConversa.EDITAR_ESCOLHA: [CallbackQueryHandler(editar_escolha, pattern="^edit_(nome|links|ambos)$")],
        EstadoConversa.EDITAR_NOVO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_novo_nome)],
        EstadoConversa.EDITAR_LINKS: [
            CallbackQueryHandler(editar_link_abrir, pattern=PADRAO_LINK_ABRIR),
            CallbackQueryHandler(editar_link_alterar, pattern=PADRAO_LINK_ALTERAR),
            CallbackQueryHandler(editar_link_remover, pattern=PADRAO_LINK_REMOVER),
            CallbackQueryHandler(editar_link_adicionar, pattern=PADRAO_LINK_ADICIONAR),
            CallbackQueryHandler(editar_link_tipo, pattern=PADRAO_LINK_TIPO),
            CallbackQueryHandler(editar_link_concluir, pattern=PADRAO_LINK_CONCLUIR),
            CallbackQueryHandler(editar_link_voltar, pattern=PADRAO_LINK_VOLTAR),
            MessageHandler(filters.TEXT & ~filters.COMMAND, editar_links),
        ],
        EstadoConversa.LINK_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_link_valor)],
        EstadoConversa.LINK_REMOCAO_CONFIRMACAO: [
            CallbackQueryHandler(editar_link_remocao_confirmar, pattern=PADRAO_LINK_REMOCAO)
        ],
        EstadoConversa.REMOVER_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remover_nome)],
        EstadoConversa.REMOVER_CANDIDATOS: [
            CallbackQueryHandler(remover_candidato, pattern=PADRAO_CANDIDATOS_REMOVER),
            MessageHandler(filters.TEXT & ~filters.COMMAND, remover_nome),
        ],
        EstadoConversa.REMOVER_CONFIRMACAO: [CallbackQueryHandler(remover_confirmacao, pattern="^rem_(ok|nao)$")],
        EstadoConversa.BUSCAR_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_nome)],
        EstadoConversa.APROVACAO: [CallbackQueryHandler(aprovacao, pattern=PADRAO_APROVACAO)],
    }
    estados.update(publicacao.estados_publicacao())
    return ConversationHandler(
        entry_points=[
            CommandHandler("nova", cmd_nova),
            CommandHandler("buscar", cmd_buscar),
            CommandHandler("editar", cmd_editar),
            CommandHandler("remover", cmd_remover),
            *publicacao.entradas_publicacao(),
        ],
        states=estados,
        fallbacks=[
            CommandHandler("cancelar", cancelar_fluxo),
        ],
        allow_reentry=True,
    )
