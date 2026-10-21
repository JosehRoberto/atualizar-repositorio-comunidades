# Changelog

> Convenção: skill `changelog-convention` (ou `docs/changelog-convention.md`).
> Ordem **cronológica decrescente**; **não** misturar séries de numeração sem a nota + divisor.

## [Unreleased]

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
