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
from bot.services import backup_service, busca_service, escrita_service, historico_service
from bot.services.git_service import GitError, GitService
from bot.services.readme_service import (
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
    gerenciador.iniciar(update.effective_user.id, Acao.EDITAR)
    await update.message.reply_text(PERGUNTA_EDITAR_NOME)
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


async def editar_escolha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe a escolha (nome/links/ambos) e direciona o próximo passo."""
    query = update.callback_query
    await query.answer()
    conversa = gerenciador.obter(query.from_user.id)
    mapa = {"edit_nome": CAMPO_NOME, "edit_links": CAMPO_LINKS, "edit_ambos": CAMPO_AMBOS}
    conversa.campo_editar = mapa.get(query.data, CAMPO_NOME)
    proximo = gerenciador.proximo_estado(conversa)
    conversa.estado = proximo
    pergunta = PERGUNTA_EDITAR_NOVO_NOME if proximo is EstadoConversa.EDITAR_NOVO_NOME else PERGUNTA_EDITAR_LINKS
    await query.message.reply_text(pergunta, parse_mode="Markdown")
    return proximo


async def editar_novo_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o novo nome."""
    conversa = gerenciador.obter(update.effective_user.id)
    conversa.rascunho.nome = update.message.text.strip()
    proximo = gerenciador.proximo_estado(conversa)
    if proximo is EstadoConversa.EDITAR_LINKS:
        await update.message.reply_text(PERGUNTA_EDITAR_LINKS, parse_mode="Markdown")
        return proximo
    return await _enviar_preview(update, conversa)


async def editar_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Acumula novos links; ao receber `pronto`, mostra o preview."""
    conversa = gerenciador.obter(update.effective_user.id)
    texto = update.message.text.strip()
    if texto.lower() == PRONTO:
        if not conversa.rascunho.links:
            await update.message.reply_text("⚠️ Informe ao menos 1 link antes de concluir.")
            return EstadoConversa.EDITAR_LINKS
        return await _enviar_preview(update, conversa)
    links, invalidas = parse_links(texto)
    if links:
        conversa.rascunho.links = links
        await update.message.reply_text(f"🔗 {len(links)} link(s) definido(s). Envie *pronto* para concluir.", parse_mode="Markdown")
    if invalidas:
        await update.message.reply_text("⚠️ Não entendi: " + "; ".join(invalidas))
    return EstadoConversa.EDITAR_LINKS


# ---------------------------------------------------------------------------
# Fluxo: REMOVER
# ---------------------------------------------------------------------------


async def cmd_remover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia o fluxo de remoção."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
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
        erro = escrita_service.sincronizar_seguro(GitService.from_config())
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
        erro = escrita_service.sincronizar_seguro(GitService.from_config())
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
        EstadoConversa.EDITAR_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_nome)],
        EstadoConversa.EDITAR_CANDIDATOS: [
            CallbackQueryHandler(editar_candidato, pattern=PADRAO_CANDIDATOS_EDITAR),
            MessageHandler(filters.TEXT & ~filters.COMMAND, editar_nome),
        ],
        EstadoConversa.EDITAR_ESCOLHA: [CallbackQueryHandler(editar_escolha, pattern="^edit_(nome|links|ambos)$")],
        EstadoConversa.EDITAR_NOVO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_novo_nome)],
        EstadoConversa.EDITAR_LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_links)],
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
