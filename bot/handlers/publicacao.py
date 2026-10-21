"""Publicação e restauração de backups (docs/requisitos.md §2.11).

- ``/publicar`` — sincroniza, mostra as alterações pendentes e, **somente após
  confirmação explícita**, faz commit + push (token fora da URL; nunca ``reset --hard``).
- ``/restaurar`` — lista os backups, mostra o **diff**, exige confirmação e restaura com
  backup prévio (``README_pre-restauracao_*.bak``) + registro no histórico.

Os helpers de texto/seleção são puros (testáveis de forma hermética); os handlers falam
com o Telegram.
"""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import Config
from bot.handlers.state_manager import Acao, EstadoConversa, gerenciador
from bot.services import backup_service, historico_service
from bot.services.git_service import GitError, GitService

logger = logging.getLogger(__name__)

CB_PUB_OK = "pub_ok"
CB_PUB_CANCELAR = "pub_cancelar"
CB_REST_OK = "rest_ok"
CB_REST_CANCELAR = "rest_cancelar"
PADRAO_PUB = f"^({CB_PUB_OK}|{CB_PUB_CANCELAR})$"
PADRAO_REST = f"^({CB_REST_OK}|{CB_REST_CANCELAR})$"

LIMITE_BACKUPS = 10
SUFIXO_PRE_RESTAURACAO = backup_service.SUFIXO_PRE_RESTAURACAO
MENSAGEM_COMMIT = "chore: atualiza comunidades pelo bot"


def _autorizado(update: Update) -> bool:
    """True se o usuário está na lista de autorizados (ou lista vazia em dev)."""
    user = update.effective_user
    if user is None:
        return False
    if not Config.TELEGRAM_ALLOWED_USER_IDS:
        return True
    return user.id in Config.TELEGRAM_ALLOWED_USER_IDS


def _historico_path() -> Path:
    return Path(Config.README_PATH).parent.parent / "bot" / "history" / "historico.jsonl"


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------


def backups_restauraveis(backup_dir: str | Path) -> list[Path]:
    """Backups disponíveis para restauração (mais recente primeiro).

    Exclui os ``_pre-restauracao_`` (cópias de segurança geradas na própria restauração).
    """
    return [
        caminho
        for caminho in backup_service.listar_backups(backup_dir, prefixo="README")
        if SUFIXO_PRE_RESTAURACAO not in caminho.name
    ]


def texto_backups(backups: list[Path]) -> str:
    """Lista numerada dos backups (limite `LIMITE_BACKUPS`)."""
    linhas = ["🗂️ *Backups disponíveis* (mais recente primeiro):"]
    linhas += [f"{i}. `{caminho.name}`" for i, caminho in enumerate(backups[:LIMITE_BACKUPS], start=1)]
    linhas.append("\nEnvie o *número* do backup a restaurar.")
    return "\n".join(linhas)


def resolver_backup(backups: list[Path], escolha: str) -> Path | None:
    """Resolve o número informado para um backup (ou ``None`` se inválido)."""
    escolha = escolha.strip()
    if not escolha.isdigit():
        return None
    indice = int(escolha)
    if 1 <= indice <= min(len(backups), LIMITE_BACKUPS):
        return backups[indice - 1]
    return None


def texto_publicacao(alteracoes: list[str]) -> str:
    """Mensagem de preview da publicação com as alterações pendentes."""
    linhas = ["⬆️ *Publicar alterações*", "Alterações pendentes:"]
    linhas += [f"• `{linha}`" for linha in alteracoes]
    linhas.append("\nConfirmar commit e push?")
    return "\n".join(linhas)


def texto_restauracao(nome_backup: str, diff: str) -> str:
    """Mensagem de preview da restauração com o diff (truncado)."""
    corpo = diff.strip() or "(sem diferenças — o README já está igual a este backup)"
    return (
        f"🔎 *Restauração* — `{nome_backup}`\n\n"
        f"```diff\n{corpo[:3000]}\n```\n\n"
        "Confirmar restauração?"
    )


def teclado_publicacao() -> InlineKeyboardMarkup:
    """Teclado de confirmação da publicação."""
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Publicar", callback_data=CB_PUB_OK),
            InlineKeyboardButton("❌ Cancelar", callback_data=CB_PUB_CANCELAR),
        ]]
    )


def teclado_restauracao() -> InlineKeyboardMarkup:
    """Teclado de confirmação da restauração."""
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Restaurar", callback_data=CB_REST_OK),
            InlineKeyboardButton("❌ Cancelar", callback_data=CB_REST_CANCELAR),
        ]]
    )


# ---------------------------------------------------------------------------
# Fluxo: PUBLICAR
# ---------------------------------------------------------------------------


async def cmd_publicar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia a publicação: mostra as alterações pendentes e pede confirmação."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    uid = update.effective_user.id
    gerenciador.iniciar(uid, Acao.PUBLICAR)
    try:
        alteracoes = GitService.from_config().alteracoes()
    except GitError as erro:
        gerenciador.encerrar(uid)
        await update.message.reply_text(f"⚠️ Não foi possível inspecionar o repositório: {erro}")
        return ConversationHandler.END
    if not alteracoes:
        gerenciador.encerrar(uid)
        await update.message.reply_text("✅ Nada a publicar — o repositório está limpo.")
        return ConversationHandler.END
    await update.message.reply_text(
        texto_publicacao(alteracoes), parse_mode="Markdown", reply_markup=teclado_publicacao()
    )
    return EstadoConversa.PUBLICAR_CONFIRMACAO


async def publicar_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Confirma (commit + push) ou cancela a publicação."""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data == CB_PUB_CANCELAR:
        gerenciador.encerrar(uid)
        await query.message.reply_text("❌ Publicação cancelada.")
        return ConversationHandler.END

    servico = GitService.from_config()
    try:
        servico.sincronizar()
        commit = servico.commit(Config.README_PATH, MENSAGEM_COMMIT)
        servico.push()
    except GitError as erro:
        gerenciador.encerrar(uid)
        await query.message.reply_text(f"⚠️ Falha ao publicar: {erro}")
        return ConversationHandler.END

    historico_service.registrar(
        _historico_path(),
        historico_service.RegistroHistorico(acao="publicar", usuario_id=uid, commit=commit),
    )
    gerenciador.encerrar(uid)
    await query.message.reply_text(f"✅ Publicado. Commit `{commit[:8]}`.", parse_mode="Markdown")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Fluxo: RESTAURAR
# ---------------------------------------------------------------------------


async def cmd_restaurar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Inicia a restauração: lista os backups disponíveis."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return ConversationHandler.END
    uid = update.effective_user.id
    gerenciador.iniciar(uid, Acao.RESTAURAR)
    backups = backups_restauraveis(Config.BACKUP_DIR)
    if not backups:
        gerenciador.encerrar(uid)
        await update.message.reply_text("📭 Nenhum backup disponível para restauração.")
        return ConversationHandler.END
    await update.message.reply_text(texto_backups(backups), parse_mode="Markdown")
    return EstadoConversa.RESTAURAR_ESCOLHA


async def restaurar_escolha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Recebe o número do backup e mostra o diff para confirmação."""
    conversa = gerenciador.obter(update.effective_user.id)
    backups = backups_restauraveis(Config.BACKUP_DIR)
    backup = resolver_backup(backups, update.message.text)
    if backup is None:
        await update.message.reply_text(
            "⚠️ Número inválido. " + texto_backups(backups), parse_mode="Markdown"
        )
        return EstadoConversa.RESTAURAR_ESCOLHA
    conversa.backup_escolhido = str(backup)
    try:
        diff = backup_service.diff_backup(backup, Config.README_PATH)
    except backup_service.BackupNaoEncontrado:
        diff = ""
    await update.message.reply_text(
        texto_restauracao(backup.name, diff), parse_mode="Markdown", reply_markup=teclado_restauracao()
    )
    return EstadoConversa.RESTAURAR_CONFIRMACAO


async def restaurar_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> EstadoConversa:
    """Confirma (restaura com backup prévio) ou cancela."""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    conversa = gerenciador.obter(uid)
    if query.data == CB_REST_CANCELAR:
        gerenciador.encerrar(uid)
        await query.message.reply_text("❌ Restauração cancelada.")
        return ConversationHandler.END

    backup = Path(conversa.backup_escolhido) if conversa.backup_escolhido else None
    if backup is None or not backup.is_file():
        gerenciador.encerrar(uid)
        await query.message.reply_text("⚠️ Backup não encontrado — refaça a seleção.")
        return ConversationHandler.END

    pre = backup_service.restaurar_backup(backup, Config.README_PATH, Config.BACKUP_DIR)
    historico_service.registrar(
        _historico_path(),
        historico_service.RegistroHistorico(
            acao="restaurar", usuario_id=uid, backup_path=str(backup)
        ),
    )
    gerenciador.encerrar(uid)
    extra = f" Backup do estado anterior: `{pre.name}`." if pre else ""
    await query.message.reply_text(
        f"✅ README restaurado de `{backup.name}`.{extra}", parse_mode="Markdown"
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Integração com o ConversationHandler
# ---------------------------------------------------------------------------


def entradas_publicacao() -> list:
    """Entry points de `/publicar` e `/restaurar`."""
    return [
        CommandHandler("publicar", cmd_publicar),
        CommandHandler("restaurar", cmd_restaurar),
    ]


def estados_publicacao() -> dict:
    """Estados do fluxo de publicação/restauração."""
    return {
        EstadoConversa.PUBLICAR_CONFIRMACAO: [
            CallbackQueryHandler(publicar_confirmacao, pattern=PADRAO_PUB)
        ],
        EstadoConversa.RESTAURAR_ESCOLHA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, restaurar_escolha)
        ],
        EstadoConversa.RESTAURAR_CONFIRMACAO: [
            CallbackQueryHandler(restaurar_confirmacao, pattern=PADRAO_REST)
        ],
    }
