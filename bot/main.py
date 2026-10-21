"""Ponto de entrada do bot."""

import logging

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
