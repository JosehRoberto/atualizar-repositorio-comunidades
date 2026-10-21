"""Ponto de entrada do bot."""

import logging
import warnings

from telegram.warnings import PTBUserWarning

from bot.config import Config
from bot.handlers.commands import create_application


def configurar_logging() -> None:
    """Configura o logging e silencia bibliotecas que expõem o token nos logs."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    for ruidoso in ("httpx", "httpcore", "telegram.request"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    # Esperado ao misturar MessageHandler e CallbackQueryHandler (per_message=False).
    warnings.filterwarnings(
        "ignore",
        message="If 'per_message=False', 'CallbackQueryHandler' will not be tracked",
        category=PTBUserWarning,
    )


def main() -> None:
    """Valida a configuração e inicia o polling."""
    configurar_logging()

    problemas = Config.validar()
    if problemas:
        raise SystemExit("Configuração inválida: " + "; ".join(problemas))

    application = create_application()
    application.run_polling()


if __name__ == "__main__":
    main()
