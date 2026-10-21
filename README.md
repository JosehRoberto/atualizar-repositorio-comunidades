# Atualização do Repositório de Comunidades

Bot Telegram que cadastra, edita, lista, busca e remove comunidades de tecnologia no `README.md` do
repositório [paralivre/comunidades-de-tecnologia-pa](https://gitlab.com/paralivre/comunidades-de-tecnologia-pa),
com backup, preview, aprovação explícita e publicação controlada.

## Objetivo

Facilitar a atualização do README do repositório alvo sem edição manual, preservando integralmente a
estrutura e a formatação Markdown existentes.

## Instalação

```bash
python3 -m venv .venv
.venv/bin/pip install -r bot/requirements.txt
.venv/bin/pip install -r requirements-test.txt
```

## Configuração

Copie `bot/.env.example` para `bot/.env` e preencha os valores (ver tabela abaixo). **Nunca** commite
o `.env`.

| Variável | Descrição |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token do bot Telegram |
| `TELEGRAM_ALLOWED_USER_IDS` | IDs autorizados (separados por vírgula) |
| `GITLAB_TOKEN` | Personal Access Token do GitLab |
| `GITLAB_USERNAME` | usuário da URL autenticada (padrão `oauth2`) |
| `GIT_REPO_URL` | URL do repositório alvo |
| `GIT_BRANCH` | branch base (padrão `master`) |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | identidade dos commits |
| `README_PATH` | caminho do README (padrão `repositorio/README.md`) |
| `BACKUP_DIR` | pasta de backups (padrão `backup`) |
| `TIMEZONE` | fuso horário (padrão `America/Belem`) |

## Comandos

- `/start` — menu principal
- `/nova` — cadastrar comunidade (nome → links → seção → preview → aprovação)
- `/buscar` — buscar comunidade
- `/editar` — editar comunidade (nome e/ou links; ou escolher pela lista de seções/comunidades)
- `/remover` — remover comunidade
- `/listar` — listar comunidades por seção
- `/validar` — validar o README (tabelas, âncoras, duplicidades, marcador)
- `/historico` — últimas alterações registradas
- `/publicar` — commit + push (com confirmação explícita)
- `/restaurar` — restaurar um backup (lista → diff → confirmação)
- `/cancelar` — encerra a operação atual

Todos os comandos também aparecem no **menu nativo do Telegram** (botão «Menu», à esquerda do campo
de digitação), registrado no boot via `set_my_commands`.

> **Fluxo edição → publicação:** as edições gravam o README no clone local e ficam **pendentes** até
> o `/publicar`. Enquanto houver alterações não publicadas, `/nova`, `/editar` e `/remover` são
> bloqueados (use `/publicar` ou `/restaurar`). O `/publicar` commita a edição pendente e sincroniza
> com o remoto (`fetch` + `pull --rebase`) antes do `push`.

## Uso

```bash
.venv/bin/python -m bot.main
```

## Estrutura do projeto

```
atualizar-repositorio-comunidades/
├── bot/                  ← código (config, main, handlers, models, schemas, services, tests)
├── backup/               ← backups (README_YYYYMMDD_HHMMSS.bak) — não versionado
├── docs/                 ← requisitos, planejamentos
├── prompts/              ← handoff para nova sessão (nova-conversa.md)
└── repositorio/          ← clone do repositório alvo (GitLab) — não versionado
```

## Política de backup

Todo README alterado é copiado para `backup/README_YYYYMMDD_HHMMSS.bak` (fuso `America/Belem`)
**antes** da alteração. Rollback: `cp backup/README_<TS>.bak repositorio/README.md`.

## Testes

```bash
pytest bot/tests/ -v
pytest bot/tests/ --cov=bot --cov-report=term-missing
```

## Deploy (systemd)

Instalação (uma vez):

```bash
sudo cp bot/atualizar-repositorio-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atualizar-repositorio-bot.service
```

Operação:

```bash
sudo systemctl restart atualizar-repositorio-bot.service && sleep 3
sudo systemctl status atualizar-repositorio-bot.service
sudo journalctl -u atualizar-repositorio-bot.service -n 30 --no-pager
```

Mantenha **instância única** (duas instâncias causam `409 Conflict` no `getUpdates`).

## Rollback

- Arquivo: `cp backup/README_<TS>.bak repositorio/README.md`.
- Código: `git revert <commit>` (preserva o histórico).

## Documentação

- Escopo e decisões: `docs/requisitos.md`.
- Guia de operação para agentes: `AGENTS.md`.
- Histórico de mudanças: `CHANGELOG.md`.
- Handoff para nova sessão: `prompts/nova-conversa.md`.
