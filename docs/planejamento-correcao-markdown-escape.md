# Planejamento de Correção: escape Markdown nas mensagens do bot

**Data:** 21/10/2026
**Versão:** 1.3
**Foco:** `bot/handlers/` (mensagens enviadas ao Telegram)
**Status:** **implementado, validado e em produção** (235 testes; restart systemd efetivado).
Diagnóstico confirmado (§14.1); revisão de risco R1–R4 incorporada (§12); R6 concluído.

---

## 1. Resumo Executivo

- **Problema:** mensagens enviadas com `parse_mode="Markdown"` falham com
  `Can't parse entities: can't find end of the entity`.
- **Causa raiz:** URLs do README contendo `_` (ex.: `t.me/elug_pa`) são interpoladas cruas em
  Markdown legado v1; o `_` abre uma entidade de itálico que nunca fecha.
- **Correção:** escapar os valores dinâmicos com `telegram.helpers.escape_markdown(..., version=1)`
  apenas onde não há code span (crases já protegem).
- **Escopo incluído:** `bot/handlers/menu.py`, `bot/tests/test_menu.py`, `CHANGELOG.md`.
- **Escopo NÃO incluído:** migração para `parse_mode="HTML"`; correção do bug latente de
  `cmd_listar` (`menu.py:615`); qualquer alteração em `bot/handlers/publicacao.py`; escrita no
  README.

---

## 2. Diagnóstico (§14.1)

- **Comportamento atual (`bot/handlers/menu.py:191-192`):** `texto_resumo_comunidade` monta
  `• *Nome* — Tipo (url)` com a URL crua e a mensagem é enviada com `parse_mode="Markdown"`
  (`menu.py:527` e `menu.py:492`). O `error_handler` (`bot/handlers/commands.py:53`) registra a
  exceção.
- **Comportamento esperado:** exibir nome e URL literalmente, sem que o parser do Telegram tente
  interpretá-los como marcação.
- **Ponto exato da divergência:** interpolação de texto dinâmico não escapado em mensagens
  Markdown; o gatilho é o `_` das URLs.
- **Evidência:**
  - Log de produção (systemd):
    ```
    17:25:53 - bot.handlers.commands - ERROR - Exceção ao tratar update:
    Can't parse entities: can't find end of the entity starting at byte offset 222
    17:26:20 - (idêntico)
    ```
  - Varredura READ-ONLY do README: **15 URLs contêm `_`** (`t.me/elug_pa`, `php_belem`,
    `sqlnorte_oficial`, `GruPy_Belem`, …).
  - Reprodução do escape (READ-ONLY):
    `escape_markdown("Elug (https://t.me/elug_pa)", version=1)` →
    `'Elug (https://t.me/elug\\_pa)'`.

---

## 3. Causa raiz

- **Técnica:** o Markdown legado (v1) do Telegram interpreta `_..._` como itálico. Uma URL com um
  único `_` abre a entidade e não a fecha → o servidor rejeita o `sendMessage` com
  `Can't parse entities`. O conteúdo dinâmico (nome, seção, URL) é interpolado sem escape.
- **Hipóteses investigadas e descartadas:**
  - *Nomes de comunidade com caracteres especiais* → **descartada**: varredura de
    `repositorio/README.md` não encontrou `_ * [ ] `` ` `` em nomes.
  - *Nomes de seção com caracteres especiais* → **descartada**: os títulos `## <emoji> <Título>`
    não contêm metacaracteres.
  - *Valores dinâmicos em `publicacao.py`* → **descartada**: todos já estão em code span/fenced
    block (`texto_backups`, `texto_publicacao`, hash, `backup.name`, diff), que o Telegram não
    parseia.
  - *Falha de deploy/systemd (instância dupla)* → **descartada**: unit `active`/`enabled`,
    instância única, sem `409 Conflict` no log.

---

## 4. Correção proposta

- **Mudança mínima:** helper de escape + aplicação nos pontos que interpolam texto dinâmico fora
  de code span.
- **Helper (em `bot/handlers/menu.py`, junto aos helpers puros):**
  ```python
  from telegram.helpers import escape_markdown


  def _md(texto) -> str:
      """Escapa texto dinâmico para Markdown legado (v1) do Telegram."""
      return escape_markdown(str(texto), version=1)
  ```
- **Pontos a alterar (somente `bot/handlers/menu.py`):**

  | Local | O que escapar | Observação |
  |---|---|---|
  | `texto_resumo_comunidade` (l.191-192) | nome + cada URL | **ponto do crash** |
  | `texto_preview` (l.180-181) | nome + seção | `render_linha` fica em crases → não escapar |
  | `texto_lista_secoes` (l.137-138) | nome da seção | |
  | `aplicar_no_doc` (l.206, 209, 212) | nome/seção | resumo pós-aplicação |
  | `editar_nome` (l.369), `remover_nome` (l.452), `buscar_nome` (l.525) | nome/seção | |
  | `cmd_listar` (l.622-623) | nome/seção | |

- `bot/handlers/publicacao.py` **não muda** (ver §3).
- **Dependência:** `telegram.helpers.escape_markdown` (já disponível em `python-telegram-bot` 22.8;
  sem nova dependência).

---

## 5. Riscos e natureza (§3.1, §14.2, §14.3)

- **Natureza (§14.2):** **correção** — o comportamento muda (mensagens deixam de falhar). Não é
  refatoração; não há critério único de refatoração a aplicar.
- **Nível de risco (§14.3):** **médio** — altera `bot/handlers/` e exige validação local do fluxo.
- **Região protegida (§3.1):** toca a **orquestração de preview/aprovação** via `texto_preview`.
  **Justificativa:** o texto de preview interpola nome/seção não escapados e sofre o mesmo defeito;
  **mitigação:** teste de regressão do preview (§6) e comentário
  `# ALTERADO [21/10/2026]: escapa texto dinâmico (fix Can't parse entities)`.
- **Não toca:** `create_application()`, `state_manager.py`, `bot/services/`, `bot/config.py`,
  `publicacao.py`.

---

## 6. Testes de regressão (§7)

- **Casos que devem continuar passando:** a suíte atual de `bot/tests/test_menu.py`
  (`texto_lista_secoes`, `texto_preview`, `texto_resumo_comunidade`, …), garantindo que a marcação
  intencional (`*Nome*`, `` `código` ``) permanece intacta.
- **Novo caso que cobre o bug:** `texto_resumo_comunidade` com URL `https://t.me/elug_pa` → o
  resultado contém `elug\_pa`.
- **Casos adicionais:** `texto_preview` e `texto_lista_secoes` com nome/seção contendo `_`/`*` →
  escapados.
- **Hermeticidade (§7):** sem `.env` real, sem rede; isolar caminhos com `tmp_path` + `monkeypatch`;
  mockar `requests`, `subprocess` e a API do Telegram. Os helpers são puros e testáveis isoladamente.

---

## 7. Backup, Rollback e Validação (§2, §11, §9)

- **Backup (§2):** **não aplicável** — a correção não escreve no README (apenas código), logo não há
  `README_YYYYMMDD_HHMMSS.bak`. Nenhum arquivo de `repositorio/` é alterado.
- **Rollback (§11):**
  - `git revert <commit>` (preserva o histórico); ou
  - `git checkout <tag|commit> -- bot/handlers/menu.py` para reverter arquivo isolado.
- **Validação (§9):**
  ```bash
  python3 -m py_compile bot/handlers/menu.py
  python3 -c "from bot.handlers.commands import create_application; print('OK')"
  pytest bot/tests/ -v
  ```

---

## 8. Documentação e Encerramento (§15, §16)

- **CHANGELOG (§15):** entrada em `[Unreleased]` (skill `changelog-convention`).
- **Encerramento (§16):** resumo da sessão e atualização de `prompts/nova-conversa.md` se o estado
  do bot mudar.

---

## 9. Git e Commits (§11, §12, §14.3)

- **Commit sob autorização (§12.1)** — não commitar por iniciativa própria.
- **Mensagem sugerida (§12.4):**
  ```
  fix: escapa valores dinâmicos em mensagens Markdown

  URLs com "_" no README quebravam o envio com "Can't parse entities".
  Aplica escape_markdown(version=1) aos valores dinâmicos fora de code span,
  preservando a marcação intencional.
  ```

---

## 10. Observação separada (fora deste fix)

`cmd_listar` (`menu.py:615`) tem bug latente:

```python
linhas = [f"📋 *{secao.nome}*" for secao in doc.secoes if lista_secoes_editaveis(doc)]
```

O `if lista_secoes_editaveis(doc)` é condição constante dentro da compreensão, então um cabeçalho
`📋 *...*` é repetido por seção. Tratar em correção à parte, se desejado.

---

## 11. Referências

- **AGENTS.md:** §2 (backup), §3.1 (regiões protegidas), §7 (testes herméticos), §9 (validação),
  §10 (planejamento/aprovação), §11 (checklist), §12 (Git/commit), §14.1 (diagnóstico),
  §14.2 (natureza), §14.3 (risco), §15 (CHANGELOG), §16 (encerramento).
- **Arquivos:** `bot/handlers/menu.py`, `bot/handlers/commands.py`, `bot/handlers/publicacao.py`,
  `bot/tests/test_menu.py`, `docs/requisitos.md`, `prompts/nova-conversa.md`.

---

## 12. Análise de Riscos de Funcionamento e Mitigações

Revisão de risco (prompt `prompts/prompt-revisao-risco-planejamento.md`), cobrindo as dimensões
obrigatórias. Riscos de gravidade **alta/média** viram **REQUISITOS DE ACEITE** com teste de
regressão.

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Alta** | Escapar o **valor do modelo** (nome/link) em vez da **string de exibição** | `render_linha` em `menu.py:183`; gravação via `readme_service.render_linha` (`readme_service.py:390,398`) | README gravado com `\_`/`\*` (corrupção da fonte da verdade) | Aplicar `_md` **somente** em strings enviadas ao Telegram; nunca em `render_linha`/`Comunidade`/`Link` |
| R2 | **Média** | Escapar conteúdo já dentro de code span/fenced | `menu.py:183` (`` `{render_linha(...)}` ``), `publicacao.py:99,109` | Barra invertida visível; quebra de `test_menu.py:156` (`"**GruPy Pará**"`) | Não escapar trechos entre crases/fences; teste do preview mantendo `**...**` |
| R3 | **Média** | Alterar região protegida (preview/aprovação) sem rastreio | `menu.py:175-186` (`texto_preview`) | Divergência silenciosa do ponto pós-confirmação | Comentário `# ALTERADO [21/10/2026]: ...` + teste de regressão do preview |
| R4 | **Média** | Regressão na suíte atual (232 testes) por mudança de saída dos helpers | `test_menu.py:122-163`, `test_publicacao.py:131-158` | Testes de texto exato falham | Rodar `pytest bot/tests/` antes de concluir; ajustar só se legítimo |
| R5 | Baixa | Import/ordem do helper | `menu.py` (topo dos helpers puros) | `NameError` no import da aplicação | `from telegram.helpers import escape_markdown` no topo; `_md` antes do uso; validar import |
| R6 | Baixa | Deploy não efetivado | serviço systemd | Correção não entra em produção | `systemctl restart atualizar-repositorio-bot.service` (§13/§6.1) |
| R7 | Baixa | Duplo escape | `menu.py:525` + `texto_resumo_comunidade` (`menu.py:191`) | `\\_` visível | Escapar cada valor uma única vez; não escapar a saída do helper novamente |

### Requisitos de aceite

- **R1 — não corromper o README:** escapar apenas texto de exibição.
  *Teste:* após `aplicar_no_doc` + `persistir`, a linha gravada no README não contém `\`
  (estende `test_menu.py:213-235`).
- **R2 — preservar code spans:** conteúdo em crases não é escapado.
  *Teste:* `texto_preview` mantém `**GruPy Pará**` (`test_menu.py:156`) e o resumo escapa a URL
  (`https://t.me/elug_pa` → `elug\_pa`).
- **R3 — região protegida rastreada:** comentário `# ALTERADO` + teste do preview.
  *Teste:* `texto_preview` com nome contendo `_` → nome escapado; seção intacta.
- **R4 — suíte verde:** `pytest bot/tests/` sem regressões.

### Risco residual aceito

- Bug latente de `cmd_listar` (`menu.py:615`) permanece (fora de escopo — ver §10).
- Migração para `parse_mode="HTML"` fica como evolução futura (não cobre metacaracteres além de
  `_ * `` ` `` `[`).

---

## Arquivos que serão alterados ou consultados

- **Alterados:** `bot/handlers/menu.py`, `bot/tests/test_menu.py`, `CHANGELOG.md`.
- **Consultados (sem alteração):** `bot/handlers/publicacao.py`, `bot/handlers/commands.py`,
  `AGENTS.md`, `docs/requisitos.md`.

## Dependências e Edge Cases

- **Dependências:** `telegram.helpers.escape_markdown` (já presente em PTB 22.8); nenhuma nova
  dependência externa; sem alteração de `requirements.txt`.
- **Edge cases:**
  - Code span/fenced permanecem **sem** escape (senão a barra invertida apareceria literal).
  - `escape_markdown` v1 escapa `_`, `*`, `` ` `` e `[` — cobre os caracteres que quebram.
  - Nome/URL com `[` ou `` ` `` também passa a ser tratado.
  - `render_linha` dentro de crases em `texto_preview` **não** é escapado (já protegido).

## Conformidade com AGENTS.md

- [x] Backup: Seção 2 — **N/A** (sem escrita no README; declarado em §7)
- [x] Regiões protegidas: Seção 3.1 — `texto_preview` justificado + teste (§5, §6)
- [x] Testes herméticos: Seção 7 — +3 em `test_menu.py` (`TestEscapeMarkdown`)
- [x] Validação: Seção 9 — `py_compile` OK, import OK, `pytest` → **235 passed**
- [x] Planejamento (aprovação antes de implementar): Seção 10 — aprovado pelo usuário
- [x] Checklist: Seção 11
- [x] Git/commit: Seção 12 — mensagem em §9
- [x] Deploy/systemd: Seção 13 — restart efetivado (R6 concluído; bot `active`, instância única)
- [x] Diagnóstico/risco: Seções 14.1 e 14.3 — §2 e §5
- [x] Análise de Riscos de Funcionamento e Mitigações: R1–R4 com teste de regressão — §12
- [x] CHANGELOG: Seção 15 — entradas em `[Unreleased]`
- [x] Encerramento: Seção 16 — resumo da sessão + `prompts/nova-conversa.md` atualizado
