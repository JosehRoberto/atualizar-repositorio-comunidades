# AGENTS.md — Guia de Operação para Agentes de IA

## Projeto: Atualização do Repositório de Comunidades

> **Este arquivo deve ser lido antes de qualquer alteração no projeto.**
> Escopo e decisões detalhadas: `docs/requisitos.md` (fonte canônica do escopo).
> Idioma do projeto: **português do Brasil (pt-BR)**.

---

## 0. Contexto e repositórios

- **Repositório do projeto (código do bot e docs):**
  `https://github.com/JosehRoberto/atualizar-repositorio-comunidades` (`origin`).
- **Repositório alvo (dados):**
  `https://gitlab.com/paralivre/comunidades-de-tecnologia-pa` — clonado em `repositorio/`.
- **Projeto de referência (arquitetura/padrões):**
  `/home/roberto/projetos/agendatipara-bot` — **somente leitura**, nunca editar.
- **Finalidade:** bot Telegram que cadastra/edita/remove comunidades no `README.md` do repositório
  alvo, com backup, preview, aprovação e publicação controlada.

---

## 1. Estrutura do projeto

```
atualizar-repositorio-comunidades/
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── .gitignore
├── bot/                     ← código do bot (handlers/models/schemas/services/tests)
├── backup/                  ← backups (README_YYYYMMDD_HHMMSS.bak) — não versionar .bak
├── docs/                    ← documentação do projeto (requisitos, prompts, planejamentos)
└── repositorio/             ← clone do repositório alvo (GitLab) — ignorado no git do projeto
    ├── README.md            ← alvo das edições do bot
    └── LICENSE              ← preservar (não editar)
```

- O código fica em `bot/`, seguindo a organização do projeto de referência.
- `repositorio/` é um **repositório git aninhado** e está no `.gitignore` do projeto.

---

## 2. Política de backup — OBRIGATÓRIA

### 2.1 Regra geral

**Todo README alterado DEVE ser copiado para `backup/` antes da alteração.**
Sem backup confirmado, nenhuma edição deve prosseguir.

### 2.2 Nomenclatura

```
backup/README_YYYYMMDD_HHMMSS.bak
```

- Fuso horário: `America/Belem`.
- Vários arquivos alterados numa mesma operação usam o **mesmo timestamp**.

### 2.3 Procedimento

```bash
mkdir -p backup
TS=$(date +%Y%m%d_%H%M%S)
cp repositorio/README.md backup/README_${TS}.bak
ls -lh backup/README_${TS}.bak   # confirmar antes de editar
```

### 2.4 Rollback

```bash
cp backup/README_<TS>.bak repositorio/README.md
```

### 2.5 Manutenção

- Manter os backups das últimas **5 sessões** de alteração.
- **Não** commitar `backup/` nem `*.bak` (já no `.gitignore`).

---

## 3. Diretório `repositorio/` e arquivos protegidos

- `repositorio/` é a **fonte da verdade** do README. A pasta antiga
  `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa` está **descontinuada**.
- Contém mais que o README (`LICENSE`). O bot edita **apenas** o `README.md` e **preserva** os
  demais arquivos.
- Não commitar `repositorio/` no repositório do projeto (já ignorado).

### 3.1 Regiões protegidas

Funções/módulos críticos — alterações exigem justificativa explícita e teste antes de concluir:

| Arquivo / Módulo | Região | Motivo da proteção |
|---|---|---|
| `bot/services/` | parser e editor de Markdown do README | preservação de estrutura/formatação |
| `bot/services/` | normalização do marcador `:triangular_flag_on_post:` | no máximo 1 comunidade marcada |
| `bot/services/` | serviço de backup | pré-condição de toda escrita |
| `bot/services/` | serviço de histórico | rastreabilidade das operações |
| `bot/services/` | serviço Git/GitLab | commit/branch/push/MR |
| `bot/handlers/` | `create_application()` | ordem de registro dos handlers |
| `bot/handlers/` | orquestração de aprovação/preview | único ponto pós-confirmação |
| `bot/config.py` | leitura de `.env` | sem valores hardcoded |

**Regra:** ao modificar região protegida, adicionar comentário `# ALTERADO [data]: <motivo>`.

---

## 4. Regras de negócio do README

- Schema das linhas: `| Comunidade | Links |` (a seção "Observatório" usa `| Serviço | Link |`).
- Linhas em **ordem alfabética** (nome normalizado: sem caixa e sem acentos).
- Marcador `:triangular_flag_on_post:`: existe em **no máximo 1** comunidade (a última adicionada).
  Referência inicial do projeto: **Divas Digitais** é a única marcada; o bot normaliza as demais.
- Badges: ordem canônica e cores definidas em `docs/requisitos.md` (§2.4).
- Alteração **cirúrgica**: nunca reformatar outras partes do README.

---

## 5. Autenticação, segredos e `.env`

| Arquivo | Regra |
|---|---|
| `bot/.env` | **Nunca** exibir, logar ou commitar |
| `bot/.env.example` | Manter atualizado, sem valores reais |
| `bot/config.py` | Lê `.env`; sem valores hardcoded |

- Autenticação GitLab via `GITLAB_TOKEN` — **nunca** embutir token em URL de remote nem persistir
  em `.git/config`.
- Configurar o logger `httpx`/`httpcore` em `WARNING` para o token do Telegram não vazar em logs.
- Variáveis previstas em `docs/requisitos.md` (§5).

---

## 6. Convenções de código

- Reaproveitar arquitetura e padrões do `agendatipara-bot`: `python-telegram-bot>=20`,
  `pydantic>=2`, `python-dotenv`, `requests`, `pytest`.
- Organização: `bot/handlers`, `bot/models`, `bot/schemas`, `bot/services`, `bot/tests`,
  `bot/config.py`, `bot/main.py`.
- Comentários e documentação em pt-BR. Não adicionar comentários supérfluos no código.

---

## 7. Testes e isolamento (OBRIGATÓRIO)

```bash
# a partir da raiz do projeto
pytest bot/tests/ -v
pytest bot/tests/ --cov=bot --cov-report=term-missing
```

- Testes **herméticos**: sem `.env` real, sem rede, sem escrita em arquivos de produção.
- Isolar caminhos (README, `backup/`, histórico) com `tmp_path` + `monkeypatch`.
- Mockar serviços externos: chamadas ao GitLab (`requests`), comandos `git` (`subprocess`) e a
  API do Telegram. **Nunca** usar token/credencial real.
- Nunca chamar `requests.*` ou `subprocess.run(["git", ...])` sem mock em testes.

---

## 8. Handlers e `ConversationHandler`

- **Nunca** registrar `CallbackQueryHandler` global para callbacks tratados dentro do
  `ConversationHandler` (o handler global intercepta e quebra o fluxo).
- A ordem dos estados é definida no `state_manager`; alterá-la exige atualizar também o dicionário
  de perguntas e o preview.
- `post_init` é atribuído uma única vez em `create_application()`; não reatribuir em `main.py`.

---

## 9. Validação após alterações

```bash
python3 -m py_compile bot/<arquivo>.py
python3 -c "from bot.handlers.commands import create_application; print('OK')"
pytest bot/tests/ -v
git status --short   # confirmar que nenhum arquivo de produção foi tocado indevidamente
```

---

## 10. Regras para planejamento estratégico

Todo planejamento deve terminar com:

```
## Arquivos que serão alterados ou consultados

- <lista completa>
```

E apresentar, para **aprovação explícita antes de implementar**:
1. Arquivos que serão criados/modificados;
2. Dependências a respeitar;
3. Edge cases a tratar.

---

## 11. Checklist de alteração

**Antes de editar:**
```
[ ] 1. Li o AGENTS.md completo nesta sessão
[ ] 2. Identifiquei todos os arquivos que serão alterados
[ ] 3. Criei backup com timestamp em backup/ (quando aplicável)
[ ] 4. A alteração toca região protegida (§3.1)? → justificativa + testes
[ ] 5. A alteração envolve segredos/`.env`? → revisar §5
[ ] 6. A alteração mexe no ConversationHandler? → revisar §8
[ ] 7. Existe plano de rollback?
[ ] 8. Testes herméticos e isolados (§7)?
```

**Após concluir:**
```
[ ] 1. Sintaxe validada (python3 -m py_compile)
[ ] 2. Imports/serviços verificados quando aplicável
[ ] 3. Testes executados
[ ] 4. Documentação atualizada (docs/requisitos.md, README.md, CHANGELOG.md)
[ ] 5. Mensagem de commit sugerida (§12.4) — sem commitar por iniciativa própria
```

---

## 12. Política de Git

O git é o **histórico oficial** do projeto. `origin` = GitHub (branch `main`). Desenvolver direto
em `main`.

### 12.1 Commit só sob solicitação
O agente **não commita por iniciativa própria**: sugere a mensagem e **aguarda autorização**.

### 12.2 Antes de commitar
Revisar `git status` e `git diff`; fazer staging seletivo; conferir que não há segredos.

### 12.3 O que NUNCA commitar
`bot/.env`, `*.env` (exceto `.example`), `repositorio/`, `backup/`, `*.bak`, `.venv/`,
`__pycache__/`.

### 12.4 Mensagem de commit
```
[tipo]: [o que mudou em uma linha]

[Por que a mudança foi necessária — contexto que o diff não mostra]
[Qual problema ela resolve]

Máximo 5 linhas no corpo.
```
Tipos: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`.

### 12.5 Granularidade
**Um commit por tema.** `docs:` pode ser commit separado do código.

### 12.6 Tags de versão
Criar **tag anotada** para cada estado validado, alinhada ao `CHANGELOG.md`:
```bash
git tag -a vX.Y -m "deploy validado: <resumo>"
git push origin vX.Y
```

### 12.7 Rollback com git
- Preferir `git revert <commit>` (preserva o histórico).
- `git checkout <tag|commit> -- <arquivo>` para reverter arquivo isolado.
- `git reset`/`reflog` só com cautela e **nunca** em `main` já publicada.
- O `backup/` (§2) continua sendo a rede para estado **não commitado**.

### 12.8 Operações no repositório alvo
Commit/branch/push/MR no GitLab são feitos pelo **serviço do bot** e exigem **confirmação explícita
do usuário no Telegram**. Nunca executar sozinho.

---

## 13. Deploy (systemd)

- Produção: Desktop (`roberto-minipc`) via systemd, a partir de
  `/home/roberto/projetos/atualizar-repositorio-comunidades`, com venv dedicada.
- Unit previsto: `bot/atualizar-repositorio-bot.service` (`ExecStart=.venv/bin/python -m bot.main`).
- Aplicar alteração = reiniciar o serviço (o commit **não** faz deploy):
```bash
sudo systemctl restart atualizar-repositorio-bot.service && sleep 3
sudo systemctl status atualizar-repositorio-bot.service
sudo journalctl -u atualizar-repositorio-bot.service -n 30 --no-pager
```
- Manter **instância única** (duas instâncias causam `409 Conflict` no `getUpdates`).

---

## 14. Protocolos de operação por tipo de tarefa

### 14.1 Diagnóstico de bugs — não corrigir sem confirmação
Explicar o que o código faz hoje, o que deveria fazer e onde está a divergência. **Só após o
usuário confirmar o diagnóstico** o agente propõe a correção.

### 14.2 Refatoração — critério único, comportamento preservado
Receber **um** critério (`legibilidade`, `performance` ou `estabilidade`); **não** alterar o
comportamento; comentar cada mudança explicando como atende ao critério.

### 14.3 Mudanças de risco
- **Baixo** (texto de mensagem, log): aplicar após validação.
- **Médio** (handlers, fluxo): validar localmente antes.
- **Alto** (`ConversationHandler`, parser/editor do README, modelo de dados, dependências):
  testar o fluxo completo `/start → … → Aprovar` antes de concluir.

---

## 15. CHANGELOG e versionamento

- Manter `CHANGELOG.md` conforme a skill `changelog-convention`:
  - `## [Unreleased]` no topo com marcos `### vX.Y[.Z] (DD/MM/AAAA) — Título`;
  - `## [x.y.z] - AAAA-MM-DD` apenas para releases publicados;
  - ordem **cronológica decrescente**; sem duplicatas;
  - `## Legenda` no fim.
- Ao sofrer reset de numeração, separar as eras com **nota + divisor**
  (`## Histórico legado (pré-<marco> — até AAAA-MM-DD)`).
- **Versão inicial do projeto:** `v0.1.0`.
- Cada versão validada recebe **tag anotada** `vX.Y[.Z]` (§12.6), com mensagem
  `deploy validado: <resumo>` — mesmo racional do `agendatipara-bot` (`v3.85`, `v2.14`, …).

---

## 16. Encerramento de sessão

Ao final de cada sessão, produzir um resumo estruturado (pt-BR):

```
## Resumo da Sessão

### O que foi feito
- [entregas]

### Documentação atualizada
- [ ] docs/requisitos.md — [alterado / sem alterações necessárias]
- [ ] README.md — [...]
- [ ] CHANGELOG.md — [...]

### O que ficou pendente ou incompleto
- [itens, com motivo]

### Decisões tomadas
- [decisões de escopo/arquitetura]

### Ponto de entrada sugerido para a próxima sessão
- [por onde retomar]
```

- Manter o handoff canônico **`prompts/nova-conversa.md`** atualizado (estado atual, fluxo,
  próximos passos); `docs/nova-sessao.md` fica como histórico da fase de construção.
- Sugerir a mensagem de commit (§12.4) **após** atualizar a documentação, sem commitar sozinho.

---

## 17. Regras de execução segura para codificação

- Trabalhar em **etapas pequenas e verificáveis**; confirmar o conteúdo real do arquivo no disco.
- Nunca deixar código parcial, imports órfãos, funções vazias ou blocos abertos.
- **Após interrupção/truncamento:** inspecionar o estado real antes de continuar; corrigir de forma
  idempotente; não repetir cegamente a última ação nem duplicar blocos.
- Antes de concluir: validar sintaxe (`python3 -m py_compile`), imports e testes disponíveis.

---

## 18. O próprio AGENTS.md é versionado

Alterações neste arquivo seguem as mesmas regras do projeto (backup quando aplicável + commit sob
autorização). Este arquivo não mantém changelog próprio — o histórico fica no `CHANGELOG.md` e no git.
