# Planejamento — Skill de criação de bots Telegram

> **Status:** planejamento (nada da skill foi criado ainda).
> Origem: proposta de transformar `docs/metodologia-projeto-bot-telegram.md` em uma **skill**
> reutilizável, criada com a skill `skill-creator`.
> Idioma: **português do Brasil (pt-BR)**.

---

## 1. Objetivo da skill

Permitir que, em **qualquer projeto/computador deste ambiente**, o agente:
1. conduza o *kickoff* de um novo bot Telegram segundo uma metodologia padronizada;
2. gere os artefatos iniciais (`AGENTS.md`, `CHANGELOG.md`, `.gitignore`, estrutura de pastas,
   templates de `docs/requisitos.md` e prompt inicial);
3. reutilize a arquitetura de referência do `/home/roberto/projetos/agendatipara-bot`;
4. aplique as políticas do projeto (backup, testes herméticos, preview/aprovação, versionamento).

---

## 2. Decisões confirmadas

| Item | Decisão | Observação |
|---|---|---|
| **Nome da skill** | `criacao-bot-telegram` | Confirmado pelo mantenedor. |
| **Local** | `/home/roberto/.config/opencode/skills/criacao-bot-telegram/` | Global — usável em todos os projetos. |
| **Escopo** | Metodologia de *kickoff* + geração dos arquivos iniciais | Não substitui `skill-creator` nem frameworks. |
| **Idioma** | pt-BR (conteúdo e descrição) | Consistente com as demais skills. |
| **Fonte de conteúdo** | `docs/metodologia-projeto-bot-telegram.md` | Vira material de origem; depois ponteiro (§10). |
| **`scripts/bootstrap.py`** | **Incluir** (mínimo, idempotente, com `--dry-run`) | Justificado em §5. |
| **Destino do doc de metodologia** | **Ponteiro** após a skill validada (paralelo durante o dev) | Justificado em §10. |

---

## 3. Local de criação

| Local | Caminho | Prós | Contras | Decisão |
|---|---|---|---|---|
| **Global (OpenCode)** | `/home/roberto/.config/opencode/skills/criacao-bot-telegram/` | disponível em todos os projetos; padrão das outras skills | mistura com skills de terceiros | **✅ Escolhido** |
| Global (Agent Skills) | `/home/roberto/.agents/skills/<nome>/` | também é escaneado | uso atual é para skills de terceiros | — |
| Local do projeto | `atualizar-repositorio-comunidades/.opencode/skills/<nome>/` | versiona junto do repo | reutilizável só neste projeto | não recomendado |

> **Workspace de avaliação (skill-creator):** manter **fora** do diretório de skills para não ser
> escaneado — sugerido `/home/roberto/projetos/criacao-bot-telegram-workspace/`.

---

## 4. Anatomia da skill

```
criacao-bot-telegram/
├── SKILL.md                      ← fluxo + "quando usar" + índice (< 500 linhas)
├── references/
│   ├── fase-requisitos.md        ← como conduzir requisitos/decisões
│   ├── arquitetura-bot.md        ← estrutura bot/ e padrões (base: agendatipara-bot)
│   ├── politicas.md              ← backup, testes herméticos, git, preview/aprovação
│   └── deploy-systemd.md         ← unit, venv, restart, instância única
├── assets/
│   └── templates/
│       ├── AGENTS.template.md
│       ├── CHANGELOG.template.md
│       ├── requisitos.template.md
│       ├── prompt-inicial.template.md
│       ├── gitignore.template
│       ├── requirements.template.txt
│       ├── pytest.template.ini
│       └── env.example.template
└── scripts/
    └── bootstrap.py              ← scaffold automático (pastas + templates)
```

- **Por que `assets/templates/`:** os templates são o coração da reutilização; mantê-los como
  arquivos prontos evita o agente reescrevê-los a cada uso.
- **`scripts/bootstrap.py`:** ver §5.

---

## 5. `scripts/bootstrap.py` — decisão e justificativa

**Decisão: incluir**, com escopo controlado.

**A favor**
- O scaffolding é **determinístico e repetitivo** (criar `bot/{handlers,models,schemas,services,tests}`,
  `backup/`, `docs/`, `.gitkeep`, `.gitignore`, `pytest.ini`, `requirements.txt`, `.env.example`,
  copiar templates). É o caso típico que o `skill-creator` recomenda empacotar: evita o agente
  reescrever a mesma sequência e economiza tokens.
- **Reprodutibilidade:** todos os projetos nascem com a mesma estrutura.

**Cuidados (por isso o escopo é mínimo)**
- O *conteúdo* dos templates (regras de negócio, regiões protegidas) **sempre** muda por projeto —
  o script **não** deve gerá-lo, só o esqueleto.
- Muitas flags tornam o script frágil e conflitam com o princípio de "explicar o porquê, ser flexível".

**Requisitos do script**
- **Idempotente:** rodar duas vezes não corrompe nem duplica.
- **`--dry-run`:** mostra o que faria, sem escrever.
- **Parametrizado apenas com variáveis conhecidas:** `<nome-projeto>`, `<data>`, `<dir-dados>`,
  `<remote>`.
- **Somente estrutura + cópia de templates** de `assets/templates/` com substituição de placeholders;
  **não** gera lógica de bot.
- Aferir utilidade real nos evals (§8): se o modelo não o usar, reavaliar.

---

## 6. Esqueleto do `SKILL.md`

```markdown
---
name: criacao-bot-telegram
description: <ver §7>
---

# Criação de Bot Telegram
## Quando usar / quando não usar
## Visão geral do fluxo (fases 0–7)
## Passo 1 — Capturar o objetivo (prompt inicial)
## Passo 2 — Consolidar requisitos e decisões
## Passo 3 — Estrutura de pastas + repositório (.gitignore, git init)
## Passo 4 — Gerar AGENTS.md (a partir de assets/templates/)
## Passo 5 — Gerar CHANGELOG.md (seguir changelog-convention)
## Passo 6 — Esqueleto de código bot/ (ordem de implementação)
## Passo 7 — Testes, documentação e deploy (systemd)
## Uso do scripts/bootstrap.py (opcional/recomendado)
## Checklist de kickoff
## Erros comuns / anti-padrões
## Referências (references/, projeto agendatipara-bot)
```

- Consultar a skill `changelog-convention` em vez de duplicar a convenção.
- Citar o `agendatipara-bot` apenas como **fonte de arquitetura**, com "somente leitura".

---

## 7. `description` (mecanismo de trigger)

Proposta inicial (a otimizar depois com o `run_loop.py` do skill-creator):

> Metodologia para criar e iniciar um novo projeto de **bot Telegram** do zero — objetivo,
> requisitos, estrutura de pastas, `AGENTS.md`, `CHANGELOG.md`, `.gitignore`, esqueleto de código e
> deploy. Use **sempre** que o usuário mencionar "criar um bot no Telegram", "novo bot",
> "bootstrap de bot", "começar um projeto de bot", "estrutura inicial de bot", mesmo que não use a
> palavra "metodologia".

Deve conter as duas dimensões: **o que faz** + **quando usar** (incluindo gatilhos em pt-BR).

---

## 8. Casos de teste (evals)

Salvos em `evals/evals.json` (sem asserções na 1ª rodada):

1. *"Quero criar um novo bot no Telegram que lê uma planilha e envia lembretes; me ajude a montar a
   estrutura inicial do projeto."*
2. *"Vou começar um bot do zero — preciso do AGENTS.md, CHANGELOG.md e da estrutura de pastas."*
3. *"Monte o kickoff de um bot Telegram que cadastra pedidos num JSON, com backup e preview."*

Avaliação: qualitativa (aderência ao fluxo e aos artefatos) + asserções objetivas
(presença de `AGENTS.md`, `CHANGELOG.md`, `.gitignore`, estrutura `bot/`).

---

## 9. Processo (skill-creator)

```
1. Draft do SKILL.md + templates + scripts/bootstrap.py
2. Criar evals/evals.json (2–3 prompts)
3. Rodar with-skill × baseline (subagentes, em paralelo)
4. Avaliar: viewer (generate_review.py) + asserções/benchmark
5. Iterar conforme feedback até estabilizar
6. Otimizar a description (run_loop.py)
7. Empacotar (package_skill.py) se o tool de apresentação existir
```

---

## 10. Destino de `docs/metodologia-projeto-bot-telegram.md`

**Decisão: manter como ponteiro** (com paralelo temporário durante o desenvolvimento).

**Análise**
- **Paralelo (dois completos):** cria **duas fontes de verdade** que divergem com o tempo —
  anti-padrão de duplicação.
- **Remover:** perde a referência local e quebra o histórico/CHANGELOG; prematuro antes de a skill
  existir e ser validada.
- **Ponteiro:** uma só fonte (a skill), com o doc reduzido a resumo curto + caminho da skill —
  evita drift e mantém a descoberta no repo.

**Sequência recomendada**
1. **Durante o desenvolvimento:** manter o doc **paralelo** (é o material de origem).
2. **Após a skill validada:** encolher o doc para **ponteiro** (título + 1 parágrafo + caminho da
   skill + como ela é acionada), registrando a mudança no `CHANGELOG.md`.

---

## 11. Riscos e cuidados

- **Risco de "engessar":** explicar o *porquê*, não só passos; evitar MUSTs rígidos.
- **Duplicação com `changelog-convention`:** referenciar a skill existente, não copiar.
- **Acoplamento ao `agendatipara-bot`:** tratar apenas como referência de arquitetura (somente leitura).
- **Script frágil:** manter `bootstrap.py` mínimo, idempotente e com `--dry-run`.
- **Workspace de avaliação:** manter fora de `~/.config/opencode/skills/`.
- **Portabilidade:** o path do `agendatipara-bot` é específico desta máquina — usar como exemplo.

---

## 12. Decisões pendentes

Nenhuma. As quatro decisões foram definidas (§2).

---

## Arquivos que serão alterados ou consultados

Para executar este planejamento, os seguintes arquivos serão modificados ou lidos:

- `docs/metodologia-projeto-bot-telegram.md` (origem do conteúdo) — **consultado**
- `docs/planejamento-skill-criacao-bot-telegram.md` (este plano) — **criado/atualizado**
- `AGENTS.md` — **consultado**; `CHANGELOG.md` — **atualizado**
- `/home/roberto/.config/opencode/skills/skill-creator/SKILL.md` — **consultado**
- `/home/roberto/.config/opencode/skills/changelog-convention/SKILL.md` — **consultado**
- `/home/roberto/projetos/agendatipara-bot/AGENTS.md` — **consultado** (referência)
- A criar (somente após aprovação): `/home/roberto/.config/opencode/skills/criacao-bot-telegram/**`
