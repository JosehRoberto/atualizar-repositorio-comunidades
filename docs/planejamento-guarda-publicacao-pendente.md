# Planejamento Estratégico: bloqueio de nova edição com alterações não publicadas

**Data:** 21/10/2026
**Versão:** 1.1
**Foco:** `bot/handlers/menu.py`, `bot/handlers/publicacao.py`, `bot/services/git_service.py`,
`bot/services/escrita_service.py`
**Status:** **implementado, validado e em produção** (290 testes; deploy efetivado; incluído na tag
`v0.6.0`, que também abrange a `v0.5.0`).
**Revisão de risco incorporada** (R1–R11; `prompts/prompt-revisao-risco-planejamento.md`).
**Origem:** análise do diagnóstico "bloqueio encadeado (deadlock) por árvore suja" (Opção B).

---

## 1. Resumo Executivo

- **Objetivo:** impedir que o clone acumule alterações **não publicadas** (árvore suja), bloqueando
  o **início de novas edições** enquanto houver pendências, e **tornar o `/publicar` capaz de
  publicar mesmo quando o remoto mudou** o `README.md`.
- **Problema que resolve:** hoje a gravação (Fase 1) não commita; se o remoto alterar o mesmo
  `README.md` antes da próxima operação, o `git pull --ff-only` falha na gravação **e** no
  `/publicar` (que sincroniza **antes** de commitar) — deadlock sem saída pelo bot.
- **Solução (Opção B):**
  1. **Guarda de edição:** bloquear `/nova`, `/editar` e `/remover` quando a árvore **não estiver
     limpa**, com mensagem "há alterações não publicadas; use `/publicar` ou `/restaurar`".
  2. **`/publicar` robusto:** **commitar antes de sincronizar** e sincronizar com **`pull --rebase`**
     (commita a edição pendente → integra o remoto → `push`).
- **Escopo incluído:** guarda nos fluxos de escrita; reordenação do `/publicar`; método de
  sincronização com rebase; **`/restaurar` sob lock/`ocupado()`**; **detecção de pendência restrita ao
  README**; ajustes de mensagens; testes; documentação.
- **Escopo NÃO incluído:**
  - Mudar o modelo "edição ≠ publicação" (o commit continua ocorrendo **só no `/publicar`**).
  - Commit automático por edição (isso era a Opção A, descartada).
  - `git reset --hard`/force-push (§12.7); branch/MR; parser/editor; backup/histórico;
    `create_application`/`state_manager`/`config.py`; criação de novas seções (§2.6).
- **Conclusão principal:** mudança de **risco médio** (bem contida) que remove o deadlock. A guarda
  ataca a causa (árvore suja acumulada) e a reordenação do `/publicar` garante a via de saída — sem
  alterar o modelo de publicação explícita.

---

## 2. Viabilidade Técnica

### O que já existe (funcionando)

- `GitService.status_limpo()` (`git_service.py:123-125`) — **existe e não é usado hoje**; é a base da guarda.
- `GitService.sincronizar()` = `fetch` + `pull --ff-only` (`git_service.py:132-143`).
- `GitService.commit()` (só o README; `git_service.py:149-164`) e `push()` (`git_service.py:166-175`).
- `escrita_service.lock_escrita()` (`asyncio.Lock`) e `sincronizar_seguro` (`escrita_service.py:42-51`).
- Fluxos isolados: `cmd_nova`/`cmd_editar`/`cmd_remover` (`menu.py:311/373/527`), `aprovacao`
  (`menu.py:687`), `remover_confirmacao` (`menu.py:600`), `/publicar` e `/restaurar` (`publicacao.py`).

### O que muda (por módulo)

| Módulo | Mudança |
|---|---|
| `bot/handlers/menu.py` | guarda em `cmd_nova`/`cmd_editar`/`cmd_remover`; reforço antes de gravar em `aprovacao`/`remover_confirmacao` |
| `bot/handlers/publicacao.py` | `publicar_confirmacao`: commit **antes** de sincronizar; sincroniza com rebase. `restaurar_confirmacao`: sob `lock_escrita()` + `ocupado()` |
| `bot/services/git_service.py` | +`commits_pendentes()` (opcional, p/ mensagem); +`pull_rebase()`/`sincronizar_publicacao()` |
| `bot/services/escrita_service.py` | +`sincronizar_publicacao_seguro()` (fetch + rebase) + mensagens |
| `docs/requisitos.md` | §2.12 — regra de bloqueio + `pull --rebase` na publicação |
| `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md` | registro (§15/§16) |

### Onde o dado é usado

- `status_limpo()` (via `GitService.from_config()`) passa a orientar se uma nova edição pode começar.
- Plug está em regiões protegidas (`git_service`/handlers) → justificativa + teste.

---

## 3. Fluxo Detalhado

### Antes (hoje)

```
/nova → ... → /aprovar → sincronizar(fetch+pull --ff-only) → grava README (árvore SUJA)
/publicar → sincronizar(fetch+pull --ff-only) → commit → push
```

Falha: árvore suja + remoto alterando o README ⇒ `pull --ff-only` falha **na gravação e no `/publicar`**.

### Depois (Opção B)

```
/nova|/editar|/remover  → [GUARDA] status_limpo()?
        ├── não → "⚠️ Há alterações não publicadas. Use /publicar ou /restaurar." (encerra)
        └── sim → segue o fluxo normal

/aprovar[/remover] → lock → [GUARDA] status_limpo()? (reforço)
        ├── não → aborta com a mesma mensagem
        └── sim → sincronizar(fetch+pull --ff-only) → conferir_hash → backup → grava README

/publicar → lock → [se status sujo] commit(README) → fetch + pull --rebase → push
/restaurar → lock → grava backup → árvore pode ficar suja → exige /publicar depois (R11)
```

- **Guarda (2 níveis):** no **início** do fluxo (UX — evita esforço perdido) e **antes de gravar**
  (correção — cobre corrida em que outra operação deixou a árvore suja durante o fluxo).
- **`/publicar`:** commita a edição pendente **primeiro** e depois integra o remoto com rebase — o
  que garante publicação mesmo com o remoto à frente.
- `/publicar` e `/restaurar` **nunca** são bloqueados pela guarda (são a via de saída).

### Estados envolvidos

- **Nenhum estado novo.** Só o corpo dos handlers muda; `state_manager.py` **intocado** (§8).

### Pontos de alteração (arquivo:linha)

- `bot/handlers/menu.py:311-371` (`cmd_nova`), `:373-...` (`cmd_editar`), `:527-...` (`cmd_remover`) —
  guarda de entrada.
- `bot/handlers/menu.py:720-723` (`aprovacao`) e `:613-616` (`remover_confirmacao`) — reforço da guarda
  antes da gravação.
- `bot/handlers/publicacao.py:176-181` (`publicar_confirmacao`) — commit antes do sync; sync com rebase.
- `bot/handlers/publicacao.py:237-266` (`restaurar_confirmacao`) — sob `lock_escrita()` + `ocupado()` (R11).
- `bot/services/git_service.py` — `pull_rebase()`/`sincronizar_publicacao()`, `commits_pendentes()`,
  **`readme_pendente()`** (status restrito ao README — R10).

### Estrutura proposta (esboço)

```python
# menu.py — guarda reutilizável
async def _bloqueado_por_publicacao_pendente(update, uid) -> bool:
    if escrita_service.ocupado():
        await _responder(update, escrita_service.MENSAGEM_OCUPADO)
        return True
    try:
        if not GitService.from_config().status_limpo():
            await _responder(update, MENSAGEM_PUBLICACAO_PENDENTE)
            return True
    except GitError as erro:
        await _responder(update, f"⚠️ Não foi possível inspecionar o repositório: {erro}")
        return True
    return False
```

```python
# publicacao.py — publicar_confirmacao
async with escrita_service.lock_escrita():
    servico = GitService.from_config()
    try:
        if not servico.status_limpo():
            servico.commit(Config.README_PATH, MENSAGEM_COMMIT)   # commita ANTES do sync
        servico.sincronizar_publicacao()                           # fetch + pull --rebase
        servico.push()
    except GitError as erro:
        ...
```

---

## 4. Próximos Passos

- **Não necessárias:** estados/handlers novos; alterar backup/histórico/parser; commit por edição.
- **Obrigatórias (após aprovação):**
  1. `git_service`: `pull_rebase()`/`sincronizar_publicacao()` (+ opcional `commits_pendentes()`).
  2. `escrita_service`: helper de sync de publicação + `MENSAGEM_PUBLICACAO_PENDENTE`.
  3. `menu.py`: guarda nos 3 `cmd_*` e reforço em `aprovacao`/`remover_confirmacao`.
  4. `publicacao.py`: commit antes do sync; rebase; mensagens.
  5. Testes herméticos (git mockado) para R1–R4.
  6. `docs/requisitos.md §2.12`, `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
  7. Validação, deploy (`systemctl restart`) e commit/tag sob autorização (§12).

---

## 5. Referências

- **Arquivos:** `bot/handlers/menu.py`, `bot/handlers/publicacao.py`, `bot/services/git_service.py`,
  `bot/services/escrita_service.py`, `bot/tests/test_git_service.py`, `bot/tests/test_escrita_service.py`,
  `bot/tests/test_publicacao.py`, `bot/tests/test_menu.py`, `docs/requisitos.md` (§2.12),
  `prompts/nova-conversa.md`.
- **AGENTS.md:** §2, §3.1, §7, §8, §9, §10, §11, §12, §13, §14.1, §14.3, §15, §16.
- **Prompts:** `prompts/prompt-criacao-planejamento-estrategico.md`,
  `prompts/prompt-revisao-risco-planejamento.md`.

---

## 6. Conformidade com AGENTS.md

- [ ] **Backup (Seção 2):** inalterado (backup segue antes de gravar).
- [ ] **Regiões protegidas (Seção 3.1):** `git_service`/handlers → justificativa + teste + comentário
  `# ALTERADO [data]` (§7).
- [ ] **Testes herméticos (Seção 7):** `subprocess`/git mockados; `tmp_path`; sem `.env`/rede.
- [ ] **Handlers (Seção 8):** sem handler novo; ordem de `create_application()` preservada.
- [ ] **Validação (Seção 9):** `py_compile` + import + `pytest bot/tests/ -v`.
- [ ] **Planejamento/aprovação (Seção 10):** este documento; implementar **só após aprovação**.
- [ ] **Checklist (Seção 11):** pré/pós alteração.
- [ ] **Git/commit (Seção 12):** `feat:`/`docs:`; tag sob autorização.
- [ ] **Deploy (Seção 13):** `systemctl restart`; instância única.
- [ ] **Documentação (Seções 15/16):** `CHANGELOG.md` + `prompts/nova-conversa.md`.
- [ ] **Riscos:** R1–R3 (alta/média) → requisitos de aceite com teste (§7).

---

## 7. Análise de Riscos de Funcionamento e Mitigações

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Alta** | `/publicar` continuar sincronizando **antes** de commitar (mantém o deadlock) | `publicacao.py:179-180` | Com remoto à frente e árvore suja, `/publicar` falha → sem saída pelo bot | Commitar **antes** do sync; `pull --rebase`; teste com remoto à frente (mock) |
| R2 | **Alta** | `pull --rebase` com conflito deixa o clone **em rebase** | novo `pull_rebase()` | Operações seguintes falham; árvore inconsistente | `try/except` + `git rebase --abort`; manter alterações; mensagem clara; teste |
| R3 | **Média** | Guarda bloqueia indevidamente (falso positivo de `status_limpo`) | `menu.py` (guarda) / `git_service.py:123` | Usuário impedido de editar sem pendência real | Mensagem orienta `/publicar`/`/restaurar`; teste com árvore limpa e suja |
| R4 | **Média** | Guarda toca fluxos protegidos e pode quebrar entrada de nova/editar/remover | `menu.py:311/373/527` | Fluxo não inicia / erro de import | Comentário `# ALTERADO [data]`; testes de entrada das 3 ações |
| R5 | **Média** | `/restaurar` deixa árvore suja de propósito; sem orientação, gera confusão | `publicacao.py` (restaurar) | Usuário tenta editar e é bloqueado | Documentar que restaurar exige `/publicar`; mensagem após restaurar |
| R6 | Baixa | `status_limpo()` pode ver arquivos não relacionados (ex.: `LICENSE` tocado) | `git_service.py:125` | Bloqueio por causa alheia ao README | Mensagem orienta publicar/restaurar; aceitável (clone é gerenciado pelo bot) |
| R7 | Baixa | Mensagens novas sem escape Markdown | handlers | `Can't parse entities` se houver `_` | Mensagens estáticas (sem valores dinâmicos) — sem risco de escape |
| R8 | Baixa | Testes tocando git real | novos testes | Viola §7 | Mockar `GitService`/`subprocess`; `tmp_path` |
| R9 | Baixa | Deploy não efetivado | systemd | Mudança não entra em produção | `systemctl restart` (§13) |
| R10 | **Média** | Guarda bloqueia **para sempre** se houver arquivo não-README modificado/untracked no clone | `status_limpo()` = `status --porcelain` (`git_service.py:125`) vs commit só do README (`git_service.py:149-164`) | `/publicar` commita só o README; a árvore nunca "limpa" ⇒ edições bloqueadas indefinidamente | Definir pendência como **README modificado** (`git status --porcelain -- README.md`); teste com untracked não-README |
| R11 | **Média** | `/restaurar` escreve o README **sem lock/`ocupado()`/hash** (pré-existente) | `publicacao.py:237-266` (vs `menu.py:720-723`) | Restauração concorrente com gravação/publicação corrompe o estado; árvore suja sem controle | Envolver `restaurar_confirmacao` em `lock_escrita()` + checar `ocupado()`; teste |

### Requisitos de aceite

- **R1 — publicação desbloqueada:** `/publicar` commita a edição pendente **antes** de sincronizar e
  conclui com o remoto à frente. *Teste:* árvore suja + `pull --rebase` → `commit` ocorre antes de
  `sincronizar_publicacao`; `push` chamado ao fim.
- **R2 — rebase seguro:** conflito no rebase aborta (`git rebase --abort`) e preserva as alterações.
  *Teste:* mock de `pull_rebase` levantando `GitError` ⇒ `rebase --abort` chamado; estado íntegro.
- **R3 — guarda correta:** nova edição bloqueada com árvore suja e permitida com árvore limpa.
  *Teste:* `cmd_nova`/`cmd_editar`/`cmd_remover` com `status_limpo()` `False` → mensagem e `END`;
  com `True` → segue para o próximo estado.
- **R4 — reforço na gravação:** `aprovacao`/`remover_confirmacao` abortam se a árvore estiver suja.
  *Teste:* mock `status_limpo=False` ⇒ não grava, não commita, retorna `END`.
- **R10 — pendência só do README:** arquivos não-README/untracked **não** bloqueiam edições.
  *Teste:* README limpo + arquivo untracked presente ⇒ guarda **não** bloqueia.
- **R11 — restauração serializada:** `restaurar_confirmacao` roda sob `lock_escrita()` e recusa se
  `ocupado()`. *Teste:* `ocupado()` verdadeiro ⇒ restaurar recusa; caminho feliz adquire o lock.

### Risco residual aceito

- Enquanto houver edição não publicada, o usuário **não** pode iniciar nova edição (por design).
- Conflito real de conteúdo no rebase permanece **abortando** (§2.12), com orientação e preservação.

---

## Arquivos que serão alterados ou consultados

- **Alterados:**
  - `bot/services/git_service.py` — `pull_rebase()`/`sincronizar_publicacao()` (+ `commits_pendentes()`).
  - `bot/services/escrita_service.py` — helper de sync de publicação + `MENSAGEM_PUBLICACAO_PENDENTE`.
  - `bot/handlers/menu.py` — guarda em `cmd_nova`/`cmd_editar`/`cmd_remover` e reforço em
    `aprovacao`/`remover_confirmacao` (região protegida §3.1).
  - `bot/handlers/publicacao.py` — `publicar_confirmacao` (commit antes do sync; rebase); mensagem do `/restaurar`.
  - `bot/tests/test_git_service.py`, `bot/tests/test_escrita_service.py`,
    `bot/tests/test_menu.py`, `bot/tests/test_publicacao.py` — casos R1–R4.
  - `docs/requisitos.md` (§2.12), `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
- **Consultados (sem alteração):** `bot/handlers/commands.py`, `bot/handlers/state_manager.py`,
  `bot/main.py`, `AGENTS.md`, `docs/planejamento-menu-comandos-telegram.md`.

## Dependências e Edge Cases

- **Dependências:** apenas `git` (CLI, já usado) e `subprocess` (isolável); **sem** nova dependência.
- **Edge cases:**
  - E1 — Árvore suja ao iniciar nova edição ⇒ bloqueio com orientação (R3).
  - E2 — Árvore suja no momento de gravar (corrida) ⇒ reforço aborta (R4).
  - E3 — `/publicar` com árvore suja ⇒ **commita primeiro**, depois `fetch` + `pull --rebase` + `push` (R1).
  - E4 — `/publicar` com árvore limpa e sem commits ⇒ "nada a publicar".
  - E5 — Conflito no rebase ⇒ `git rebase --abort`; alterações preservadas (R2).
  - E6 — `/restaurar` permitido mesmo com árvore suja; após restaurar, exige `/publicar` (R5).
  - E7 — Autor do commit via `-c user.name/user.email` (já em `commit()`); não persiste no repo.
  - E8 — Nada de `reset --hard`/force-push; rebase só de commits locais (§12.7).
  - E9 — Sincronização de gravação mantém `--ff-only`; rebase só na publicação.
  - E10 — Testes herméticos (git mockado) (R8).
  - E11 — Pendência considera **só o README**; untracked/não-README não bloqueiam (R10).
  - E12 — `/restaurar` sob `lock_escrita()` + `ocupado()` (R11).

## Conformidade com AGENTS.md

- [ ] Backup: Seção 2 — inalterado (antes de gravar)
- [ ] Regiões protegidas: Seção 3.1 — `git_service`/handlers justificados + testes (§7)
- [ ] Testes herméticos: Seção 7 — git mockado; `tmp_path` (R8)
- [ ] Handlers/ConversationHandler: Seção 8 — sem handler novo; ordem preservada
- [ ] Validação: Seção 9 — `py_compile` + import + `pytest`
- [ ] Planejamento (aprovação): Seção 10 — **este documento**; implementar só após aprovação
- [ ] Checklist: Seção 11
- [ ] Git/commit: Seção 12 — `feat:`/`docs:`; tag sob autorização
- [ ] Deploy/systemd: Seção 13 — restart; instância única (R9)
- [ ] Documentação: Seções 15 e 16 — `CHANGELOG.md` + `prompts/nova-conversa.md`
- [ ] Análise de Riscos: R1–R3 alta/média + R4–R5 e R10–R11 médias → requisitos de aceite (§7)

---

## Decisões a aprovar (AGENTS.md §10)

1. **Guarda de edição** em `/nova`, `/editar`, `/remover` quando a árvore estiver suja, **mais** o
   reforço antes de gravar em `aprovacao`/`remover_confirmacao`.
2. **`/publicar` commita antes de sincronizar** e sincroniza com `pull --rebase` (não `--ff-only`).
3. **`/restaurar` não commita** (mantém o modelo "commit só no `/publicar`"); após restaurar, o
   usuário deve publicar. **Além disso, `/restaurar` passa a rodar sob `lock_escrita()` + `ocupado()`** (R11).
4. **`docs/requisitos.md §2.12`** passa a prever a regra de bloqueio e o `pull --rebase` na publicação.
5. **Mensagem de commit** no `/publicar`: manter `chore: atualiza comunidades pelo bot`.
6. **Pendência restrita ao README** (R10): a guarda considera `git status --porcelain -- README.md`,
   ignorando arquivos não-README/untracked.

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
