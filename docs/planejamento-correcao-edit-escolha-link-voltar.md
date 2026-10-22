# Planejamento de Correção: primeiro clique em "Links" no `/editar` + botão "Voltar" no menu de links

**Data:** 21/10/2026
**Versão:** 1.1
**Foco:** `bot/handlers/menu.py` (fluxo de edição — escolha de campo + menu de links)
**Status:** **implementado, validado e em produção** (337 testes; deploy efetivado; tag `v0.7.1`
publicada).
**Revisão de risco incorporada** (R1–R7; `prompts/prompt-revisao-risco-planejamento.md`).
**Diagnóstico (§14.1):** **confirmado pelo usuário** (comportamento atual × esperado × divergência).

---

## 1. Resumo Executivo

- **Problema (2 itens):**
  1. No `/editar`, o **primeiro** clique em **"Links"** exibe "✏️ Qual é o novo nome?" em vez do menu
     de links; só o **segundo** clique mostra a lista de links. O mesmo defeito atinge "Nome" e
     "Nome e links" no primeiro clique (retornam o estado errado).
  2. O **menu de links** não tem botão **"↩️ Voltar"** (só `/cancelar`).
- **Causa raiz:** `_oferecer_edicao` retorna `EDITAR_ESCOLHA` **sem** atualizar `conversa.estado`;
  `editar_escolha` calcula o próximo estado via `proximo_estado`, que lê `conversa.estado`
  **defasado** (`EDITAR_NOME`) e devolve `EDITAR_ESCOLHA`.
- **Correção:** (a) sincronizar `conversa.estado = EDITAR_ESCOLHA` em `_oferecer_edicao`;
  (b) adicionar o botão **"↩️ Voltar"** ao menu de links, retornando à escolha "Nome/Links/Nome e links".
- **Escopo incluído:** `bot/handlers/menu.py` (2 pontos) + `bot/tests/test_menu.py`.
- **Escopo NÃO incluído:** `state_manager.py` (nenhum estado novo); parser/editor do README, backup,
  histórico, git, `config.py`; `/nova`; botão "Voltar" no **nível de seções** da lista (futuro).

---

## 2. Diagnóstico (§14.1)

- **Comportamento atual (`bot/handlers/menu.py`):**
  - `_oferecer_edicao` (`:544-562`) mostra "O que deseja alterar?" com os botões Nome/Links/Nome e
    links e **retorna `EDITAR_ESCOLHA`**, mas **não** seta `conversa.estado`.
  - `editar_escolha` (`:735-747`): `conversa.campo_editar = mapa[query.data]` → `proximo =
    gerenciador.proximo_estado(conversa)` → `conversa.estado = proximo`; se `proximo is
    EDITAR_LINKS` mostra o menu de links, senão envia `PERGUNTA_EDITAR_NOVO_NOME`.
  - `proximo_estado` (`bot/handlers/state_manager.py:172-195`) ramifica por `conversa.estado`
    (ramo `if estado is EDITAR_NOME: return EDITAR_ESCOLHA`, `:178-179`).
- **Comportamento esperado:** o **primeiro** clique deve respeitar o campo escolhido
  (Links → menu de links; Nome/Nome e links → pergunta de nome) e retornar o estado correto
  (`EDITAR_LINKS`/`EDITAR_NOVO_NOME`).
- **Ponto exato da divergência:** `conversa.estado` fica **dessincronizado** do estado real do
  `ConversationHandler` porque `_oferecer_edicao` não o atualiza; `editar_escolha` confia em
  `proximo_estado`, que lê esse campo defasado.
- **Evidência:**
  - Reprodução do usuário: 1º clique em "Links" → "Qual é o novo nome?"; 2º clique → menu de links.
  - Rastreamento do código: `_oferecer_edicao` retorna `EDITAR_ESCOLHA` sem `conversa.estado = …`;
    `editar_escolha:742` depende de `proximo_estado`, que usa `conversa.estado`.
  - No caminho de `aprovacao` (`:1172`) o estado é setado explicitamente — o que confirma que o
    padrão esperado é manter `conversa.estado` coerente com o estado retornado.

---

## 3. Causa raiz

- **Técnica:** o fluxo mantém **dois** registros de estado: o do `ConversationHandler` (PTB) e o
  campo `ConversaUsuario.estado` (usado por `proximo_estado`). `_oferecer_edicao` atualiza apenas o
  primeiro (via `return`). Ao clicar, `editar_escolha` chama `proximo_estado` com
  `conversa.estado == EDITAR_NOME` (defasado) → o ramo `EDITAR_NOME → EDITAR_ESCOLHA`
  (`state_manager.py:178`) ignora o `campo_editar` e devolve `EDITAR_ESCOLHA`. No 2º clique,
  `conversa.estado` já é `EDITAR_ESCOLHA` (`menu.py:743`), então o ramo correto roda.
- **Hipóteses investigadas e descartadas:**
  - *`callback_data` errado* → descartada: o mapa `{"edit_links": CAMPO_LINKS, …}` (`:740`) está
    correto; o `campo_editar` é setado antes do cálculo.
  - *Registro/ordem dos `CallbackQueryHandler`* → descartada: o handler roda (a mensagem muda).
  - *`conferir_hash`/lock* → descartada: não há escrita nesse passo.

---

## 4. Correção proposta (mudança mínima)

**Arquivo:** `bot/handlers/menu.py` (região protegida §3.1).

1. **Sincronizar o estado na origem** — em `_oferecer_edicao`, setar `conversa.estado =
   EstadoConversa.EDITAR_ESCOLHA` antes de `return`. Corrige, de uma vez, os três botões (o caminho
   é o mesmo para `editar_nome` e `editar_candidato`).
   ```python
   conversa.estado = EstadoConversa.EDITAR_ESCOLHA   # ALTERADO [21/10/2026]: mantém proximo_estado coerente
   ...
   return EstadoConversa.EDITAR_ESCOLHA
   ```
   *(Defesa extra opcional: setar o mesmo em `editar_escolha` logo antes de `proximo_estado`.)*

2. **Botão "↩️ Voltar" no menu de links:**
   - Extrair o teclado da escolha para um helper único `teclado_escolha_edicao()` (evita duplicação
     com `_oferecer_edicao`).
   - Adicionar ao `teclado_links` uma linha `[↩️ Voltar]` com **novo** callback `edit_lk_voltar`
     (distinto do `edit_lk_back` do submenu, que volta ao menu de links).
   - Novo handler `editar_link_voltar_escolha` (padrão `^edit_lk_voltar$`): limpa
     `link_indice`/`link_tipo`, reenvia a mensagem "O que deseja alterar?" com o teclado de escolha e
     retorna `EDITAR_ESCOLHA` (rascunho preservado).

**Dependências:** nenhuma nova (PTB já presente); `state_manager.py` **não muda**.

---

## 5. Riscos e natureza (§3.1, §14.2, §14.3)

- **Natureza (§14.2):** **correção** — o comportamento muda (1º clique passa a acertar; novo Voltar).
  Não é refatoração; não há critério único de refatoração.
- **Nível de risco (§14.3):** **médio** — altera `bot/handlers/` e a coerência de estado.
- **Região protegida (§3.1):** `menu.py` (orquestração de `EDITAR_ESCOLHA`/menu de links).
  **Justificativa:** ponto exato do bug; **mitigação:** testes de regressão + comentário
  `# ALTERADO [21/10/2026]`.
- **Não toca:** `state_manager.py`, `bot/services/`, parser/editor, backup, histórico, git,
  `create_application`, `config.py`.

### Riscos (R1…Rn)

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Média** | Correção de estado alterar outras transições do `/editar` | `_oferecer_edicao` (`menu.py:562`); `proximo_estado` (`state_manager.py:172-195`) | Regressão em Nome/Links/Ambos | Teste do 1º clique nos 3 botões + fluxo completo até o preview |
| R2 | **Média** | Novo callback "Voltar" registrado fora do estado (§8) ou colidindo padrões | `menu.py` (registro em `EDITAR_LINKS`) | Fluxo quebra / botão inerte | `CallbackQueryHandler` **dentro** do estado, padrão `^edit_lk_voltar$` distinto; teste |
| R3 | **Média** | "Voltar" perder o rascunho/links editados | `editar_link_voltar_escolha` | Usuário perde edições | Preservar `conversa.rascunho`; teste |
| R4 | Baixa | Duplicação do teclado de escolha divergir | `_oferecer_edicao` × novo handler | UI inconsistente | Helper único `teclado_escolha_edicao()`; teste |
| R5 | Baixa | `conversa.estado` voltar a dessincronizar em outros handlers | retornos sem `conversa.estado = …` | Bug semelhante futuro | Registrar observação; alvo mínimo desta correção (auditoria futura) |
| R6 | Baixa | Deploy não efetivado | systemd | Correção fora de produção | `systemctl restart` (§13) |
| R7 | **Média** | "Voltar" no caminho "Nome e links" (`campo_editar=ambos`) perder o rascunho já editado | `editar_link_voltar_escolha` | Perda de edição (nome/links) ou duplicidade | Preservar `conversa.rascunho`; teste do caminho "ambos" até o preview |

### Requisitos de aceite

- **R1 — 1º clique correto:** em `EDITAR_ESCOLHA`, um clique em `edit_links` leva a `EDITAR_LINKS`
  (menu de links); `edit_nome`/`edit_ambos` levam a `EDITAR_NOVO_NOME`. *Teste:* 3 casos.
- **R2 — Voltar funcional:** o botão `edit_lk_voltar` retorna a `EDITAR_ESCOLHA` com o teclado de
  escolha. *Teste:* handler + montagem (padrão dentro do estado).
- **R3 — rascunho preservado:** após "Voltar", `conversa.rascunho.links` mantém as edições. *Teste.*
- **R4 — teclado único:** escolha vinda de `_oferecer_edicao` e de "Voltar" é idêntica. *Teste.*
- **R7 — caminho "ambos":** "Voltar" durante "Nome e links" não perde o nome já digitado nem os
  links editados. *Teste:* editar nome → menu de links → "Voltar" → preview mantém ambos.

### Risco residual aceito

- Dessincronização de `conversa.estado` em **outros** handlers (`nova_*`, `publicacao`, …) permanece
  latente — fora do escopo desta correção (registrar como **auditoria futura**).
- "Voltar" no **nível de seções** da lista (`/editar`) continua ausente (evolução futura).
- Cobertura verificada: os **2** caminhos para `EDITAR_ESCOLHA` estão tratados — `_oferecer_edicao`
  (corrigido) e `aprovacao` CB_EDITAR (`menu.py:1172-1174`, que já seta o estado).

---

## 6. Testes de regressão (§7)

- **Devem continuar passando:** `test_menu.py` (fluxos de edição/nova/remover, lista, links),
  `test_state_manager.py` (`proximo_estado`), `test_link_template.py`.
- **Novos casos (herméticos, Telegram mockado):**
  - 1º clique em `edit_links` → `EDITAR_LINKS` (menu) — cobre o bug.
  - 1º clique em `edit_nome` → `EDITAR_NOVO_NOME`; 1º clique em `edit_ambos` → `EDITAR_NOVO_NOME`.
  - `edit_lk_voltar` → `EDITAR_ESCOLHA` com teclado de escolha; `rascunho.links` preservado.
  - Registro: `montar_conversation_handler()` inclui o padrão `edit_lk_voltar` dentro de `EDITAR_LINKS`.
- **Hermeticidade (§7):** sem `.env`/rede; `tmp_path` + `monkeypatch`; fakes do Telegram.

---

## 7. Rollback (§2)

- **Código:** `git revert <commit>` (preserva o histórico) ou
  `git checkout <tag|commit> -- bot/handlers/menu.py`.
- **README:** **N/A** — a correção não escreve no `repositorio/README.md`; não há `README_*.bak`.

---

## 8. Referências

- **Arquivos:** `bot/handlers/menu.py`, `bot/handlers/state_manager.py`, `bot/tests/test_menu.py`,
  `docs/planejamento-edicao-links-botoes.md`, `prompts/nova-conversa.md`.
- **AGENTS.md:** §2 (backup — N/A), §3.1 (regiões protegidas), §7 (testes), §8 (handlers/callbacks),
  §9 (validação), §10 (planejamento/aprovação), §11 (checklist), §12 (Git/commit), §13 (deploy),
  §14.1 (diagnóstico), §14.2 (natureza), §14.3 (risco), §15 (CHANGELOG), §16 (encerramento).

---

## 9. Conformidade com AGENTS.md

- [ ] Backup: Seção 2 — **N/A** (sem escrita no README; §7)
- [ ] Regiões protegidas: Seção 3.1 — `menu.py` justificado + teste (§5, §6)
- [ ] Testes herméticos: Seção 7 — casos novos em `test_menu.py` (§6)
- [ ] Validação: Seção 9 — `py_compile` + import + `pytest bot/tests/ -v`
- [ ] Planejamento (aprovação antes de implementar): Seção 10 — este documento
- [ ] Checklist: Seção 11
- [ ] Git/commit: Seção 12 — mensagem em §Commit
- [ ] Deploy/systemd: Seção 13 — restart (R6)
- [ ] Diagnóstico/risco: Seções 14.1 e 14.3 — §2/§3 e §5
- [ ] Riscos: R1–R7 com teste de regressão — §5/§6
- [ ] CHANGELOG: Seção 15 — entrada em `[Unreleased]`
- [ ] Encerramento: Seção 16 — resumo da sessão

**Commit sugerido (§12.4):**
```
fix: corrige primeiro clique na escolha de edição e adiciona Voltar nos links

_oferecer_edicao não atualizava conversa.estado, então o 1o clique em
Links exibia a pergunta de nome. Sincroniza o estado e adiciona o botão
Voltar ao menu de links (retorna à escolha Nome/Links/Nome e links).
```

---

## Arquivos que serão alterados ou consultados

- **Alterados:** `bot/handlers/menu.py` (`_oferecer_edicao`, `teclado_links`, novo handler
  `editar_link_voltar_escolha`, helper `teclado_escolha_edicao`, registro em `EDITAR_LINKS`),
  `bot/tests/test_menu.py`, `CHANGELOG.md`.
- **Consultados (sem alteração):** `bot/handlers/state_manager.py`, `docs/planejamento-edicao-links-botoes.md`,
  `prompts/nova-conversa.md`, `AGENTS.md`.

## Dependências e Edge Cases

- **Dependências:** nenhuma nova; `state_manager.py` inalterado.
- **Edge cases:**
  - E1 — 1º clique em cada um dos 3 botões (Nome/Links/Nome e links) → estado correto (R1).
  - E2 — "Voltar" com links já editados → rascunho preservado (R3).
  - E3 — Callback "Voltar" em mensagem antiga/estado diferente → padrão específico; sem efeito colateral.
  - E4 — "Voltar" sem comunidade selecionada (sessão expirada) → tratar com mensagem/`/editar`.
  - E5 — Colisão com `edit_lk_back` (submenu → menu) → nome distinto `edit_lk_voltar`.
  - E6 — Teclado de escolha único (helper) para as duas origens (R4).
  - E7 — "Voltar" no caminho "Nome e links" preserva nome já digitado e links editados (R7).

## Conformidade com AGENTS.md

- [ ] Backup: Seção 2 — **N/A**
- [ ] Regiões protegidas: Seção 3.1 — `menu.py` (§5)
- [ ] Testes herméticos: Seção 7 — §6
- [ ] Validação: Seção 9
- [ ] Planejamento (aprovação): Seção 10 — **este documento**
- [ ] Checklist: Seção 11
- [ ] Git/commit: Seção 12
- [ ] Deploy/systemd: Seção 13 — R6
- [ ] Diagnóstico/risco: Seções 14.1 e 14.3 — §2/§3/§5
- [ ] Riscos: R1–R7 com teste de regressão — §5/§6
- [ ] CHANGELOG: Seção 15
- [ ] Encerramento: Seção 16

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
