# Contexto do Projeto: Atualização do Repositório de Comunidades

> **Use este arquivo para iniciar qualquer nova conversa sobre este projeto.**
> Ele contém o estado atual completo — leia-o integralmente antes de qualquer ação.

> **Para iniciar uma nova sessão com IA, copie este prompt:**
>
> "Leia os seguintes arquivos para entender o estado atual do projeto Atualização do
> Repositório de Comunidades:
> 1. prompts/nova-conversa.md - Estado atual do bot, arquitetura, fluxo, decisões e próximos passos
> 2. docs/requisitos.md - Escopo completo, decisões confirmadas e regras de negócio do README
> 3. AGENTS.md - Regras para alterações (backup, regiões protegidas, testes herméticos, Git, deploy)
> 4. CHANGELOG.md - Histórico de versões (entradas em `[Unreleased]`)
> Após ler estes arquivos, reporte o estado atual e o plano (arquivos a criar/alterar, dependências
> e edge cases) e aguarde aprovação antes de implementar."

---

> **Pasta autoritativa (21/10/2026):** `/home/roberto/projetos/atualizar-repositorio-comunidades`.
> O bot roda desta pasta via systemd, com venv dedicada (`.venv/`). A pasta antiga
> `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa` está **descontinuada**. O README
> alvo é sempre o do clone `repositorio/README.md`. Testes: `pytest bot/tests/` (herméticos, sem
> `.env` real, sem rede).

## 1. Visão Geral

Bot do Telegram (`@atualizar_repositorio_bot`) para cadastrar, editar, listar, buscar e remover
comunidades de tecnologia no `README.md` do repositório alvo, **sem edição manual** do arquivo.
O bot opera sobre um clone local do repositório alvo, preservando integralmente a estrutura e a
formatação Markdown existentes, com backup, preview, aprovação explícita e publicação controlada.

**Arquitetura: Desktop (roberto-minipc) via systemd**
- Bot: systemd (`atualizar-repositorio-bot.service`) + `.venv/` (pasta autoritativa).
- Deploy alternativo via Docker (Swarm): previsto, **não em uso**.

| Item | Valor |
|---|---|
| Bot Telegram | `@atualizar_repositorio_bot` |
| Unit systemd | `atualizar-repositorio-bot.service` |
| Repositório do projeto | `https://github.com/JosehRoberto/atualizar-repositorio-comunidades` (`origin`, `main`) |
| Repositório alvo (dados) | `https://gitlab.com/paralivre/comunidades-de-tecnologia-pa` (branch `master`) |
| Clone local do alvo | `repositorio/` (repositório git aninhado, ignorado no git do projeto) |
| Status atual | **MVP funcional — bot operacional** |
| Versão | `v0.2.0` (tag anotada) |
| Python | Python 3.12 |
| Biblioteca | `python-telegram-bot` 22.8 (v20+) |
| Testes | **232** herméticos |

**Escopo do cadastro (schema real do README):**
- Cada comunidade tem **apenas `nome` + `links`** (`| Comunidade | Links |`) — sem cidade,
  descrição ou tecnologias (não há colunas para isso).
- A seção **Observatório Amazônico** usa schema distinto (`| Serviço | Link |`) e **não é editável**
  pelo fluxo de comunidades.
- Marcador `:triangular_flag_on_post:`: existe em **no máximo 1** comunidade (referência inicial:
  **Divas Digitais**); o bot normaliza as demais.

---

## 2. Estrutura do Projeto

```
atualizar-repositorio-comunidades/
├── AGENTS.md                          ← leia SEMPRE antes de alterar qualquer arquivo
├── CHANGELOG.md                       ← histórico de versões
├── README.md                          ← visão geral + instalação + comandos
├── pytest.ini                         ← configuração do pytest
├── requirements-test.txt              ← dependências de teste
├── .gitignore                         ← ignora repositorio/, backup/*.bak, .env, caches
├── backup/                            ← backups (README_YYYYMMDD_HHMMSS.bak) — não versionar .bak
├── docs/                              ← documentação do projeto
│   ├── requisitos.md                  ← fonte canônica do escopo e das decisões
│   ├── nova-sessao.md                 ← handoff anterior (histórico)
│   ├── prompt-inicial.md              ← prompt de kickoff do projeto
│   ├── planejamento-skill-criacao-bot-telegram.md
│   └── metodologia-projeto-bot-telegram.md (ponteiro p/ a skill)
├── bot/                               ← código do bot (Desktop via systemd)
│   ├── .env                           ← segredos (nunca expor ou commitar)
│   ├── .env.example                   ← mantido atualizado, sem valores reais
│   ├── config.py                       ← lê `.env` (`Config`, `validar()`), sem hardcode
│   ├── main.py                         ← logging + `run_polling`
│   ├── requirements.txt
│   ├── atualizar-repositorio-bot.service ← unit systemd (instância única)
│   ├── handlers/
│   │   ├── commands.py                ← `create_application()` + `/start`, `/cancelar`, menu
│   │   ├── state_manager.py           ← máquina de estados (PROTEGIDA): EstadoConversa, Acao,
│   │   │                                 ConversaUsuario, GerenciadorEstado, ORDEM_POR_ACAO
│   │   ├── menu.py                     ← fluxos nova/editar/remover/buscar + preview/aprovação;
│   │   │                                 `/listar`, `/validar`, `/historico`
│   │   └── publicacao.py               ← `/publicar` (commit+push) e `/restaurar` (diff+backup)
│   ├── models/
│   │   └── comunidade.py              ← `Comunidade`, `Link`, `nome_normalizado()`
│   ├── schemas/
│   │   └── comunidade.py              ← `ComunidadeSchema`, `LinkSchema` (pydantic v2)
│   ├── services/                      ← região protegida (AGENTS.md §3.1)
│   │   ├── readme_service.py          ← parser/editor do README (seções/âncoras/tabelas/badges)
│   │   ├── backup_service.py          ← backup/listagem/limpeza/diff/restauração
│   │   ├── historico_service.py       ← histórico JSONL append-only
│   │   ├── tempo.py                    ← fuso `America/Belem` (timestamp)
│   │   ├── git_service.py             ← fetch/pull/commit/branch/push/MR via `GITLAB_TOKEN`
│   │   ├── validacao_service.py       ← validações §2.8 + `🧩 Validar README`
│   │   └── escrita_service.py         ← `asyncio.Lock` + sync + recheck de hash (§2.12)
│   ├── history/                        ← `historico.jsonl` (não versionado)
│   └── tests/                          ← pytest (232 testes herméticos)
│       ├── conftest.py
│       ├── test_config.py, test_models.py, test_schemas.py
│       ├── test_readme_service.py, test_backup_service.py, test_historico_service.py
│       ├── test_validacao_service.py, test_git_service.py, test_escrita_service.py
│       └── test_state_manager.py, test_menu.py, test_publicacao.py
├── repositorio/                        ← clone do repositório alvo (GitLab) — ignorado no git
│   ├── README.md                       ← alvo das edições do bot (fonte da verdade)
│   └── LICENSE                         ← preservar (não editar)
└── prompts/
    └── nova-conversa.md               ← este arquivo
```

---

## 3. Estado Atual do Bot (21/10/2026)

### Arquitetura Desktop implementada

- **Bot principal**: systemd (`atualizar-repositorio-bot.service`) + `.venv/` — roda em
  `/home/roberto/projetos/atualizar-repositorio-comunidades`.
- `ExecStart=.venv/bin/python -m bot.main`, `WorkingDirectory` no projeto,
  `EnvironmentFile=bot/.env`, `Restart=on-failure`, **instância única**.
- Deploy alternativo via Docker (Swarm): previsto, **não em uso**.

### O que está funcionando

- Bot operacional (`create_application()` monta a aplicação; smoke test inicia o polling sem erros).
- `bot/.env` **configurado** (não versionado): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`
  (usuário `87681147`) e `GITLAB_TOKEN` (`comunidades-bot`); `Config.validar()` sem problemas.
- **Serviços de domínio (região protegida) implementados e testados:**
  - Parser/editor do README (`readme_service`): parse de seções/âncoras/tabelas, detecção de
    schema, leitura/escrita de linhas `| **Nome** | badges |`, inserção/edição/remoção em **ordem
    alfabética** (`nome_normalizado`), badges na **ordem canônica** (shields.io) e normalização do
    marcador `:triangular_flag_on_post:` (no máximo 1). **Edição cirúrgica**.
  - Backup (`backup_service`): `README_YYYYMMDD_HHMMSS.bak` (fuso `America/Belem`),
    listagem/limpeza (`manter N`), diff e restauração com backup prévio
    (`README_pre-restauracao_*.bak`).
  - Histórico (`historico_service` + `tempo`): JSONL append-only em
    `bot/history/historico.jsonl` (`timestamp`, `usuario_id`, `acao`, `secao`, `comunidade`,
    `antes`, `depois`, `backup_path`, `commit`).
  - Git/GitLab (`git_service`): `fetch`/`pull --ff-only`, `commit` (define autor), `criar_branch`,
    `push` via URL autenticada montada **em runtime** (token **fora** do remote), `criar_merge_request`
    (API v4, header `PRIVATE-TOKEN`); helpers de hash. Token **mascarado** em erros.
  - Validações (`validacao_service`): campos obrigatórios, URLs válidas, duplicidade de nome/URL,
    seção editável e `🧩 Validar README` (integridade de tabelas, âncoras × seções, duplicidades,
    URLs inválidas e coerência do marcador) + `comparar_estrutura` (edição cirúrgica).
  - Escrita concorrente (`escrita_service`): `asyncio.Lock` global, `sincronizar_seguro`
    (`fetch` + `pull --ff-only`; aborta em conflito) e `conferir_hash` antes de gravar.
- **Fluxo conversacional** (`state_manager` + `menu`): nova/editar/remover/buscar com **preview** e
  **aprovação** (`✅ Aplicar` / `✏️ Editar` / `🔀 Trocar seção` / `❌ Cancelar`).
- **Publicação e restauração** (`publicacao`): `/publicar` (sincroniza, mostra alterações pendentes e,
  **somente após confirmação explícita**, faz `commit` + `push`) e `/restaurar` (lista backups →
  **diff** → confirmação → backup prévio). Ambos registram no histórico.
- **Consulta**: `/listar`, `/validar` e `/historico`.
- **Guard de segurança**: `TELEGRAM_ALLOWED_USER_IDS` em todos os handlers.
- **Segurança**: logging `httpx`/`httpcore` em `WARNING` (token do bot não vaza) e `PTBUserWarning`
  esperado silenciado em `main.py`.
- **Rotação de token GitLab concluída**: token antigo revogado; exposição local removida; novo token
  `comunidades-bot` (`api`, `write_repository`; expira em 20/10/2027) validado e cadastrado.
- **Release `v0.2.0` publicada**: tag anotada `v0.2.0` (`deploy validado: bot completo`) criada e
  enviada ao `origin`; `main` sincronizada com `origin/main`.

### Pendente / Em investigação

- **Instalar/ativar a unit systemd** (requer `sudo`, do usuário): copiar para
  `/etc/systemd/system/`, `daemon-reload` e `enable --now` — ver `README.md §Deploy`.
- **Busca fuzzy (§2.10)**: hoje `buscar`/`editar`/`remover` usam match exato pela chave normalizada
  com fallback por substring (`menu.buscar_nome`); evolução prevista: fuzzy (`rapidfuzz`/`difflib`) +
  lista numerada de candidatos.
- **Criação de novas seções pelo bot (§2.6)**: hoje o fluxo insere em seções existentes; criar seção
  nova (âncora + título + tabela + atualização da "Navegação Rápida") ainda não está implementado.
- **Fluxo de branch/Merge Request**: `git_service` já expõe `criar_branch`/`criar_merge_request`,
  mas `/publicar` faz `commit` + `push` direto — o MR como opção é evolução futura.
- **Adequar dados do README alvo**: a varredura `🧩 Validar README` detectou 2 problemas legítimos no
  clone atual (URL do Discord repetida entre *AWS User Group Castanhal* e *XibéSec*; 9 comunidades
  marcadas com `:triangular_flag_on_post:`) — a normalização para **Divas Digitais** como única
  marcada ocorre na primeira inserção pelo bot.

### Bugs já resolvidos

| Bug | Solução |
|---|---|
| `PTBUserWarning` no log do serviço (mistura de `MessageHandler`/`CallbackQueryHandler`) | Filtro específico em `main.py` (`warnings.filterwarnings` para `per_message=False`); `create_application()` limpo |
| `409 Conflict` no `getUpdates` (duas instâncias) | Garantir **instância única** via systemd; nunca subir bot duplicado |
| Token GitLab exposto em texto no `.git/config` do clone antigo e em `~/.git-credentials` | Token removido desses locais, antigo **revogado**; autenticação por token em runtime (`GITLAB_TOKEN`), sem persistir em remote |
| Disparidade entre `docs/requisitos.md`, `AGENTS.md`, `README.md` e o código | Sincronização documental (handoff, próximos passos, nome da unit) |

---

## 4. Fluxo Atual

```
/start (menu)  ou  /nova
       ↓
NOVA_NOME → NOVA_LINKS (linhas "Tipo URL"; envie "pronto")
       ↓
NOVA_SECAO (número/nome da seção; Observatório não editável)
       ↓
[validação: nome, ≥1 link, URL, duplicidade, seção]
       ↓
PREVIEW → APROVACAO  ✅ Aplicar | ✏️ Editar | 🔀 Trocar seção | ❌ Cancelar
       ↓
(sincroniza git + recheck de hash, sob lock)
       ↓
backup → grava README (cirúrgico) → registra histórico → confirma
       ↓
/disponível separadamente: /publicar (commit + push, com confirmação)

/editar:  EDITAR_NOME → EDITAR_ESCOLHA (nome | links | ambos)
          → EDITAR_NOVO_NOME e/ou EDITAR_LINKS → PREVIEW → APROVACAO
/remover: REMOVER_NOME → REMOVER_CONFIRMACAO (✅ Remover | ❌ Cancelar)
/buscar:  BUSCAR_NOME → resultado (somente leitura)
```

> **Ordem canônica dos estados** (`bot/handlers/state_manager.py`, região protegida):
> ```
> NOVA:     NOVA_NOME → NOVA_LINKS → NOVA_SECAO → PREVIEW → APROVACAO
> EDITAR:   EDITAR_NOME → EDITAR_ESCOLHA → (EDITAR_NOVO_NOME →) [EDITAR_LINKS →] PREVIEW → APROVACAO
> REMOVER:  REMOVER_NOME → REMOVER_CONFIRMACAO
> BUSCAR:   BUSCAR_NOME
> PUBLICAR: PUBLICAR_CONFIRMACAO
> RESTAURAR:RESTAURAR_ESCOLHA → RESTAURAR_CONFIRMACAO
> ```
> A ramificação de `EDITAR_ESCOLHA` usa `campo_editar` (`nome` / `links` / `ambos`).

### Regras de negócio do README

- **Schema das linhas:** `| Comunidade | Links |` (Observatório: `| Serviço | Link |`).
- **Ordem:** alfabética por `nome_normalizado()` (sem caixa e sem acentos).
- **Marcador `:triangular_flag_on_post:`:** no máximo 1 comunidade (a "última adicionada");
  referência inicial: **Divas Digitais**.
- **Badges:** ordem canônica e cores definidas em `docs/requisitos.md` §2.4.
- **Alteração cirúrgica:** nunca reformatar outras partes do README; `comparar_estrutura` garante que
  o diff toca só a linha/bloco alvo.

---

## 5. Regras Técnicas Críticas

### ConversationHandler (python-telegram-bot v20+)

- **`montar_conversation_handler()` registrado PRIMEIRO** em `create_application()`
  (entry_points + fallbacks) — antes dos comandos globais.
- `entry_points`: `/nova`, `/buscar`, `/editar`, `/remover` + entradas de publicação.
- `fallbacks`: apenas `/cancelar` (`cancelar_fluxo`); `allow_reentry=True`.
- `CallbackQueryHandler` **dentro dos estados** (aprovação `^aprov_(ok|editar|secao|cancelar)$`,
  edição `^edit_(nome|links|ambos)$`, remoção `^rem_(ok|nao)$`) — **nunca** um
  `CallbackQueryHandler` global para callbacks do fluxo.
- Nunca registrar handler global que “roube” comandos do `ConversationHandler`.

### Ordem de registro dos handlers (importa)

```python
application.add_handler(montar_conversation_handler())  # sempre PRIMEIRO
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("cancelar", cancelar))
application.add_handler(CommandHandler("listar", cmd_listar))
application.add_handler(CommandHandler("validar", cmd_validar))
application.add_handler(CommandHandler("historico", cmd_historico))
```

### Regiões protegidas (AGENTS.md §3.1)

Alterações exigem **justificativa explícita + teste**; comentar `# ALTERADO [data]: <motivo>`:

| Arquivo / Módulo | Região | Motivo |
|---|---|---|
| `bot/services/` | parser e editor de Markdown do README | preservação de estrutura/formatação |
| `bot/services/` | normalização do marcador `:triangular_flag_on_post:` | no máximo 1 comunidade marcada |
| `bot/services/` | serviço de backup | pré-condição de toda escrita |
| `bot/services/` | serviço de histórico | rastreabilidade das operações |
| `bot/services/` | serviço Git/GitLab | commit/branch/push/MR |
| `bot/handlers/` | `create_application()` | ordem de registro dos handlers |
| `bot/handlers/` | `state_manager.py` e orquestração de aprovação/preview | ordem dos estados e ponto pós-confirmação |
| `bot/config.py` | leitura de `.env` | sem valores hardcoded |

---

## 6. Comandos do Terminal

```bash
# Validação local (antes de reiniciar):
python3 -m py_compile bot/handlers/commands.py && echo "OK"
python3 -c "from bot.handlers.commands import create_application; print('OK')"

# Testes (herméticos, sem .env real nem rede):
pytest bot/tests/ -v
pytest bot/tests/ --cov=bot --cov-report=term-missing

# Backup obrigatório antes de editar o README:
mkdir -p backup
TS=$(date +%Y%m%d_%H%M%S)
cp repositorio/README.md backup/README_${TS}.bak
ls -lh backup/README_${TS}.bak

# Git do projeto:
git status --short
git diff
```

### 6.1 Restart + validação (comandos canônicos, uma linha)

**Sempre via systemd** (atômico). Nunca usar `pkill` por nome. Reinicia e já valida
(estado, instância única e varredura de erros):

```bash
sudo systemctl restart atualizar-repositorio-bot.service && sleep 3 && echo "MainPID: $(sudo systemctl show -p MainPID --value atualizar-repositorio-bot.service)" && echo "Bot: $(systemctl is-active atualizar-repositorio-bot.service)" && pgrep -af "[b]ot\.main" && sudo journalctl -u atualizar-repositorio-bot.service -n 30 --no-pager && (sudo journalctl -u atualizar-repositorio-bot.service --since "2 min ago" --no-pager | grep -iE "\b409\b|\bconflict\b|\btraceback\b|\berror\b" || echo "OK: sem 409/erros desde o restart")
```

> `pgrep -af "[b]ot\.main"` deve retornar **exatamente 1** processo (instância única).
> A varredura usa `--since "2 min ago"` e `\b409\b`/`\berror\b` (fronteira de palavra) para evitar
> falsos positivos.

---

## 7. Regras para o Agente

1. Ler `AGENTS.md` completo antes de qualquer alteração.
2. Fazer backup de cada arquivo/README antes de editar (AGENTS.md §2).
3. Nunca expor tokens ou conteúdo do `bot/.env`; manter `bot/.env.example` atualizado.
4. Nunca embutir o `GITLAB_TOKEN` na URL do remote nem persistir em `.git/config`.
5. Verificar sintaxe (`py_compile`) e imports após edições.
6. Ao criar planejamento estratégico: informar os arquivos que serão alterados/consultados e
   **aguardar aprovação** antes de implementar (AGENTS.md §10).
7. Não alterar funções/regiões protegidas sem justificativa explícita + teste.
8. Em `ConversationHandler`, revisar AGENTS.md §8 (nunca `CallbackQueryHandler` global para
   callbacks do fluxo).
9. Testes **herméticos**: sem `.env` real, sem rede; isolar caminhos com `tmp_path` + `monkeypatch`;
   mockar `requests`, `subprocess` e a API do Telegram.
10. **Não commitar por iniciativa própria** — sugerir a mensagem e aguardar autorização (§12.1).
11. Operações de commit/branch/push/MR no repositório alvo exigem **confirmação explícita no
    Telegram** (feito pelo serviço do bot) — nunca executar sozinho.

---

## 8. Fluxo de Atualização e Deploy (systemd)

### Política de sincronização

A pasta autoritativa é `/home/roberto/projetos/atualizar-repositorio-comunidades`. O serviço roda via
systemd a partir desta pasta com a `.venv` dedicada. Deploy = reiniciar o serviço (o commit **não**
faz deploy).

### Atualizar o bot

```bash
# 1. Editar localmente
nano bot/handlers/menu.py

# 2. Testar sintaxe e imports
python3 -m py_compile bot/handlers/menu.py
python3 -c "from bot.handlers.commands import create_application; print('OK')"

# 3. Rodar os testes
pytest bot/tests/ -v

# 4. Reiniciar o serviço
sudo systemctl restart atualizar-repositorio-bot.service && sleep 3
sudo systemctl status atualizar-repositorio-bot.service
sudo journalctl -u atualizar-repositorio-bot.service -n 30 --no-pager
```

### Instalação da unit (uma vez, requer `sudo`)

```bash
sudo cp bot/atualizar-repositorio-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atualizar-repositorio-bot.service
```

> Mantenha **instância única** (duas instâncias causam `409 Conflict` no `getUpdates`).

### Rollback

- **Arquivo:** `cp backup/README_<TS>.bak repositorio/README.md`.
- **Código:** `git revert <commit>` (preserva o histórico); `git checkout <tag|commit> -- <arquivo>`
  para reverter arquivo isolado. Nunca `reset --hard` em `main` já publicada.

---

## 9. Próximos Passos

1. ⏳ **Instalar/ativar a unit systemd** (passos `sudo` em `README.md §Deploy`) — única pendência para
   o deploy de produção.
2. ✅ **Publicar a release:** tag anotada `v0.2.0` criada e **já publicada** no `origin`.
3. 🔜 **Busca fuzzy (§2.10):** match exato → fuzzy (`rapidfuzz`/`difflib`) + lista numerada de
   candidatos; desempate por URL em nomes homônimos.
4. 🔜 **Criação de novas seções (§2.6):** âncora + título `## <emoji> <Título>` + tabela + atualização
   da "Navegação Rápida", inserida antes de `## 🤝 Como Contribuir`.
5. 🔜 **Fluxo de branch/Merge Request:** usar `git_service.criar_branch`/`criar_merge_request` como
   alternativa ao `push` direto em `/publicar`.
6. 🔜 **Normalização inicial do clone:** ao inserir a primeira comunidade, normalizar o marcador
   `:triangular_flag_on_post:` (hoje 9 marcadas; deve sobrar só **Divas Digitais**).
7. 🔜 **Backlog:** revisar os 2 problemas legítimos apontados por `🧩 Validar README` (URL do Discord
   repetida; marcador múltiplo).

---

## Soluções Encontradas Durante a Operação

### 1. `409 Conflict` no `getUpdates`

**Sintoma:** `409 Conflict: terminated by other getUpdates request`.

**Causa:** bot rodando em duas instâncias (ex.: Desktop e Docker/VPS) simultaneamente.

**Solução:** manter **instância única** — um só serviço systemd ativo; não subir o bot localmente
enquanto o serviço roda.

### 2. Exposição do token GitLab

**Sintoma:** token em texto no `.git/config` do clone antigo e em `~/.git-credentials`.

**Causa:** autenticação embutida na URL do remote / credential helper.

**Solução:** token removido desses locais e **rotacionado**; autenticação feita **em runtime** com
`GITLAB_TOKEN` (nunca persistido no remote nem em `.git/config`).

### 3. `PTBUserWarning` no log do serviço

**Sintoma:** aviso do `python-telegram-bot` sobre `CallbackQueryHandler` com `per_message=False`.

**Causa:** mistura esperada de `MessageHandler` e `CallbackQueryHandler` no `ConversationHandler`.

**Solução:** filtro específico em `main.py` (`warnings.filterwarnings`), mantendo o log limpo;
`create_application()` inalterado.

---

## Changelog

> **Histórico canônico:** o registro completo de versões está em **[`CHANGELOG.md`](../CHANGELOG.md)**.
> Este documento mantém apenas o **estado atual** do bot; para o histórico completo, consulte o
> `CHANGELOG.md`.

> **Regra:** a lista abaixo mantém **apenas as atualizações mais recentes** — histórico completo no
> `CHANGELOG.md`.

**Últimas mudanças (resumo):**
- **21/10/2026** — **`v0.2.0`** (CHANGELOG preparado para a release): `bot/main.py` silencia o
  `PTBUserWarning` esperado; unit systemd (`bot/atualizar-repositorio-bot.service`) e `.venv`
  validados; **232 testes**.
- **21/10/2026** — **`escrita_service`** (região protegida): `asyncio.Lock` global, `sincronizar_seguro`
  (`fetch` + `pull --ff-only`) e `conferir_hash` antes de gravar (§2.12); **+12 testes** (suíte em 232).
- **21/10/2026** — **`publicacao`** (região protegida): `/publicar` (commit + push com confirmação) e
  `/restaurar` (lista → diff → confirmação → backup prévio), além de `/validar` e `/historico`;
  **+25 testes** (suíte na época em 220).

---
*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
