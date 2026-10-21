# Planejamento Estratégico: gerenciador de links por botões no `/editar`

**Data:** 21/10/2026
**Versão:** 1.1
**Foco:** `bot/handlers/menu.py`, `bot/handlers/state_manager.py` (+ novo
`bot/services/link_template.py`)
**Status:** **implementado e validado** (330 testes; `py_compile` + import OK). Pendente **deploy**
(`systemctl restart`) e **commit/tag** sob autorização (§12).
**Revisão de risco incorporada** (R1–R18; `prompts/prompt-revisao-risco-planejamento.md`).
**Origem:** análise das sugestões (1) entrada por "handle" por tipo e (2) remover link específico.

---

## 1. Resumo Executivo

- **Objetivo:** evoluir a edição de **links** no `/editar` de "substituir a lista inteira por texto"
  para um **gerenciador por botões**: listar os links existentes e, para cada um, **alterar valor**
  ou **remover**; além de **adicionar** link pelo catálogo de tipos.
- **Sugestão 1 (handle por tipo):** ao alterar/adicionar um link, o usuário pode enviar **apenas o
  identificador** (ex.: Instagram → `username`), montando a URL a partir de um **template** do tipo;
  se enviar uma **URL completa**, ela é usada como está (fallback universal).
- **Sugestão 2 (remoção):** botão para **remover** um link específico, com confirmação — hoje
  remover 1 link obriga a redigitar todos (`menu.py:690`).
- **Escopo incluído:**
  - Estado `EDITAR_LINKS` reformulado como **menu de links** (callbacks + colar vários como fallback).
  - Submenu por link: **alterar valor** / **remover** / voltar.
  - **Adicionar link** via **catálogo de tipos** (`ORDEM_BADGES`).
  - **Templates** tipo→URL em módulo puro `bot/services/link_template.py`.
  - Bloqueio de remoção do **último** link (invariante "ao menos 1 link").
  - Testes herméticos e documentação.
- **Escopo NÃO incluído:**
  - `/nova` (mantém o colar vários por texto; poderá reusar o gerenciador depois).
  - Correção automática de URLs existentes fora do padrão (edição cirúrgica).
  - Alterar parser/editor do README, backup, histórico, git, `create_application`, `config.py`.
- **Conclusão:** viável e coerente com o `/editar` já baseado em botões. **Risco médio**: toca a
  máquina de estados (região protegida §3.1) e introduz **dado de domínio novo** (templates), mas a
  regra "URL completa tem precedência" neutraliza a ambiguidade dos templates.

---

## 2. Viabilidade Técnica

### O que já existe (funcionando)

- `Link` = `(tipo, url)` (`bot/models/comunidade.py:8`) e `parse_links` (`menu.py:135`).
- Catálogo canônico de tipos: `ORDEM_BADGES`/`BADGES` (`readme_service.py:24-59`, §2.4).
- Preview/aprovação e gravação cirúrgica (`_enviar_preview`, `menu.py:349`; `render_linha`).
- Padrão de botões já dominado (candidatos/lista): índices em `callback_data`, estado de desvio.
- Fluxo `/editar → Links` atual: `editar_escolha` (`menu.py:654`) → `EDITAR_LINKS` →
  `editar_links` (`menu.py:679`), que hoje **substitui** `conversa.rascunho.links` (`menu.py:690`).

### O que muda (por módulo)

| Módulo | Mudança |
|---|---|
| `bot/handlers/state_manager.py` | **+estado `LINK_VALOR`** e **`LINK_REMOCAO_CONFIRMACAO`** (desvios opcionais); +campos `link_indice`, `link_tipo` em `ConversaUsuario` |
| `bot/handlers/menu.py` | `EDITAR_LINKS` vira **menu de links**; handlers de submenu (alterar/remover/adicionar) e registro de callbacks |
| `bot/services/link_template.py` | **novo** — `TEMPLATES`, `montar_url(tipo, valor)`, `precisa_url_completa(tipo)`, `rotulo_tipo(tipo)` |
| `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py` | novos casos |
| `docs/requisitos.md` §2.4 | nota dos templates por tipo |
| `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md` | registro (§15/§16) |

### Regra central (resolve a ambiguidade dos templates)

```
montar_url(tipo, valor):
  se valor começa com http(s)://  → usa o valor (URL completa, precedência máxima)
  senão, se tipo tem template      → aplica base do tipo (ex.: instagram.com/{valor})
  senão                            → erro: "para {tipo}, envie a URL completa"
```

Assim, tipos ambíguos (YouTube, LinkedIn, WhatsApp, Facebook) permanecem utilizáveis: o handle
atende o caso comum e a URL completa cobre as variantes.

---

## 3. Fluxo Detalhado

### Fluxo do `/editar → Links` (depois)

```
/editar → … → "O que deseja alterar?" [Nome] [Links] [Nome e links]
    └── Links → EDITAR_LINKS (MENU de links)
          🔗 Links de *Comunidade*:
          [1. Instagram] [2. Meetup] …            ← edit_lk_<i> abre o submenu do link i
          [➕ Adicionar link] [✅ Concluir] [📋 Colar vários]

          edit_lk_<i> → submenu do link:
             [✏️ Alterar valor] [🗑️ Remover] [↩️ Voltar]
                 ├── Alterar valor → LINK_VALOR (envia handle ou URL) → volta ao menu
                 ├── Remover → LINK_REMOCAO_CONFIRMACAO [🗑️ Remover] [❌ Cancelar]
                 │       └── se for o ÚLTIMO link → bloqueia (§ invariante)
                 └── Voltar → EDITAR_LINKS

          edit_lk_add → catálogo de tipos → tipo escolhido → LINK_VALOR → volta ao menu
          edit_lk_ok  → _enviar_preview (aprovação)
          texto "Instagram x / Meetup y" → parse_links (modo colar vários, ainda suportado)
```

### Estados e máquina de estados

- `EDITAR_LINKS` (existente) — passa a ser o **menu** (callbacks + texto para colar vários).
- **`LINK_VALOR`** (novo) — aguarda o valor (handle/URL) do link em `conversa.link_indice`/
  `conversa.link_tipo`; ao concluir, aplica `montar_url` e volta a `EDITAR_LINKS`.
- **`LINK_REMOCAO_CONFIRMACAO`** (novo) — confirma a remoção do link `conversa.link_indice`.
- São **desvios opcionais** (como `EDITAR_CANDIDATOS`/`EDITAR_LISTA`); a ordem canônica
  `EDITAR_ESCOLHA → … → PREVIEW` permanece.

### Callbacks (padrões)

| callback_data | Uso |
|---|---|
| `edit_lk_<i>` | abrir submenu do link i |
| `edit_lk_set_<i>` | alterar valor do link i |
| `edit_lk_rm_<i>` | remover link i (vai para confirmação) |
| `edit_lk_rmok` / `edit_lk_rmno` | confirma / cancela remoção |
| `edit_lk_add` | adicionar link (catálogo de tipos) |
| `edit_lk_tp_<i>` | tipo escolhido no catálogo |
| `edit_lk_colar` | dica do modo "colar vários" |
| `edit_lk_ok` | concluir → preview |
| `edit_lk_back` | voltar ao menu |

> **`callback_data` ≤ 64 bytes** (limite do Telegram): usar **índice**, nunca o nome/URL.

### Pontos de alteração (arquivo:linha)

- `menu.py:654-665` — `editar_escolha`: ao escolher `links`, enviar o **menu de links** (não o texto).
- `menu.py:679-694` — `editar_links`: reformular como menu (callbacks) + colar vários.
- `menu.py` — novos handlers de submenu; registro de callbacks em `EDITAR_LINKS`, `LINK_VALOR`,
  `LINK_REMOCAO_CONFIRMACAO`.
- `state_manager.py` — novos estados (enum + `ORDEM_POR_ACAO[EDITAR]`) e campos
  `link_indice`/`link_tipo` (defaults); comentário `# ALTERADO [data]`.
- `bot/services/link_template.py` — **novo** (puro, testável).

### Estrutura proposta (esboço)

```python
# link_template.py
TEMPLATES = {
    "Instagram": "https://instagram.com/{valor}",
    "GitHub": "https://github.com/{valor}",
    "GitLab": "https://gitlab.com/{valor}",
    "Facebook": "https://facebook.com/{valor}",
    "X": "https://x.com/{valor}",
    "YouTube": "https://youtube.com/@{valor}",
    "Telegram": "https://t.me/{valor}",
    "Meetup": "https://meetup.com/{valor}",
    "LinkTree": "https://linktr.ee/{valor}",
    "LinkedIn": "https://linkedin.com/in/{valor}",
    "WhatsApp": "https://wa.me/{valor}",
}
URL_COMPLETA_OBRIGATORIA = {"Site", "Google Drive", "Slack", "Discord"}

def montar_url(tipo: str, valor: str) -> str:
    valor = valor.strip()
    if valor.startswith(("http://", "https://")):
        return valor
    if tipo in TEMPLATES:
        return TEMPLATES[tipo].format(valor=valor.lstrip("@/"))
    raise ValueError(f"para {tipo}, envie a URL completa")
```

---

## 4. Próximos Passos

- **Não necessárias:** novos serviços de backup/histórico/git; alterar parser/editor/validação.
- **Obrigatórias (após aprovação):**
  1. `link_template.py` + testes puros.
  2. `state_manager`: `LINK_VALOR`, `LINK_REMOCAO_CONFIRMACAO`, campos `link_indice`/`link_tipo`.
  3. `menu.py`: menu de links, submenu, adicionar (catálogo), remover (com bloqueio do último),
     alterar valor (com template), registro de callbacks.
  4. Testes herméticos (R1–R8).
  5. `docs/requisitos.md §2.4`, `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
  6. Validação, deploy (`systemctl restart`) e commit/tag (§12).

---

## 5. Referências

- **Arquivos:** `bot/handlers/menu.py` (editar_links, editar_escolha, parse_links, _oferecer_edicao),
  `bot/handlers/state_manager.py`, `bot/models/comunidade.py`, `bot/services/readme_service.py`
  (`ORDEM_BADGES`/`BADGES`), `bot/services/validacao_service.py` ("ao menos 1 link", `:163`),
  `bot/tests/test_menu.py`, `docs/requisitos.md §2.4`, `prompts/nova-conversa.md`.
- **AGENTS.md:** §3.1 (protegidas), §4 (badges/ordem), §7 (testes), §8 (handlers/callbacks),
  §9 (validação), §10 (aprovação), §11 (checklist), §12 (Git), §13 (deploy), §15/§16 (docs).
- **Prompts:** `prompts/prompt-criacao-planejamento-estrategico.md`,
  `prompts/prompt-revisao-risco-planejamento.md`.

---

## 6. Conformidade com AGENTS.md

- [ ] **Backup (Seção 2):** **N/A** — não escreve no README (só no preview/gravação já existente).
- [ ] **Regiões protegidas (Seção 3.1):** `state_manager`/`menu.py` → justificativa + teste +
  comentário `# ALTERADO [data]`.
- [ ] **Handlers/Callbacks (Seção 8):** `CallbackQueryHandler` **dentro** dos estados; nunca global.
- [ ] **Testes herméticos (Seção 7):** `link_template` puro; Telegram mockado.
- [ ] **Validação (Seção 9):** `py_compile` + import + `pytest bot/tests/ -v`.
- [ ] **Planejamento/aprovação (Seção 10):** este documento; implementar **só após aprovação**.
- [ ] **Checklist (Seção 11).**
- [ ] **Git/commit (Seção 12):** `feat:`/`docs:`; tag sob autorização.
- [ ] **Deploy (Seção 13):** restart; instância única.
- [ ] **Documentação (Seções 15/16):** `CHANGELOG.md` + `prompts/nova-conversa.md`.
- [ ] **Riscos:** R1–R6 e R12–R15 (média) → requisitos de aceite com teste (§7).

---

## 7. Análise de Riscos de Funcionamento e Mitigações

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Média** | Template gerando URL errada/rejeitando URL válida | novo `TEMPLATES`/`montar_url` | Link inválido no README | **URL completa tem precedência** (`http(s)://` → usa como está); preview humano; teste |
| R2 | **Média** | Remover o **último** link viola "ao menos 1 link" | `validacao_service.py:163`; `editar_links` não valida no preview (`menu.py:349`) | Comunidade sem links gravada | Bloquear remoção quando `len(links)==1`; teste |
| R3 | **Média** | Novos estados quebrarem a ordem do fluxo (região protegida) | `state_manager.py` (`ORDEM_POR_ACAO[EDITAR]`) | Transições indevidas / fluxo travado | Estados como **desvios opcionais**; comentário `# ALTERADO`; teste de transição |
| R4 | **Média** | Callback global "roubando" updates (§8) | registro em `menu.py` | Fluxo quebra | `CallbackQueryHandler` **dentro** dos estados; teste de montagem |
| R5 | **Média** | Índice de link **obsoleto** (lista mudou entre render e clique) | callbacks por índice (`conversa.rascunho.links`) | Operação no link errado | Re-renderizar após cada operação; validar faixa; teste |
| R6 | **Média** | **Duplicidade** de tipo/URL ao adicionar | `montar_url`/catálogo | Dois links iguais/duplicados | Regra explícita (permitir tipos repetidos; avisar URL idêntica via validação); teste |
| R7 | Baixa | `ValueError` de `montar_url` derrubar o handler | `link_template.py` | Exceção no fluxo | Tratar e pedir valor válido/URL completa; teste |
| R8 | Baixa | Escape Markdown de URL com `_` nas mensagens | mensagens do menu | `Can't parse entities` | Usar `_md` (já existente); teste |
| R9 | Baixa | `parse_links` (colar vários) regredir | `menu.py:135` | Perda de fluxo existente | Manter o modo colar e testá-lo |
| R10 | Baixa | Testes tocando Telegram real | novos testes | Viola §7 | Fakes (`test_menu.py`) |
| R11 | Baixa | Deploy não efetivado | systemd | Recurso fora de produção | `systemctl restart` (§13) |
| R12 | **Média** | Campos novos (`link_indice`/`link_tipo`) não limpos no `reset()` | `ConversaUsuario.reset()` (`state_manager.py:120-131`) | Estado vaza entre fluxos (edição com link "fantasma") | Adicionar os campos ao `reset()`; teste |
| R13 | **Média** | Caminho "Nome e links" (`editar_novo_nome`) continuar mostrando o texto antigo em vez do menu | `menu.py:668-676` (`editar_novo_nome`) | UX inconsistente entre os dois caminhos | Rotear **ambos** os caminhos (`editar_escolha` e `editar_novo_nome`) para o menu; teste |
| R14 | **Média** | "Colar vários" (texto) **substituir** a lista e descartar remoções feitas no menu | `menu.py:690` (`links = ...`) | Remoções/edições perdidas ao colar | Definir semântica (recomendado **anexar** com dedupe) e testar |
| R15 | **Média** | Novos callbacks sem checagem de **autorização** | handlers novos em `menu.py` | Usuário não autorizado altera links | Aplicar `_autorizado(update)` (padrão dos handlers); teste |
| R16 | Baixa | `query.answer()` ausente nos novos callbacks | handlers novos | "giro" no botão do Telegram | `await query.answer()`; teste |
| R17 | Baixa | Template malformado p/ entradas com `/`, `@` ou `+` (YouTube/LinkedIn/WhatsApp) | `montar_url` (`link_template.py`) | URL incorreta | URL completa tem precedência (R1) + dica no prompt + preview; teste |
| R18 | Baixa | Índice inválido/estado perdido (restart) | `gerenciador` em memória (`state_manager.py:199`) | Operação em link errado/quebra | Validar faixa + mensagem "recomece com /editar"; teste |

### Requisitos de aceite

- **R1 — precedência da URL completa:** valor com `http(s)://` é usado como está; handle aplica o
  template. *Teste:* `montar_url("Instagram","user")` → `instagram.com/user`;
  `montar_url("Site","https://x.com")` → `https://x.com`.
- **R2 — bloqueio do último link:** remover quando resta 1 link é recusado com mensagem.
  *Teste:* remover o único link → mantém a lista e avisa.
- **R3 — estado coerente:** `EDITAR_ESCOLHA → EDITAR_LINKS → (LINK_VALOR|LINK_REMOCAO_CONFIRMACAO)
  → EDITAR_LINKS → PREVIEW`. *Teste:* `test_state_manager.py` + fluxo.
- **R4 — sem callback global:** novos padrões registrados **dentro** dos estados.
  *Teste:* `montar_conversation_handler()` não registra esses padrões globalmente.
- **R5 — índice validado:** índice fora de faixa não executa operação. *Teste:* clique com lista vazia.
- **R6 — duplicidade tratada:** adicionar tipo repetido é permitido; URL idêntica é sinalizada.
  *Teste:* cenário com URL duplicada.
- **R12 — reset limpa os campos:** após `reset()`, `link_indice`/`link_tipo` são `None`.
  *Teste:* iniciar, setar campos, encerrar, checar `None`.
- **R13 — um único caminho para o menu:** "Links" e "Nome e links" abrem o mesmo menu de links.
  *Teste:* `editar_novo_nome` com `campo_editar=ambos` → `EDITAR_LINKS` com menu.
- **R14 — colar vários não perde edições:** modo texto anexa (com dedupe) à lista do menu.
  *Teste:* remover um link no menu e colar outros → remoção preservada.
- **R15 — autorização:** novos callbacks recusam usuário não autorizado.
  *Teste:* `TELEGRAM_ALLOWED_USER_IDS` sem o usuário ⇒ mensagem de não autorizado.

### Risco residual aceito

- Tipos ambíguos (YouTube/LinkedIn/WhatsApp/Facebook) usam o template no caso comum; variantes exigem
  URL completa (documentado no prompt de valor).
- URLs existentes fora do padrão **não** são reescritas automaticamente (edição cirúrgica).

---

## Arquivos que serão alterados ou consultados

- **Alterados:**
  - `bot/services/link_template.py` — **novo** (TEMPLATES, `montar_url`, `precisa_url_completa`).
  - `bot/handlers/state_manager.py` — estados `LINK_VALOR`/`LINK_REMOCAO_CONFIRMACAO`; campos
    `link_indice`/`link_tipo` (defaults); comentário `# ALTERADO`.
  - `bot/handlers/menu.py` — menu de links, submenu, adicionar/remover/alterar, registro de callbacks.
  - `bot/tests/test_link_template.py` (novo), `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py`.
  - `docs/requisitos.md` (§2.4), `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
- **Consultados (sem alteração):** `bot/models/comunidade.py`, `bot/services/readme_service.py`,
  `bot/services/validacao_service.py`, `bot/handlers/commands.py`, `AGENTS.md`.

## Dependências e Edge Cases

- **Dependências:** nenhuma nova (PTB já presente); sem alteração em `requirements`.
- **Edge cases:**
  - E1 — Valor é URL completa → usada como está (R1).
  - E2 — Tipo sem template (Site, Google Drive, Slack, Discord) e valor não-URL → pedir URL completa.
  - E3 — Remover o último link → bloqueado (R2).
  - E4 — Lista vazia no menu → oferecer "Adicionar link" (e concluir bloqueado, se 0 links).
  - E5 — Índice fora de faixa → aviso "recomece/atualize" (R5).
  - E6 — Tipo repetido → permitido; URL idêntica → aviso (R6).
  - E7 — Colar vários (texto) continua funcionando (R9).
  - E8 — Mensagens com URL `_` → escape com `_md` (R8).
  - E9 — `allow_reentry`: novo `/editar` reseta a conversa.
  - E10 — Guarda de publicação pendente mantida na entrada de `/editar`.
  - E11 — `reset()` zera `link_indice`/`link_tipo` (R12).
  - E12 — Caminho "Nome e links" abre o menu de links (R13).
  - E13 — Colar vários **anexa** (com dedupe), preservando remoções (R14).
  - E14 — Callback não autorizado recusado (R15); `query.answer()` chamado (R16).

## Conformidade com AGENTS.md

- [ ] Backup: Seção 2 — **N/A** (sem escrita direta no README além da gravação já existente)
- [ ] Regiões protegidas: Seção 3.1 — `state_manager`/`menu.py` justificados + testes (§7)
- [ ] Handlers/callbacks: Seção 8 — callbacks dentro dos estados (R4)
- [ ] Testes herméticos: Seção 7 — `link_template` puro + fakes (R10)
- [ ] Validação: Seção 9 — `py_compile` + import + `pytest`
- [ ] Planejamento (aprovação): Seção 10 — **este documento**; implementar só após aprovação
- [ ] Checklist: Seção 11
- [ ] Git/commit: Seção 12 — `feat:`/`docs:`; tag sob autorização
- [ ] Deploy/systemd: Seção 13 — restart; instância única (R11)
- [ ] Documentação: Seções 15 e 16 — `CHANGELOG.md` + `prompts/nova-conversa.md`
- [ ] Análise de Riscos: R1–R6 e R12–R15 (médias) com teste de regressão — §7

---

## Decisões a aprovar (AGENTS.md §10)

1. **Menu de links por botões** (listar/submenu por link) substitui o "substituir tudo por texto",
   mantendo **colar vários** como opção.
2. **Alterar valor com template por tipo** (handle) e **URL completa com precedência** (R1).
3. **Remover link** com confirmação e **bloqueio do último** (R2).
4. **Novos estados** `LINK_VALOR` e `LINK_REMOCAO_CONFIRMACAO` + campos `link_indice`/`link_tipo`
   (região protegida) — desvios opcionais.
5. **Catálogo de tipos** para "Adicionar" = `ORDEM_BADGES` + "Outros".
6. **`/nova` fora de escopo** (mantém texto; reuso do gerenciador como evolução futura).
7. **Campos `link_indice`/`link_tipo` limpos no `reset()`** (R12) e **ambos os caminhos**
   (`Links` e `Nome e links`) abrem o **mesmo menu** (R13).
8. **"Colar vários" anexa com dedupe**, preservando remoções feitas no menu (R14); callbacks com
   `_autorizado` e `query.answer()` (R15/R16).

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
