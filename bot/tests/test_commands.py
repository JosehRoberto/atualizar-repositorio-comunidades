"""Testes herméticos do menu nativo de comandos (`commands.py`).

Cobrem a composição de `COMANDOS_MENU`, a derivação do texto `MENU`, o `post_init`
(com `bot.set_my_commands` mockado) e a montagem da `Application`. Sem rede, sem
`.env` real e sem tocar em produção.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import BotCommand
from telegram.ext import CommandHandler, ConversationHandler

from bot.config import Config
from bot.handlers.commands import (
    COMANDOS_MENU,
    MENU,
    create_application,
    post_init,
)

NOMES_ESPERADOS = {
    "start",
    "nova",
    "buscar",
    "editar",
    "remover",
    "listar",
    "validar",
    "historico",
    "publicar",
    "restaurar",
    "cancelar",
}

PADRAO_COMANDO = re.compile(r"^[a-z0-9_]{1,32}$")


def _comandos_registrados(application) -> set[str]:
    """Coleta os nomes de comando registrados (globais + entry points)."""
    nomes: set[str] = set()
    for grupo in application.handlers.values():
        for handler in grupo:
            if isinstance(handler, CommandHandler):
                nomes.update(handler.commands)
            elif isinstance(handler, ConversationHandler):
                for entry in handler.entry_points:
                    if isinstance(entry, CommandHandler):
                        nomes.update(entry.commands)
    return nomes


class TestComandosMenu:
    def test_sem_duplicatas(self):
        nomes = [comando for comando, _ in COMANDOS_MENU]
        assert len(nomes) == len(set(nomes))

    def test_nomes_validos_para_o_telegram(self):
        for comando, _ in COMANDOS_MENU:
            assert PADRAO_COMANDO.match(comando), comando

    def test_descricoes_dentro_do_limite(self):
        for _, descricao in COMANDOS_MENU:
            assert 1 <= len(descricao) <= 256
            assert "\n" not in descricao

    def test_menu_derivado_exclui_start(self):
        assert "/start" not in MENU
        for comando, descricao in COMANDOS_MENU:
            if comando == "start":
                continue
            assert f"/{comando} — {descricao}" in MENU

    def test_menu_tem_cabecalho(self):
        assert MENU.startswith("📋 Menu principal:")


class TestPostInit:
    @pytest.mark.asyncio
    async def test_registra_comandos(self):
        bot = SimpleNamespace(set_my_commands=AsyncMock())
        application = SimpleNamespace(bot=bot)

        await post_init(application)

        bot.set_my_commands.assert_awaited_once()
        comandos = bot.set_my_commands.call_args.args[0]
        assert [c.command for c in comandos] == [comando for comando, _ in COMANDOS_MENU]
        assert all(isinstance(c, BotCommand) for c in comandos)

    @pytest.mark.asyncio
    async def test_falha_de_rede_nao_propaga(self):
        bot = SimpleNamespace(set_my_commands=AsyncMock(side_effect=RuntimeError("rede")))
        application = SimpleNamespace(bot=bot)

        await post_init(application)

        bot.set_my_commands.assert_awaited_once()


class TestCreateApplication:
    def test_token_ausente(self, monkeypatch):
        monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "")
        with pytest.raises(RuntimeError):
            create_application()

    def test_post_init_atribuido_uma_vez(self, config_ok):
        application = create_application()
        assert application.post_init is post_init

    def test_conversation_handler_registrado_primeiro(self, config_ok):
        application = create_application()
        primeiro = application.handlers[0][0]
        assert isinstance(primeiro, ConversationHandler)

    def test_todo_comando_do_menu_tem_handler(self, config_ok):
        application = create_application()
        registrados = _comandos_registrados(application)
        assert {comando for comando, _ in COMANDOS_MENU} <= registrados

    def test_comandos_esperados(self, config_ok):
        application = create_application()
        assert _comandos_registrados(application) == NOMES_ESPERADOS
