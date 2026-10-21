"""Montagem de URLs de links a partir de um identificador ("handle").

Para tipos com base previsível (Instagram, GitHub, Telegram, …), o usuário pode
enviar apenas o identificador; a URL é montada pelo template. Uma **URL completa**
(`http://`/`https://`) tem **precedência** e é usada como está — o que cobre tipos
ambíguos (YouTube, LinkedIn, WhatsApp, Facebook) e links fora do padrão.

Módulo puro (sem I/O), testável de forma hermética.
"""

from __future__ import annotations

# tipo -> base da URL (o identificador entra em {valor}).
TEMPLATES: dict[str, str] = {
    "Instagram": "https://instagram.com/{valor}",
    "GitHub": "https://github.com/{valor}",
    "GitLab": "https://gitlab.com/{valor}",
    "Facebook": "https://facebook.com/{valor}",
    "X": "https://x.com/{valor}",
    "YouTube": "https://youtube.com/@{valor}",
    "Telegram": "https://t.me/{valor}",
    "Meetup": "https://meetup.com/{valor}",
    "LinkTree": "https://linktr.ee/{valor}",
    "LinkedIn": "https://linkedin.com/in/{valor}",
    "WhatsApp": "https://wa.me/{valor}",
}

# Tipos que não têm base previsível: exigem URL completa.
URL_COMPLETA_OBRIGATORIA: frozenset[str] = frozenset(
    {"Site", "Google Drive", "Slack", "Discord"}
)


def precisa_url_completa(tipo: str) -> bool:
    """True se o tipo não tem template e exige URL completa."""
    return tipo not in TEMPLATES


def montar_url(tipo: str, valor: str) -> str:
    """Monta a URL do link.

    - ``valor`` começando com ``http://``/``https://`` → usado como está.
    - tipo com template → aplica a base ao identificador.
    - caso contrário → ``ValueError`` (o tipo exige URL completa).
    """
    valor = valor.strip()
    if not valor:
        raise ValueError("informe um identificador ou a URL completa")
    if valor.startswith(("http://", "https://")):
        return valor
    base = TEMPLATES.get(tipo)
    if base is None:
        raise ValueError(f"para {tipo}, envie a URL completa")
    return base.format(valor=valor.lstrip("@/"))
