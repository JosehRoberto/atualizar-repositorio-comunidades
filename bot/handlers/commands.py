"""Handlers de comando e montagem da `Application`."""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config
from bot.handlers.menu import cmd_historico, cmd_listar, cmd_validar, montar_conversation_handler

logger = logging.getLogger(__name__)

MENU = (
    "📋 Menu principal:\n"
    "/nova — ➕ Nova comunidade\n"
    "/buscar — 🔍 Buscar comunidade\n"
    "/editar — ✏️ Editar comunidade\n"
    "/remover — 🗑️ Remover comunidade\n"
    "/listar — 📋 Listar comunidades\n"
    "/validar — 🧩 Validar README\n"
    "/historico — 📜 Histórico de alterações\n"
    "/publicar — ⬆️ Publicar alterações\n"
    "/restaurar — ♻️ Restaurar backup\n"
    "/cancelar — ↩️ Cancelar"
)


def _autorizado(update: Update) -> bool:
    """True se o usuário está na lista de autorizados (ou se a lista está vazia em dev)."""
    user = update.effective_user
    if user is None:
        return False
    if not Config.TELEGRAM_ALLOWED_USER_IDS:
        return True
    return user.id in Config.TELEGRAM_ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe o menu principal para usuários autorizados."""
    if not _autorizado(update):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return
    await update.message.reply_text(f"👋 Olá! Bem-vindo(a).\n\n{MENU}")


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Encerra a operação atual."""
    await update.message.reply_text("❌ Operação cancelada.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra exceções sem vazar detalhes sensíveis."""
    logger.error("Exceção ao tratar update: %s", context.error)


def create_application() -> Application:
    """Cria a `Application` e registra os handlers (a ordem importa)."""
    if not Config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado")

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(montar_conversation_handler())
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("listar", cmd_listar))
    application.add_handler(CommandHandler("validar", cmd_validar))
    application.add_handler(CommandHandler("historico", cmd_historico))
    application.add_error_handler(error_handler)
    return application
