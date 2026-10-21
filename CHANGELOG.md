# Changelog

> Convenção: skill `changelog-convention` (ou `docs/changelog-convention.md`).
> Ordem **cronológica decrescente**; **não** misturar séries de numeração sem a nota + divisor.

## [Unreleased]

### v0.4.0 (21/10/2026) — Menu nativo de comandos do Telegram

- **Adicionado:** `bot/handlers/commands.py` — constante `COMANDOS_MENU` (fonte única) e `post_init`,
  que registra o **menu nativo de comandos** do Telegram via
  `bot.set_my_commands([BotCommand(...)])`; o botão "Menu" (à esquerda do campo de digitação) passa a
  listar todos os comandos do bot.
- **Alterado:** `bot/handlers/commands.py` — o texto do `/start` (`MENU`) agora é **derivado** de
  `COMANDOS_MENU` (elimina duplicação); `create_application()` registra o `post_init` **uma única vez**
  no builder.
- **Região protegida (§3.1):** `create_application()` — comentário `# ALTERADO [21/10/2026]`; nenhum
  handler novo, ordem de registro preservada.
- **Robustez:** falha de rede em `set_my_commands` no boot é capturada (`try/except`) e **não**
  derruba o polling.
- **Testes:** +12 herméticos (`bot/tests/test_commands.py`; `set_my_commands` mockado). Suíte em **270**.
- **Validado:** `py_compile` OK; import de `create_application` OK; `pytest bot/tests/` → **270 passed**.
- **Planejamento:** `docs/planejamento-menu-comandos-telegram.md` (v1.1, riscos R1–R9).
- **Validado em produção:** restart systemd efetivado; log `Comandos registrados no menu do Telegram`;
  sem `409`/erros.
- **Arquivos:** `bot/handlers/commands.py`, `bot/tests/test_commands.py`.

## [0.3.0] - 2026-10-21

### Adicionado (21/10/2026) — Busca fuzzy com candidatos numerados (§2.10)

- **Adicionado:** `bot/services/busca_service.py` — chave de busca sem acentos, emojis e pontuação;
  pontuação por igualdade, substring e cobertura de tokens (`difflib`, limiar `0,6`); lista
  ranqueada com até 5 candidatos e desempate por URL em nomes homônimos.
- **Alterado:** `bot/handlers/menu.py` — `/buscar` exibe os candidatos em texto; `/editar` e
  `/remover` passam a oferecer botões numerados quando não há match exato, com seleção automática
  quando existe apenas um candidato; nova tentativa por texto continua disponível.
- **Alterado:** `bot/handlers/state_manager.py` (região protegida) — estados
  `EDITAR_CANDIDATOS` e `REMOVER_CANDIDATOS` e campo `candidatos` na conversa; a ordem canônica
  permanece a mesma quando não há desvio fuzzy (§3.1).
- **Testes:** +23 herméticos (`test_busca_service.py` = 14, `test_menu.py` = 9). Suíte em **258**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **258 passed**; busca real no clone
  (`aws castanha` → *AWS User Group Castanhal*; `divas digital` → *Divas Digitais*).
- **Arquivos:** `bot/services/busca_service.py`, `bot/handlers/menu.py`,
  `bot/handlers/state_manager.py`, `bot/tests/test_busca_service.py`, `bot/tests/test_menu.py`.

## [0.2.1] - 2026-10-21

### Corrigido (21/10/2026) — Escape Markdown nas mensagens do bot

- **Corrigido:** `bot/handlers/menu.py` — escapa valores dinâmicos (nome de comunidade, seção e URL)
  com `telegram.helpers.escape_markdown(version=1)` nas mensagens enviadas com
  `parse_mode="Markdown"`; URLs com `_` (15 no README) quebravam o envio com
  `Can't parse entities`. O escape é aplicado apenas **fora** de code span; os valores do modelo
  permanecem intactos (README não é corrompido).
- **Região protegida (§3.1):** `texto_preview` (preview/aprovação) — comentário
  `# ALTERADO [21/10/2026]`.
- **Testes:** +3 herméticos (`bot/tests/test_menu.py`) — URL com `_`, preview preservando code span
  e persistência sem corromper o README. Suíte em **235**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **235 passed**.
- **Arquivos:** `bot/handlers/menu.py`, `bot/tests/test_menu.py`.

### Documentação (21/10/2026) — Planejamento de correção e prompts de planejamento/revisão de risco

- **Adicionado:** `docs/planejamento-correcao-markdown-escape.md` (v1.1) — planejamento de correção
  do erro `Can't parse entities`: diagnóstico (§14.1), causa raiz, correção proposta, análise de
  riscos R1–R4 com testes de regressão e conformidade com o `AGENTS.md`.
- **Adicionado:** `prompts/prompt-criacao-planejamento-correcao-bug.md`,
  `prompts/prompt-criacao-planejamento-estrategico.md` e
  `prompts/prompt-revisao-risco-planejamento.md` — prompts padronizados, adaptados à realidade e ao
  contexto deste projeto.
- **Arquivos:** `docs/planejamento-correcao-markdown-escape.md`, `prompts/prompt-criacao-planejamento-correcao-bug.md`,
  `prompts/prompt-criacao-planejamento-estrategico.md`, `prompts/prompt-revisao-risco-planejamento.md`.

### Documentação (21/10/2026) — Handoff canônico refletido em `AGENTS.md` e no prompt

- **Alterado:** `AGENTS.md §16` — passa a exigir manter o handoff canônico
  `prompts/nova-conversa.md` atualizado (`docs/nova-sessao.md` permanece como histórico).
- **Alterado:** `prompts/nova-conversa.md` — a seção "Últimas mudanças (resumo)" inclui o commit do
  handoff (`f9f59ab`) e mantém as 3 atualizações mais recentes.
- **Arquivos:** `AGENTS.md`, `prompts/nova-conversa.md`.

### Documentação (21/10/2026) — Prompt de continuidade canônico (`prompts/nova-conversa.md`)

- **Adicionado:** `prompts/nova-conversa.md` — handoff canônico para abrir uma nova sessão do
  OpenCode, com a mesma estrutura/metodologia de `agendatipara-bot/prompts/nova-conversa.md`:
  prompt inicial (lista de leitura), visão geral, estrutura, estado atual, fluxo, regras técnicas
  críticas, comandos do terminal, regras do agente, fluxo de atualização/deploy, próximos passos,
  soluções encontradas e ponteiro para o `CHANGELOG.md`.
- **Migrado:** detalhe do usuário autorizado (`TELEGRAM_ALLOWED_USER_IDS` = `87681147`) de
  `docs/nova-sessao.md` para o novo documento; `docs/nova-sessao.md` permanece como handoff anterior.
- **Alterado:** `docs/requisitos.md §6` passa a apontar `prompts/nova-conversa.md` como handoff
  canônico da próxima sessão.
- **Alterado:** `docs/nova-sessao.md` — nota de cabeçalho marcando-o como documento histórico
  (fase de construção), com o handoff canônico em `prompts/nova-conversa.md`.
- **Alterado:** `README.md` — a estrutura do projeto passa a listar `prompts/` e a seção
  "Documentação" cita o handoff para nova sessão.
- **Arquivos:** `prompts/nova-conversa.md`, `docs/requisitos.md`, `docs/nova-sessao.md`, `README.md`.

## [0.2.0] - 2026-10-21

### Corrigido (21/10/2026) — `PTBUserWarning` no log do serviço

- **Corrigido:** `bot/main.py` — silencia (de forma específica) o `PTBUserWarning` esperado ao
  misturar `MessageHandler` e `CallbackQueryHandler` no `ConversationHandler` (`per_message=False`),
  mantendo o log do serviço limpo.
- **Validado:** `create_application()` sem o aviso; `pytest bot/tests/` → **232 passed**.
- **Arquivos:** `bot/main.py`.

### Adicionado (21/10/2026) — Deploy systemd (unit e `.venv`)

- **Adicionado:** `bot/atualizar-repositorio-bot.service` — unit systemd (instância única,
  `WorkingDirectory` no projeto, `ExecStart=.venv/bin/python -m bot.main`, `EnvironmentFile=bot/.env`,
  `Restart=on-failure`).
- **Alterado:** `README.md` — lista completa de comandos e passos de instalação/operação do serviço.
- **Validado:** `systemd-analyze verify` sem erros; `.venv` criada e dependências instaladas
  (`python-telegram-bot 22.8`); `create_application()` monta a aplicação na `.venv`; suíte em **232**.
- **Pendente (requer `sudo`, usuário):** copiar a unit para `/etc/systemd/system/`, `daemon-reload` e
  `enable --now`.
- **Arquivos:** `bot/atualizar-repositorio-bot.service`, `README.md`.

### Adicionado (21/10/2026) — Concorrência e proteção de escrita (`escrita_service`)

- **Adicionado:** `bot/services/escrita_service.py` (região protegida) — `asyncio.Lock` global de
  escrita (`lock_escrita`/`ocupado`), `sincronizar_seguro` (`fetch` + `pull --ff-only`; aborta em
  conflito) e `conferir_hash` (recheck do hash do README antes de gravar) — §2.12.
- **Alterado:** `bot/handlers/state_manager.py` (região protegida) — campo `hash_base` em
  `ConversaUsuario`.
- **Alterado:** `bot/handlers/menu.py` — o preview grava o hash; `aprovacao` e
  `remover_confirmacao` adquirem o lock, sincronizam e reconferem o hash antes de gravar, com aviso
  "aguarde" ao segundo usuário.
- **Alterado:** `bot/handlers/publicacao.py` — `/publicar` passa a operar sob o mesmo lock.
- **Testes:** +12 herméticos (`bot/tests/test_escrita_service.py` = 10 + 2 em `test_menu.py`).
  Suíte em **232**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **232 passed**.
- **Arquivos:** `bot/services/escrita_service.py`, `bot/handlers/state_manager.py`,
  `bot/handlers/menu.py`, `bot/handlers/publicacao.py`, `bot/tests/test_escrita_service.py`,
  `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py`.

### Adicionado (21/10/2026) — Publicação e restauração (`publicacao`)

- **Adicionado:** `bot/handlers/publicacao.py` (região protegida) — `/publicar` (sincroniza, mostra
  as alterações pendentes e, **somente após confirmação explícita**, faz `commit` + `push`; token
  fora da URL e sem `reset --hard`) e `/restaurar` (lista os backups, mostra o **diff**, exige
  confirmação e restaura com backup prévio `README_pre-restauracao_*.bak`). Ambos registram no
  histórico JSONL.
- **Adicionado:** `GitService.alteracoes()` — lista as alterações pendentes (`git status --porcelain`).
- **Alterado:** `bot/handlers/state_manager.py` (região protegida) — ações `PUBLICAR`/`RESTAURAR` e
  estados `PUBLICAR_CONFIRMACAO`, `RESTAURAR_ESCOLHA`, `RESTAURAR_CONFIRMACAO`.
- **Alterado:** `bot/handlers/menu.py` — mescla os fluxos de publicação/restauração no
  `ConversationHandler` e adiciona `/validar` e `/historico`; `bot/handlers/commands.py` registra os
  comandos e atualiza o menu de `/start`.
- **Testes:** +25 herméticos (`bot/tests/test_publicacao.py` = 23 + 2 em `test_git_service.py`).
  Suíte em **220**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **220 passed**.
- **Arquivos:** `bot/handlers/publicacao.py`, `bot/handlers/state_manager.py`, `bot/handlers/menu.py`,
  `bot/handlers/commands.py`, `bot/services/git_service.py`, `bot/tests/test_publicacao.py`,
  `bot/tests/test_git_service.py`, `bot/tests/test_state_manager.py`.

### Adicionado (21/10/2026) — Handlers do menu e fluxo conversacional (`menu`)

- **Adicionado:** `bot/handlers/menu.py` — consome a máquina de estados e conduz o fluxo
  conversacional do Telegram: **nova** (nome → links → seção → preview → aprovação),
  **editar** (busca → escolha do campo → novo valor → preview → aprovação),
  **remover** (busca → confirmação) e **buscar** (consulta somente leitura). Gera o **preview**
  a partir do rascunho e trata a aprovação (`✅ Aprovar`, `✏️ Editar`, `🔀 Trocar seção`, `❌ Cancelar`).
  Inclui backup + escrita cirúrgica no README e registro de histórico, com guarda de
  `TELEGRAM_ALLOWED_USER_IDS`.
- **Testes:** +22 herméticos (`bot/tests/test_menu.py`) — transições de estado, coleta de dados,
  preview, aprovação/edição/cancelamento e caminhos de erro. API do Telegram, serviços de arquivo
  e backup mockados/isolados. Suíte em **191**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **191 passed**.
- **Arquivos:** `bot/handlers/menu.py`, `bot/tests/test_menu.py`.

### Adicionado (21/10/2026) — Máquina de estados do fluxo conversacional (`state_manager`)

- **Adicionado:** `bot/handlers/state_manager.py` (região protegida) — define `EstadoConversa`,
  `Acao`, `ConversaUsuario` e `GerenciadorEstado`; mantém o rascunho e a posição no fluxo por
  usuário e calcula a **ordem de transição** de cada ação (nova/editar/remover/buscar), com a
  ramificação de edição em `EDITAR_ESCOLHA` (nome/links/ambos). Lógica pura, sem I/O nem dependência
  do Telegram.
- **Testes:** +22 herméticos (`bot/tests/test_state_manager.py`) — criação/reset de conversa,
  `iniciar`/`encerrar`, ordem dos estados e ramificações de edição. Suíte em **169**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **169 passed**.
- **Arquivos:** `bot/handlers/state_manager.py`, `bot/tests/test_state_manager.py`.

### Adicionado (21/10/2026) — Serviço de validações (`validacao_service`)

- **Adicionado:** `bot/services/validacao_service.py` (região protegida) — validações de §2.8:
  campos obrigatórios (nome, ≥1 link), URLs válidas (`http`/`https`/`tg`; `normalizar_url` remove
  espaços e exige esquema), duplicidade de **nome** e **URL** (bloqueia exata, alerta similaridade
  ≥ 0,85), existência/editabilidade da seção e pendências do fluxo. Inclui **`validar_readme`**
  (`🧩 Validar README`: integridade de tabelas, âncoras da navegação × seções, duplicidades, URLs
  inválidas e coerência do marcador) e **`comparar_estrutura`** (garante edição cirúrgica).
  Relatório por severidade (`erro`/`aviso`) com `Relatorio.ok`.
- **Testes:** +50 herméticos (`bot/tests/test_validacao_service.py`) — URLs válidas/inválidas,
  similares, duplicidades, seção não editável, varredura completa e comparação de estrutura.
  Suíte em **147**.
- **Validado:** `py_compile` OK; varredura real do `repositorio/README.md` → 2 erros legítimos
  (URL do Discord repetida entre *AWS User Group Castanhal* e *XibéSec*; 9 comunidades marcadas),
  zero falsos positivos; `pytest bot/tests/` → **147 passed**.
- **Arquivos:** `bot/services/validacao_service.py`, `bot/tests/test_validacao_service.py`.

### Adicionado (21/10/2026) — Serviço Git/GitLab (`git_service`)

- **Adicionado:** `bot/services/git_service.py` (região protegida) — `GitService` com
  `fetch`/`pull --ff-only` (sincronização, §2.12), `commit` (define autor), `criar_branch`, `push`
  via URL autenticada montada **em runtime** (token **fora** do remote, `credential.helper=`) e
  `criar_merge_request` pela API v4 (header `PRIVATE-TOKEN`). Helpers de hash
  (`hash_conteudo`/`hash_arquivo`) para recheck antes de gravar. Token **mascarado** em erros;
  `subprocess`/`requests` isoláveis por mock.
- **Testes:** +24 herméticos (`bot/tests/test_git_service.py`) — URL autenticada/escape, hashes,
  execução Git, commit/branch/push e Merge Request (API), além dos caminhos de erro.
  `subprocess`/`requests` mockados. Suíte em **97**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **97 passed**.
- **Arquivos:** `bot/services/git_service.py`, `bot/tests/test_git_service.py`.

### Adicionado (21/10/2026) — Serviço de histórico e utilitário de tempo

- **Adicionado:** `bot/services/historico_service.py` — registro **JSONL append-only**
  (`bot/history/historico.jsonl`) com os campos `timestamp`, `usuario_id`, `acao`, `secao`,
  `comunidade`, `antes`, `depois`, `backup_path`, `commit`; `ler_historico`, `ultimos`, `contar`
  e `RegistroHistorico` (dataclass). Linhas corrompidas levantam `HistoricoCorrompido`.
- **Adicionado:** `bot/services/tempo.py` — `fuso_belem()`, `timestamp_belem()` e `agora_iso()`
  (fuso `America/Belem`), extraídos de `backup_service` para reuso (sem duplicação).
- **Alterado:** `bot/services/backup_service.py` passa a importar `timestamp_belem` de `tempo.py`
  (comportamento preservado).
- **Testes:** +15 herméticos (`bot/tests/test_historico_service.py`) — append, campos/ordem,
  timestamp automático/explicito, round-trip, linhas vazias/corrompidas e `ultimos`/`contar`.
  Suíte em **73**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **73 passed**.
- **Arquivos:** `bot/services/historico_service.py`, `bot/services/tempo.py`,
  `bot/services/backup_service.py`, `bot/tests/test_historico_service.py`.

### Adicionado (21/10/2026) — Serviço de backup (`backup_service`)

- **Adicionado:** `bot/services/backup_service.py` (região protegida) — `criar_backup`
  (`<nome>_YYYYMMDD_HHMMSS.bak`, fuso `America/Belem`), `listar_backups`/`ultimo_backup`
  (mais recente primeiro, por timestamp do nome), `limpar_antigos` (mantém as últimas N sessões),
  `diff_backup` (preview de restauração) e `restaurar_backup` (gera backup
  `_pre-restauracao_<ts>.bak` antes de restaurar). Sem `.env` nem rede — recebe caminhos explícitos.
- **Testes:** +20 herméticos (`bot/tests/test_backup_service.py`) — timestamp, criação/nome/conteúdo,
  listagem/ordenação, limpeza, diff e restauração. Suíte em **58**.
- **Validado:** `py_compile` OK; `pytest bot/tests/` → **58 passed**.
- **Arquivos:** `bot/services/backup_service.py`, `bot/tests/test_backup_service.py`.

### Adicionado (21/10/2026) — Parser/editor do README (`readme_service`)

- **Adicionado:** `bot/services/readme_service.py` (região protegida) — parse do README em
  seções/âncoras/tabelas, detecção de schema (`| Comunidade | Links |` × `| Serviço | Link |`),
  leitura e escrita de linhas `| **Nome** | badges |`, inserção/edição/remoção em **ordem
  alfabética** (`nome_normalizado`), badges na **ordem canônica** com renderização shields.io e
  normalização do marcador `:triangular_flag_on_post:` (no máximo 1; referência **Divas Digitais**).
  Edição **cirúrgica**: só as linhas alvo são reescritas.
- **Testes:** +26 herméticos (`bot/tests/test_readme_service.py`) — parse, round-trip, ordenação de
  badges, inserir/editar/remover, migração do marcador, seção não editável (Observatório) e I/O com
  `tmp_path`. Suíte em **38**.
- **Validado:** `py_compile` OK; round-trip idêntico no `repositorio/README.md` (17 seções, 70
  comunidades, 16 itens de navegação); `pytest bot/tests/` → **38 passed**.
- **Arquivos:** `bot/services/readme_service.py`, `bot/tests/test_readme_service.py`.

### Documentação (21/10/2026) — Nomes do bot e da unit systemd padronizados

- **Alterado:** `docs/requisitos.md §2.15` — username `@atualizar_repositorio_bot` e unit
  `atualizar-repositorio-bot.service`; `AGENTS.md` (§13) e `README.md` passam a usar o nome concreto
  da unit (fim do placeholder `<nome>-bot.service`).
- **Arquivos:** `docs/requisitos.md`, `AGENTS.md`, `README.md`.

### Documentação (21/10/2026) — Handoff reflete o bot operacional

- **Alterado:** `docs/nova-sessao.md` — `bot/.env` completo e validado, bot operacional (smoke test),
  lista de commits atualizada e novo item de deploy (systemd).
- **Alterado:** `docs/requisitos.md §6` — item 9 passa a citar só a unit systemd (`.env` ok).
- **Arquivos:** `docs/nova-sessao.md`, `docs/requisitos.md`.

### Documentação (21/10/2026) — `docs/nova-sessao.md` sincronizado

- **Alterado:** `Estado atual` atualizado — commits de docs, `bot/.env` já existente (com
  `GITLAB_TOKEN` validado; faltam as variáveis do Telegram) e rotação do token concluída.
- **Arquivos:** `docs/nova-sessao.md`.

### Segurança (21/10/2026) — Rotação do token GitLab concluída

- **Segurança:** token antigo **revogado**; exposição local eliminada (`~/.git-credentials`, URL do
  remote do clone antigo e backup removidos). Novo token `comunidades-bot` (`api`,
  `write_repository`; expira em 20/10/2027) validado via API (`/personal_access_tokens/self`, HTTP 200)
  e cadastrado em `bot/.env` (ignorado).
- **Arquivos:** `docs/requisitos.md` (§3 item 4).

### Segurança (21/10/2026) — Exposição local do token GitLab removida

- **Segurança:** token removido de `~/.git-credentials` (backup com permissão `600`) e da URL do
  remote do clone antigo (`~/projetos/paralivre/comunidades-de-tecnologia-pa`). `bot/.env` criado
  (ignorado pelo git).
- **Pendente:** revogar o token antigo no GitLab e cadastrar o novo (scope `api`) em `bot/.env`.
- **Arquivos:** `docs/requisitos.md` (§3 item 4).

### Documentação (21/10/2026) — `docs/requisitos.md` sincronizado

- **Alterado:** `§6 Próximos passos` atualizado (concluído vs. em andamento, com os commits).
- **Alterado:** `§5` passou a listar `BACKUP_DIR`, alinhado a `bot/config.py` e `bot/.env.example`.
- **Arquivos:** `docs/requisitos.md`.

### Documentação (21/10/2026) — Prompt de continuidade para nova sessão

- **Adicionado:** `docs/nova-sessao.md` — prompt de handoff para uma nova sessão do OpenCode com
  contexto, estado atual, próximos passos ordenados e convenções obrigatórias.
- **Arquivos:** `docs/nova-sessao.md`.

### v0.1.0 (21/10/2026) — Estrutura inicial e esqueleto do bot

- **Adicionado:** commit inicial do projeto (`8af47a3`) — `.gitignore`, `AGENTS.md`, `CHANGELOG.md`,
  `docs/` e estrutura base (`bot/`, `backup/`, `docs/`).
- **Adicionado:** esqueleto do bot em `bot/` — `config.py` (lê `.env`), `main.py`,
  `handlers/commands.py` (`create_application()` + `/start` e `/cancelar`), `models/comunidade.py`
  (nome + links, com chave normalizada), `schemas/comunidade.py` (pydantic v2), `services/` e `tests/`.
- **Adicionado:** `bot/requirements.txt`, `bot/.env.example`, `pytest.ini`, `requirements-test.txt`
  e `README.md` do projeto.
- **Testes:** 12 (config, modelo de domínio e schemas) — herméticos, sem rede nem `.env` real.
- **Validado:** `py_compile` OK; `from bot.handlers.commands import create_application` OK;
  `pytest bot/tests/` → **12 passed**.
- **Arquivos:** `bot/**`, `pytest.ini`, `requirements-test.txt`, `README.md`.

### Skill (21/10/2026) — `eval-3` discriminante (iteration-2)

- **Alterado:** `eval-3` da skill `criacao-bot-telegram` reescrito (prompt menos prescritivo e
  assertions sobre o "como"); revalidado só esse caso.
- **Validado:** `iteration-2` — with-skill **7/7 (100%)** vs baseline **4/7 (57%)**, delta **+0.43**
  (antes: 100% × 100%). Publicado no repo da skill (commit `135e50f`).
- **Arquivos:** externo ao repo do projeto (`~/projetos/criacao-bot-telegram/evals/evals.json`).

### Documentação (21/10/2026) — Metodologia convertida em ponteiro para a skill

- **Alterado:** `docs/metodologia-projeto-bot-telegram.md` reduzido a **ponteiro** para a skill
  `criacao-bot-telegram` (nome, repo, caminho global, quando é acionada e uso rápido do
  `bootstrap.py`), eliminando a duplicação do passo a passo.
- **Backup:** cópia integral do doc antecessor em `backup/metodologia-projeto-bot-telegram_*.bak`.
- **Arquivos:** `docs/metodologia-projeto-bot-telegram.md`.

### Skill (21/10/2026) — Draft da skill `criacao-bot-telegram`

- **Adicionado:** skill global em `~/.config/opencode/skills/criacao-bot-telegram/` com `SKILL.md`,
  `references/` (fase-requisitos, arquitetura-bot, politicas, deploy-systemd), `assets/templates/`
  (AGENTS, CHANGELOG, requisitos, prompt-inicial, gitignore, requirements, pytest, env.example),
  `scripts/bootstrap.py` e `evals/evals.json`.
- **Validado:** `bootstrap.py` compila (`py_compile`), gera a estrutura e substitui placeholders;
  idempotente e com `--dry-run`. `evals.json` válido (3 evals).
- **Nota:** a skill vive **fora** do repositório do projeto, em
  `~/projetos/criacao-bot-telegram` (repo git `github.com/JosehRoberto/criacao-bot-telegram`), com
  `~/.config/opencode/skills/criacao-bot-telegram` como **symlink**. Não é versionada no repo do projeto.
- **Pendente:** otimizar a `description` da skill (via `run_loop.py`).
- **Validado (21/10/2026):** rodada de evals `iteration-1` — with-skill **100%** vs baseline **67%**
  (delta **+0.33**); feedback do viewer vazio. Skill publicada em
  `github.com/JosehRoberto/criacao-bot-telegram` (commit `963bff2`, tag anotada `v0.1.0`).
- **Arquivos:** `~/.config/opencode/skills/criacao-bot-telegram/**` (externo ao repo do projeto).

### Documentação (21/10/2026) — Planejamento da skill de criação de bots Telegram

- **Adicionado:** `docs/planejamento-skill-criacao-bot-telegram.md` — plano para transformar a
  metodologia em uma skill reutilizável (via `skill-creator`): objetivo, anatomia
  (`SKILL.md`/`references`/`assets`/`scripts`), local de criação, `description` de trigger,
  casos de teste, riscos e decisões pendentes. **Nada da skill foi criado.**
- **Decisões:** nome `criacao-bot-telegram`; local global
  (`~/.config/opencode/skills/`); `scripts/bootstrap.py` **incluído** (mínimo, idempotente,
  `--dry-run`); `docs/metodologia-projeto-bot-telegram.md` vira **ponteiro** após a skill validada
  (paralelo durante o desenvolvimento).
- **Arquivos:** `docs/planejamento-skill-criacao-bot-telegram.md`.

### Documentação (21/10/2026) — Metodologia de criação de bots Telegram

- **Adicionado:** `docs/metodologia-projeto-bot-telegram.md` — referência reutilizável para iniciar
  um novo bot Telegram: fases (objetivo → requisitos → estrutura → `AGENTS.md` → `CHANGELOG.md` →
  esqueleto → testes → deploy), templates (`AGENTS.md`, `CHANGELOG.md`, `.gitignore`, prompt inicial),
  checklists de kickoff e distinção entre o que é genérico × específico.
- **Arquivos:** `docs/metodologia-projeto-bot-telegram.md`.

### Documentação (21/10/2026) — `AGENTS.md` alinhado ao padrão do `agendatipara-bot`

- **Alterado:** `AGENTS.md` expandido com as boas práticas do projeto de referência: regiões
  protegidas, isolamento de testes, regras de `ConversationHandler`, checklist pré/pós-alteração,
  planejamento estratégico, validação, manutenção de `backup/`, protocolos de diagnóstico/
  refatoração e **política de versionamento e tags** (`vX.Y[.Z]` anotada, `deploy validado: …`).
- **Alterado:** `CHANGELOG.md` — confirmada a mesma estratégia de versões do `agendatipara-bot`
  (marcos `### vX.Y (DD/MM/AAAA)` sob `## [Unreleased]` + `## Legenda`).
- **Arquivos:** `AGENTS.md`, `CHANGELOG.md`.

### v0.1.0 (21/10/2026) — Base do projeto

- **Adicionado:** documento de requisitos e decisões de escopo (`docs/requisitos.md`).
- **Adicionado:** repositório git do projeto (branch `main`) com remote `origin` para
  `https://github.com/JosehRoberto/atualizar-repositorio-comunidades`.
- **Adicionado:** `.gitignore` — ignora `repositorio/` (clone aninhado), `backup/*.bak`, `.env`,
  caches Python, estado/histórico do bot e logs.
- **Adicionado:** clone local do repositório alvo em `repositorio/`
  (`https://gitlab.com/paralivre/comunidades-de-tecnologia-pa`, branch `master`, commit `9f6cece`);
  contém `README.md` e `LICENSE`.
- **Adicionado:** `backup/.gitkeep` e `bot/.gitkeep` para versionar a estrutura base.
- **Adicionado:** `AGENTS.md` (guia de operação para agentes de IA) e `CHANGELOG.md` inicial.
- **Arquivos:** `.gitignore`, `AGENTS.md`, `CHANGELOG.md`, `docs/requisitos.md`,
  `docs/prompt-inicial.md`, `repositorio/` (clone), `backup/`, `bot/`.
- **Status:** estruturação inicial concluída; código-fonte do bot ainda não iniciado.

---

## Legenda

- **Adicionado** — novas funcionalidades
- **Alterado** — mudanças em funcionalidades existentes
- **Corrigido** — correções de bugs
- **Removido** — funcionalidades removidas
- **Segurança** — correções de vulnerabilidades
- **Obsoleto** — funcionalidades marcadas para remoção futura
