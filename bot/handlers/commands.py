"""Handlers de comando e montagem da `Application`."""

import logging

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config
from bot.handlers.menu import cmd_historico, cmd_listar, cmd_validar, montar_conversation_handler

logger = logging.getLogger(__name__)

COMANDOS_MENU = [
    ("start", "Iniciar o bot / menu principal"),
    ("nova", "➕ Nova comunidade"),
    ("buscar", "🔍 Buscar comunidade"),
    ("editar", "✏️ Editar comunidade"),
    ("remover", "🗑️ Remover comunidade"),
    ("listar", "📋 Listar comunidades"),
    ("validar", "🧩 Validar README"),
    ("historico", "📜 Histórico de alterações"),
    ("publicar", "⬆️ Publicar alterações"),
    ("restaurar", "♻️ Restaurar backup"),
    ("cancelar", "↩️ Cancelar"),
]

MENU = "📋 Menu principal:\n" + "\n".join(
    f"/{comando} — {descricao}" for comando, descricao in COMANDOS_MENU if comando != "start"
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


async def post_init(application: Application) -> None:
    """Registra o menu nativo de comandos no Telegram.

    Executado uma única vez no boot (via ``run_polling``). Não deve derrubar o
    polling caso a chamada de rede falhe (§7, R1).
    """
    try:
        await application.bot.set_my_commands(
            [BotCommand(comando, descricao) for comando, descricao in COMANDOS_MENU]
        )
        logger.info("Comandos registrados no menu do Telegram.")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar comandos no menu do Telegram")


def create_application() -> Application:
    """Cria a `Application` e registra os handlers (a ordem importa)."""
    if not Config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado")

    # ALTERADO 21/10/2026: registra o menu nativo de comandos via post_init (região protegida §3.1).
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(montar_conversation_handler())
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("listar", cmd_listar))
    application.add_handler(CommandHandler("validar", cmd_validar))
    application.add_handler(CommandHandler("historico", cmd_historico))
    application.add_error_handler(error_handler)
    return application
