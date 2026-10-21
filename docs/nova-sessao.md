# Nova sessão — continuidade do desenvolvimento

> ⚠️ **Documento histórico** (fase de construção do bot). O handoff **canônico** para iniciar uma
> nova sessão é **`prompts/nova-conversa.md`** — consulte-o primeiro.

> **Prompt para uso no chat do OpenCode (nova sessão).**
> Copie o texto da seção "Prompt" abaixo como primeira mensagem.

---

## Prompt

Leia, nesta ordem, antes de qualquer alteração:

1. `AGENTS.md` — guia de operação do projeto (backup, regiões protegidas, testes herméticos,
   `ConversationHandler`, política de Git, deploy). **É obrigatório.**
2. `docs/requisitos.md` — fonte canônica do escopo e das decisões.
3. `CHANGELOG.md` — histórico (entradas em `[Unreleased]`).
4. Este arquivo (`docs/nova-sessao.md`) — estado atual e próximos passos.

Ao terminar a leitura, **reporte o estado atual e o plano** (arquivos a criar/alterar, dependências e
edge cases) e **aguarde aprovação** antes de implementar (AGENTS.md §10).

### Contexto do projeto

- **Projeto (código do bot e docs):** `https://github.com/JosehRoberto/atualizar-repositorio-comunidades`
  (`origin`, branch `main`).
- **Repositório alvo (dados):** `https://gitlab.com/paralivre/comunidades-de-tecnologia-pa`
  — clone local em `repositorio/` (ignorado no git). O README editado é `repositorio/README.md`;
  **preservar** `repositorio/LICENSE`.
- **Projeto de referência (arquitetura, somente leitura):** `/home/roberto/projetos/agendatipara-bot`.
- **Objetivo:** bot Telegram que cadastra/edita/lista/busca/remove comunidades no `README.md` do
  repositório alvo, com backup, preview, aprovação explícita e publicação controlada.
- **Idioma:** português do Brasil. **Fuso:** `America/Belem`.

### Estado atual (já implementado e commitado)

- Git: `main` sincronizada com `origin/main`.
  - `8af47a3` — estrutura inicial (docs, `AGENTS.md`, `.gitignore`, pastas).
  - `ec67e9e` — esqueleto do bot.
  - Docs subsequentes: `e83f6fa`, `3d7e9fd`, `04125e9`, `33081da`, `dca05fd`
    (handoff, sincronização, segurança).
- `bot/`:
  - `config.py` — lê `.env` (`Config`, `validar()`), sem segredos hardcoded.
  - `main.py` — logging (silencia `httpx`/`httpcore`) + `run_polling`.
  - `handlers/commands.py` — `create_application()` (registra o `ConversationHandler` do menu
    **antes** dos comandos globais), `/start` (menu), `/cancelar` e `/listar`, guard de
    `TELEGRAM_ALLOWED_USER_IDS`, error handler.
  - `handlers/state_manager.py` — máquina de estados (`EstadoConversa`, `Acao`, `ConversaUsuario`,
    `GerenciadorEstado`); ordem de transição por ação (região protegida).
  - `handlers/menu.py` — fluxo conversacional (nova/editar/remover/buscar) com **preview** e
    aprovação (`✅/✏️/🔀/❌`); backup + escrita cirúrgica + histórico; `/validar` e `/historico`.
  - `handlers/publicacao.py` — `/publicar` (commit + push com confirmação) e `/restaurar`
    (lista backups → diff → confirmação → backup prévio + histórico).
  - `models/comunidade.py` — `Comunidade`, `Link`, `nome_normalizado()` (minúsculas, sem acentos).
  - `schemas/comunidade.py` — `ComunidadeSchema`, `LinkSchema` (pydantic v2, valida URL).
  - `services/` — implementados (região protegida): `readme_service`, `backup_service`,
    `historico_service`, `tempo`, `git_service`, `validacao_service` e `escrita_service`.
  - `atualizar-repositorio-bot.service` — unit systemd (instância única).
  - `tests/` — **235** testes herméticos (config, modelo, schemas, serviços e fluxo) **passando**.
- Raiz: `pytest.ini`, `requirements-test.txt`, `README.md`, `bot/requirements.txt`,
  `bot/.env.example`.
- `bot/.env` **configurado** (não versionado): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`
  (usuário `87681147`) e `GITLAB_TOKEN` (`comunidades-bot`) — `Config.validar()` sem problemas.
- Bot **operacional**: `create_application()` monta a aplicação e o smoke test iniciou o polling sem
  erros (bot `@atualizar_repositorio_bot`).
- Segurança: rotação do token GitLab **concluída** (token antigo revogado; exposição local removida).
- **Unit systemd instalada e ativa** (instância única); após mudanças de código, efetivar com
  `sudo systemctl restart atualizar-repositorio-bot.service`. Os itens 1–9 estão implementados e
  testados (235 testes).

### Próximos passos (ordem recomendada)

Implementar cada item **com teste hermético** antes de avançar:

1. ✅ **Serviço de parser/editor do README** — `bot/services/readme_service.py`
   (região protegida): parsear seções/âncoras, linhas `| Comunidade | Links |` e as exceções
   (`Observatório` usa `| Serviço | Link |`), badges `shields.io`, inserir/editar/remover bloco,
   **ordem alfabética** por `nome_normalizado()`, e normalização do marcador
   `:triangular_flag_on_post:` (no máximo 1; referência inicial: **Divas Digitais**).
   Formato do bloco e catálogo de badges: `docs/requisitos.md` §2.4–2.6. **Concluído** (26 testes).
2. ✅ **Serviço de backup** — `bot/services/backup_service.py` (pré-condição de escrita):
   `backup/README_YYYYMMDD_HHMMSS.bak` (fuso `America/Belem`). **Concluído** (20 testes).
3. ✅ **Serviço de histórico** — `bot/services/historico_service.py` (JSONL append-only).
   **Concluído** (15 testes; inclui `bot/services/tempo.py`).
4. ✅ **Serviço Git/GitLab** — `bot/services/git_service.py`: commit/branch/push/MR via `GITLAB_TOKEN`,
   **sem** embutir token em URL; mockar `requests`/`subprocess` nos testes. **Concluído** (24 testes).
5. ✅ **Validações** — `🧩 Validar README` e duplicidade (nome/URL): `docs/requisitos.md` §2.8.
   **Concluído** (`bot/services/validacao_service.py`, 50 testes).
6. ✅ **Fluxo conversacional** — `bot/handlers/state_manager.py` (ordem dos estados) + handlers do menu
   (nova/buscar/editar/remover/listar) com **preview** e **aprovação** (`✅/✏️/🔀/❌`).
   **Concluído** (22 testes em `test_state_manager.py` + 22 em `test_menu.py`).
7. ✅ **Publicação** — `/publicar` como etapa separada, **somente com confirmação explícita**;
   `rollback`/`/restaurar` (lista backups, diff, confirmação). **Concluído**
   (`bot/handlers/publicacao.py` + 25 testes). Inclui `/validar` e `/historico`.
8. ✅ **Multi-usuário/segurança** — `asyncio.Lock` por arquivo; `git pull --ff-only` antes de editar;
   recheck de hash antes de gravar. **Concluído** (`bot/services/escrita_service.py` + 12 testes).
9. ✅ **Deploy local (systemd)** — `.venv` criada, dependências instaladas e unit
   `bot/atualizar-repositorio-bot.service` (instância única) criada e validada
   (`systemd-analyze verify`); unit **instalada e ativa** (após mudanças de código, `restart`).

### Convenções obrigatórias (resumo)

- **Backup**: todo README alterado é copiado para `backup/` **antes** da alteração.
- **Alteração cirúrgica**: nunca reformatar outras partes do README.
- **Testes**: herméticos (sem `.env` real, sem rede, sem escrever em produção); isolar caminhos com
  `tmp_path` + `monkeypatch`; mockar `requests`, `subprocess` e a API do Telegram.
- **Regiões protegidas** (AGENTS.md §3.1): exige justificativa + teste; comentar `# ALTERADO [data]:`.
- **Git**: **não commitar por iniciativa própria** — sugerir a mensagem e aguardar autorização.
- **Segredos**: apenas em `bot/.env`; manter `bot/.env.example` atualizado.

### Comandos úteis

```bash
pytest bot/tests/ -v
python3 -m py_compile bot/<arquivo>.py
python3 -c "from bot.handlers.commands import create_application; print('OK')"
git status --short
```

### Ponto de entrada

Os itens 1–9 estão implementados e testados (235 testes). Unit systemd instalada e ativa; após
mudanças de código, reiniciar o serviço. Release publicada: tag anotada `v0.2.1` (fix do escape
Markdown).
