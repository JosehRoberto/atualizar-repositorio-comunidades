# Planejamento Estratégico: menu de comandos nativo do Telegram ("menu da esquerda")

**Data:** 21/10/2026
**Versão:** 1.1
**Foco:** `bot/handlers/commands.py` (registro do menu nativo de comandos)
**Status:** **implementado, validado e em produção** (270 testes; `py_compile` + import OK; restart
systemd efetivado — R7 concluído). **Commit (`639f202`, `45aad75`) e tag `v0.4.0` publicados no `origin`.**
**Revisão de risco incorporada** (R1–R9; `prompts/prompt-revisao-risco-planejamento.md`).

---

## 1. Resumo Executivo

- **Objetivo:** exibir o **menu nativo de comandos do Telegram** (o botão azul "Menu", à **esquerda**
  do campo de digitação), populado via `bot.set_my_commands([BotCommand(...)])`, para que os comandos
  do bot apareçam listados ao toque do usuário.
- **Escopo incluído:**
  - Registrar a lista de `BotCommand` no boot, a partir de uma **fonte única** de comandos.
  - Gerar o texto do `/start` (`MENU`) a partir dessa mesma fonte (elimina duplicação).
  - Tratar falha de rede no registro (não derrubar o polling).
  - Testes herméticos do registro e da composição da lista.
- **Escopo NÃO incluído (decisão explícita do usuário):**
  - **`ReplyKeyboardMarkup`** (teclado fixo no rodapé, como no `agendatipara-bot`) — **não** será
    implementado. O pedido é "apenas o menu principal da esquerda".
  - `set_chat_menu_button(MenuButtonDefault())` — só é necessário se um dia for definido um botão
    de menu customizado; hoje não há, então é **N/A**.
  - Qualquer escrita no `README.md` (logo, backup §2 é **N/A**).
  - Alteração de `state_manager.py`, `bot/services/`, `bot/config.py`, `publicacao.py`, `menu.py`.
- **Conclusão principal:** mudança pequena, contida em `bot/handlers/commands.py` + um teste novo.
  Único ponto sensível é tocar `create_application()` (região protegida §3.1) e o fato de
  `set_my_commands` ser chamada de rede no boot — ambos mitigados (ver §7, R1–R3).

---

## 2. Viabilidade Técnica

### O que já existe (funcionando)

- `/start` (`bot/handlers/commands.py:38`) já envia o `MENU` textual (`:13-25`) para usuários
  autorizados — permanecerá.
- Todos os comandos do `MENU` já estão registrados como handlers:
  - entry points do `ConversationHandler` (`bot/handlers/menu.py:841-846`): `nova`, `buscar`,
    `editar`, `remover` + `publicacao.entradas_publicacao()` (`publicar`, `restaurar`);
  - `CommandHandler` globais (`bot/handlers/commands.py:63-67`): `start`, `cancelar`, `listar`,
    `validar`, `historico`.
- `python-telegram-bot` 22.7 (instalado; a doc citava 22.8 — ver R9) suporta `BotCommand` e
  `ApplicationBuilder.post_init` — **sem nova dependência**.

### O que não é necessário (já existente)

- Nenhum handler novo é criado. `set_my_commands` **não** registra handler; apenas informa ao
  Telegram qual lista exibir no botão "Menu". Portanto **não há risco de interceptar updates** do
  `ConversationHandler`.

### Onde o dado é coletado e usado

- **Coleta:** constante de módulo `COMANDOS_MENU` em `bot/handlers/commands.py` (nome + descrição).
- **Uso 1:** `set_my_commands` no boot (menu nativo).
- **Uso 2:** composição do texto `MENU` do `/start` (fonte única → sem divergência).

### Impacto em cada serviço/módulo

| Módulo | Impacto |
|---|---|
| `bot/handlers/commands.py` | **Alterado** — `COMANDOS_MENU`, `post_init`, `MENU` derivado, `create_application()` |
| `bot/main.py` | **Sem alteração** — `run_polling()` já invoca `post_init` (§8: não reatribuir em `main.py`) |
| `bot/handlers/menu.py` / `publicacao.py` | **Sem alteração** |
| `bot/services/`, `bot/models/`, `bot/schemas/`, `bot/config.py` | **Sem alteração** |

---

## 3. Fluxo Detalhado

### Estados e handlers

- **Nenhum estado novo** em `bot/handlers/state_manager.py` (`EstadoConversa`, `Acao`,
  `ORDEM_POR_ACAO`) — intocados. Não há impacto em `ConversationHandler` (AGENTS.md §8).
- `create_application()` (`bot/handlers/commands.py:56`) passa a registrar `post_init` **uma única
  vez**, via builder:
  ```python
  application = (
      Application.builder()
      .token(Config.TELEGRAM_BOT_TOKEN)
      .post_init(post_init)
      .build()
  )
  ```

### Sequência no boot

```
run_polling() → initialize() → post_init(application)
                                    ↓
                        bot.set_my_commands([BotCommand(...)])   ← chamada de rede (UI do Telegram)
                                    ↓
                   sucesso → log INFO "Comandos registrados no menu do Telegram."
                   falha   → log ERROR (try/except) → polling prossegue
                                    ↓
                         getUpdates (loop normal)
```

### Estrutura proposta (em `bot/handlers/commands.py`)

```python
from telegram import BotCommand, Update

COMANDOS_MENU = [
    ("start",     "Iniciar o bot / menu principal"),
    ("nova",      "➕ Nova comunidade"),
    ("buscar",    "🔍 Buscar comunidade"),
    ("editar",    "✏️ Editar comunidade"),
    ("remover",   "🗑️ Remover comunidade"),
    ("listar",    "📋 Listar comunidades"),
    ("validar",   "🧩 Validar README"),
    ("historico", "📜 Histórico de alterações"),
    ("publicar",  "⬆️ Publicar alterações"),
    ("restaurar", "♻️ Restaurar backup"),
    ("cancelar",  "↩️ Cancelar"),
]

MENU = "📋 Menu principal:\n" + "\n".join(
    f"/{cmd} — {desc}" for cmd, desc in COMANDOS_MENU if cmd != "start"
)


async def post_init(application: Application) -> None:
    """Registra o menu nativo de comandos; não deve derrubar o polling em falha de rede."""
    try:
        await application.bot.set_my_commands(
            [BotCommand(cmd, desc) for cmd, desc in COMANDOS_MENU]
        )
        logger.info("Comandos registrados no menu do Telegram.")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar comandos no menu do Telegram")
```

> **Decisão em aberto (aprovação):** incluir `start` como **primeiro** item do menu nativo é a
> convenção do Telegram (e o `agendatipara-bot` faz assim), mas ele **não** aparece no texto `MENU`
> atual. A lista acima inclui `start` no menu nativo e o **exclui** do texto do `/start` (para não
> ficar "`/start — Iniciar o bot`" dentro do próprio `/start`). Confirmar na aprovação.

### Integração com estados existentes

- `nova`/`editar`/`remover`/`buscar`/`publicar`/`restaurar` continuam sendo **entry points**; o menu
  nativo apenas reenvia o comando textual (mesmo efeito de o usuário digitar `/nova`). Sem mudança
  de comportamento.

---

## 4. Próximos Passos

- **Ações não necessárias (já implementadas):** `/start`, todos os handlers dos comandos, guard de
  autorização (`_autorizado`, `commands.py:28`).
- **Ações obrigatórias:**
  1. Implementar `COMANDOS_MENU` + `post_init` + builder em `bot/handlers/commands.py`.
  2. Criar `bot/tests/test_commands.py` (hermético; `bot.set_my_commands` mockado com `AsyncMock`)
     cobrindo R1 (resiliência), R3 (`post_init` único), R8 (comando × handler) e R2 (ordem).
  3. Validar: `python3 -m py_compile`, import de `create_application`, `pytest bot/tests/ -v`.
  4. Atualizar `CHANGELOG.md` (`[Unreleased]`) e `prompts/nova-conversa.md` (§16), corrigindo a
     versão do PTB para 22.7 (R9).
  5. Reiniciar via systemd (`§13`) — o commit **não** faz deploy.
  6. Sugerir mensagem de commit (§12.4); **não commitar sem autorização**.

---

## 5. Referências

- **Arquivos do projeto:** `bot/handlers/commands.py`, `bot/main.py`, `bot/handlers/menu.py`,
  `bot/handlers/publicacao.py`, `bot/tests/conftest.py`, `docs/requisitos.md` (l.185, l.305-314),
  `README.md` (l.40), `prompts/nova-conversa.md`.
- **AGENTS.md:** §2 (backup — N/A), §3.1 (regiões protegidas), §7 (testes herméticos), §8
  (`create_application`/`post_init`), §9 (validação), §10 (planejamento/aprovação), §11 (checklist),
  §12 (Git/commit), §13 (deploy/systemd), §15 (CHANGELOG), §16 (encerramento).
- **Referência de padrão:** `agendatipara-bot/bot/handlers/commands.py` — `set_bot_commands`
  (l.4714) e `post_init` (l.4879). **Divergência intencional:** lá o `post_init` é chamado por
  `loop.run_until_complete` em `main.py`; aqui ele é atribuído **só** em `create_application()`
  (AGENTS.md §8).
- **Documentação complementar:** `prompts/prompt-criacao-planejamento-estrategico.md`,
  `prompts/prompt-revisao-risco-planejamento.md`.

---

## 6. Conformidade com AGENTS.md

- [x] **Backup (Seção 2):** **N/A** — nenhuma escrita no README/`repositorio/` (declarado §1/§7).
- [x] **Regiões protegidas (Seção 3.1):** toca `create_application()` → justificativa + teste + comentário.
- [x] **Testes herméticos (Seção 7):** `bot/tests/test_commands.py`; `set_my_commands` via `AsyncMock`.
- [x] **Handlers (Seção 8):** **nenhum** handler novo; `post_init` atribuído só em `create_application()`.
- [x] **Validação (Seção 9):** `py_compile` + import + `pytest bot/tests/ -v` → **270 passed**.
- [x] **Planejamento/aprovação (Seção 10):** aprovado pelo usuário; implementado.
- [x] **Checklist (Seção 11):** pré/pós alteração.
- [x] **Git/commit (Seção 12):** mensagem sugerida em §9; commit/tag concluídos (`639f202`, `45aad75`, `v0.4.0`).
- [x] **Deploy (Seção 13):** restart via systemd efetivado (R7 concluído); instância única.
- [x] **Documentação (Seções 15/16):** `CHANGELOG.md` + `prompts/nova-conversa.md`.
- [x] **Riscos:** R1–R3 (alta/média) e R8–R9 (baixas com teste) viram requisitos de aceite (§7).

---

## 7. Análise de Riscos de Funcionamento e Mitigações

Dimensões do *Prompt de Revisão de Risco*. Riscos alta/média → **REQUISITO DE ACEITE**.

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Alta** | `set_my_commands` falhar no boot (rede/Telegram fora) e **derrubar o polling** | `post_init` executado dentro de `run_polling()` (`bot/main.py:37`) | Bot não sobe / reinicia em loop (`Restart=on-failure`) | Envolver em `try/except Exception` + `logger.exception` (nunca propagar) |
| R2 | **Média** | Alterar região protegida `create_application()` sem rastreio | `bot/handlers/commands.py:56-69` | Ordem de handlers quebrada / divergência silenciosa | Nenhum handler novo; adicionar comentário `# ALTERADO [data]: <motivo>`; teste de `post_init` |
| R3 | **Média** | Reatribuir `post_init` em `main.py`, violando §8 | `bot/main.py:36-37` | Dupla atribuição / aviso PTB / ordem imprevisível | Atribuir **apenas** em `create_application()` via `.post_init()`; `main.py` intocado |
| R4 | **Baixa** | Divergência entre `MENU` (texto) e a lista nativa | `bot/handlers/commands.py:13-25` | Comando exibido no menu mas ausente no texto (ou vice-versa) | `MENU` **derivado** de `COMANDOS_MENU` (fonte única) |
| R5 | **Baixa** | Teste tocar rede / `.env` real | criação de `test_commands.py` | Teste não hermético / flaky (viola §7) | Mock `application.bot.set_my_commands` (`AsyncMock`); `config_ok` do `conftest.py` |
| R6 | **Baixa** | Descrição de comando inválida (nome/limite) | `BotCommand(cmd, desc)` | Telegram rejeita (`BadRequest`) → cai em R1 | Nomes minúsculos 1-32, descrições < 256 chars (validado no teste) |
| R7 | **Baixa** | Deploy não efetivado | serviço systemd | Menu não aparece em produção | `systemctl restart atualizar-repositorio-bot.service` (§13/§6.1) |
| R8 | **Baixa** | Lista nativa com comando sem handler correspondente | `COMANDOS_MENU` × entry points (`menu.py:841-846`) + globais (`commands.py:63-67`) | Botão no menu que não responde a nada | Teste comparando `COMANDOS_MENU` ao conjunto de comandos registrados |
| R9 | **Baixa** | Documentação cita PTB 22.8, instalado é 22.7 | `prompts/nova-conversa.md:46` | Nenhum funcional (`BotCommand`/`post_init` existem em ambos) | Alinhar a versão na doc para 22.7 |

### Requisitos de aceite

- **R1 — resiliência no boot:** falha em `set_my_commands` **não** derruba o bot.
  *Teste:* `post_init` com `bot.set_my_commands` lançando exceção → não propaga; log emitido.
- **R2 — região protegida rastreada:** comentário `# ALTERADO [data]` + `create_application()`
  inalterado no que importa (ordem dos handlers preservada).
  *Teste:* `create_application()` ainda registra o `ConversationHandler` **primeiro** e `start` depois.
- **R3 — `post_init` único:** atribuído só em `create_application()`; `application.post_init is post_init`.
  *Teste:* inspecionar `app.post_init` após `create_application()`.
- **R8 — menu sem comando inerte:** todo comando de `COMANDOS_MENU` tem handler registrado.
  *Teste:* comparar `COMANDOS_MENU` ao conjunto `{nova, buscar, editar, remover, listar, validar,
  historico, publicar, restaurar, cancelar, start}` (entry points + `CommandHandler` globais).
- **R9 — doc alinhada:** `prompts/nova-conversa.md` registra `python-telegram-bot` 22.7.
  *Teste:* inspeção na atualização do handoff (§16), sem teste automatizado.

### Risco residual aceito

- Menu é **global** (todos os usuários veem a lista) — aceitável: a autorização continua sendo
  imposta em cada handler (`_autorizado`, `commands.py:28-35`). Não há menu por escopo/perfil.
- Ordem/agrupamento de comandos no menu nativo segue a ordem de inserção de `COMANDOS_MENU`
  (o Telegram não permite cabeçalhos/grupos).

---

## Arquivos que serão alterados ou consultados

- **Alterados:**
  - `bot/handlers/commands.py` — `COMANDOS_MENU`, `post_init`, `MENU` derivado, `create_application()`.
  - `bot/tests/test_commands.py` — **novo** (registro do menu; hermético).
  - `CHANGELOG.md` — entrada em `[Unreleased]`.
  - `prompts/nova-conversa.md` — atualização do estado (§16).
- **Consultados (sem alteração):** `bot/main.py`, `bot/handlers/menu.py`,
  `bot/handlers/publicacao.py`, `bot/tests/conftest.py`, `docs/requisitos.md`, `README.md`,
  `AGENTS.md`, `agendatipara-bot/bot/handlers/commands.py`.

## Dependências e Edge Cases

- **Dependências:** apenas `telegram.BotCommand` + `ApplicationBuilder.post_init` (já em PTB 22.7);
  **sem** alteração em `requirements.txt`/`requirements-test.txt`.
- **Edge cases:**
  - E1 — Rede fora no boot: `post_init` não pode propagar exceção (R1).
  - E2 — Fonte única: `MENU` derivado de `COMANDOS_MENU` (R4). `start` no menu nativo, fora do texto.
  - E3 — Limites do Telegram: nomes minúsculos, 1-32 chars; descrições ≤ 256 chars; sem `\n` (R6).
  - E4 — `main.py` **não** reatribui `post_init` (§8, R3).
  - E5 — Nenhum handler global novo: não interfere no `ConversationHandler` (§8).
  - E6 — Deploy: só entra em produção após `systemctl restart` (R7).
  - E7 — Teste não faz rede: `set_my_commands` mockado (R5).
  - E8 — Coerência menu × handlers: todo `COMANDOS_MENU` deve ter handler (R8).
  - E9 — Versão do PTB documentada deve refletir a instalada (22.7) (R9).

## Conformidade com AGENTS.md

- [x] Backup: Seção 2 — **N/A** (sem escrita no README; §1/§7)
- [x] Regiões protegidas: Seção 3.1 — `create_application()` justificado + teste + comentário (§7, R2)
- [x] Testes herméticos: Seção 7 — `bot/tests/test_commands.py` (mock `AsyncMock`; §7, R5)
- [x] Handlers/ConversationHandler: Seção 8 — sem handler novo; `post_init` único (§7, R3)
- [x] Validação: Seção 9 — `py_compile` + import + `pytest` → **270 passed** (§4)
- [x] Planejamento (aprovação): Seção 10 — aprovado; implementado
- [x] Checklist: Seção 11 — pré/pós alteração
- [x] Git/commit: Seção 12 — mensagem em §9; commit/tag concluídos (`639f202`, `45aad75`, `v0.4.0`)
- [x] Deploy/systemd: Seção 13 — restart efetivado (R7 concluído); log "Comandos registrados no menu"; instância única
- [x] Documentação: Seções 15 e 16 — `CHANGELOG.md` + `prompts/nova-conversa.md` (R9)
- [x] Análise de Riscos: R1–R3 e R8–R9 com teste de regressão — §7

---

## 9. Git e Commits (§11, §12, §14.3)

- **Commit sob autorização (§12.1)** — não commitar por iniciativa própria.
- **Mensagem sugerida (§12.4):**
  ```
  feat: registra menu de comandos nativo do Telegram

  O /start exibia os comandos apenas como texto e o botão "Menu" do app
  ficava vazio. Registra BotCommand no post_init (fonte única COMANDOS_MENU),
  com tratamento de falha de rede para não derrubar o polling.
  ```
- **Tag (§12.6):** `v0.4.0` criada (anotada) e publicada no `origin`.

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
