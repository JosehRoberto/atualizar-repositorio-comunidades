"""Handlers de comando e montagem da `Application`."""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config

logger = logging.getLogger(__name__)

MENU = (
    "📋 Menu principal:\n"
    "➕ Nova comunidade\n"
    "🔍 Buscar comunidade\n"
    "✏️ Editar comunidade\n"
    "🗑️ Remover comunidade\n"
    "📋 Listar comunidades\n"
    "🧩 Validar README\n"
    "📜 Histórico de alterações\n"
    "⬆️ Publicar alterações\n"
    "↩️ Cancelar"
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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_error_handler(error_handler)
    return application
