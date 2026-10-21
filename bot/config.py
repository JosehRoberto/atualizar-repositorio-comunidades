"""Configuração do bot — lê variáveis de ambiente (`.env`), sem valores hardcoded."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).resolve().parent / ".env")


def _parse_ids(valor: str) -> list[int]:
    """Converte '1, 2,3' em [1, 2, 3], ignorando vazios."""
    return [int(i) for i in valor.replace(" ", "").split(",") if i]


class Config:
    """Configurações do projeto, lidas do ambiente na importação."""

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USER_IDS = _parse_ids(os.getenv("TELEGRAM_ALLOWED_USER_IDS", ""))

    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
    GITLAB_USERNAME = os.getenv("GITLAB_USERNAME", "oauth2")
    GIT_REPO_URL = os.getenv(
        "GIT_REPO_URL",
        "https://gitlab.com/paralivre/comunidades-de-tecnologia-pa.git",
    )
    GIT_BRANCH = os.getenv("GIT_BRANCH", "master")
    GIT_USER_NAME = os.getenv("GIT_USER_NAME", "ParaLivre")
    GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "contato@paralivre.org")

    README_PATH = Path(
        os.getenv("README_PATH", str(PROJECT_ROOT / "repositorio" / "README.md"))
    )
    BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(PROJECT_ROOT / "backup")))
    TIMEZONE = os.getenv("TIMEZONE", "America/Belem")

    @classmethod
    def validar(cls) -> list[str]:
        """Retorna a lista de problemas de configuração (lista vazia = tudo ok)."""
        problemas: list[str] = []
        if not cls.TELEGRAM_BOT_TOKEN:
            problemas.append("TELEGRAM_BOT_TOKEN ausente")
        if not cls.TELEGRAM_ALLOWED_USER_IDS:
            problemas.append("TELEGRAM_ALLOWED_USER_IDS ausente")
        return problemas
