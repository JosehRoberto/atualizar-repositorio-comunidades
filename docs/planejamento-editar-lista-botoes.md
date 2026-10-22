# Planejamento Estratégico: `/editar` híbrido com lista de comunidades em botões

**Data:** 21/10/2026
**Versão:** 1.1
**Foco:** `bot/handlers/menu.py` (+ 1 estado em `bot/handlers/state_manager.py`)
**Status:** **implementado, validado e em produção** (305 testes; deploy efetivado; tag `v0.6.0`
publicada).
**Revisão de risco incorporada** (R1–R16; `prompts/prompt-revisao-risco-planejamento.md`).

---

## 1. Resumo Executivo

- **Objetivo:** tornar `/editar` **híbrido** — manter a pergunta textual (nome) e oferecer um botão
  inline **"📋 Listar comunidades"** que exibe as comunidades como **botões**, permitindo escolher
  sem digitar; ao selecionar, segue para o fluxo de edição existente.
- **Problema que resolve:** digitar/lembrar nomes exatos é o ponto fraco hoje (o README tem **70
  comunidades** e o nome mais longo tem **57 caracteres**); o fuzzy só atua quando o texto não casa.
- **Abordagem escolhida:** **dois níveis** — **seções → comunidades** (espelha o README), com
  **paginação** no nível de comunidades para manter teclados pequenos.
- **Escopo incluído:**
  - Botão `edit_listar` na pergunta do `/editar` (mantém o modo texto — híbrido).
  - Nível 1: botões das **seções editáveis** (`edit_sec_<i>`).
  - Nível 2: botões das **comunidades da seção** (`edit_lst_<i>`, **reuso** do handler de candidatos),
    com paginação (`edit_lista_pg_<n>`) e "voltar às seções" (`edit_lista_voltar`).
  - Novo estado de desvio `EDITAR_LISTA` (análogo a `EDITAR_CANDIDATOS`).
  - Testes herméticos e documentação.
- **Escopo NÃO incluído:**
  - `/remover` e `/buscar` (mesma ideia pode ser estendida depois).
  - Busca por texto/filtro dentro da lista (v1 é navegação por seção).
  - Alterar parser/editor do README, backup, histórico, git, `create_application`, `config.py`.
  - Correção do bug latente do `/listar` (`menu.py:808`) — tema à parte.
- **Conclusão:** viável e de **risco médio**, pois **reaproveita** o mecanismo de candidatos já
  existente (teclados, índice, desempate por URL, `_oferecer_edicao`). O único ponto sensível é o
  **novo estado** em região protegida (§3.1) — mitigado por teste e comentário `# ALTERADO`.

---

## 2. Viabilidade Técnica

### O que já existe (funcionando) e será reaproveitado

- Seleção por botões: `EDITAR_CANDIDATOS` (`menu.py:867-868`), `teclado_candidatos` (`menu.py:202`),
  `_guardar_candidatos` (`menu.py:403`), `_candidato_escolhido` (`menu.py:417`, relê o README e
  desempata por URL), `editar_candidato` (`menu.py:479`) → `_oferecer_edicao` (`menu.py:435`).
- Listagem: `lista_secoes_editaveis` (`menu.py:156`), `doc.comunidades()`, `busca_service.rotulo_candidato`.
- Pergunta: `PERGUNTA_EDITAR_NOME` (`menu.py:71`), enviada em `cmd_editar` (`menu.py:399`).
- Estado de desvio: `EDITAR_CANDIDATOS` em `ORDEM_POR_ACAO[EDITAR]` (`state_manager.py:79`).

### O que muda (por módulo)

| Módulo | Mudança |
|---|---|
| `bot/handlers/state_manager.py` | **+estado `EDITAR_LISTA`** (região protegida §3.1) e entrada em `ORDEM_POR_ACAO[EDITAR]` |
| `bot/handlers/menu.py` | botão na pergunta; handlers `editar_listar`, `editar_lista_secao`, `editar_lista_pagina`, `editar_lista_voltar`; helpers de teclado/texto; registro dos callbacks no `ConversationHandler` |
| `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py` | novos casos (níveis, paginação, seleção, voltar) |
| `docs/requisitos.md` | §2.10 — nota do `/editar` por lista |
| `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md` | registro (§15/§16) |

### Onde o dado é usado

- Seções: `lista_secoes_editaveis(doc)` (índice → nome), sem persistência.
- Comunidades da seção: guardadas em **`conversa.candidatos`** (já existe), no mesmo formato
  `(nome, seção, url)`; a seção escolhida vai para **`conversa.secao_alvo`** (já existe).
- **Nenhum campo novo** em `ConversaUsuario`.

---

## 3. Fluxo Detalhado

### Fluxo do `/editar` (depois)

```
/editar → EDITAR_NOME
    "✏️ Qual comunidade você quer editar? (nome)"
    [📋 Listar comunidades]        ← botão novo (edit_listar); texto continua válido
        ├── digitar nome → editar_nome (exato/fuzzy) → _oferecer_edicao
        └── clicar botão → EDITAR_LISTA
              │  (edit_listar) → botões das SEÇÕES (edit_sec_<i>)
              ├── escolher seção (edit_sec_<i>) → carrega comunidades em conversa.candidatos
              │        → EDITAR_CANDIDATOS (reuso) com teclado paginado (edit_lst_<i>)
              │             ├── escolher comunidade (edit_lst_<i>) → _oferecer_edicao → EDITAR_ESCOLHA
              │             ├── ⬅️/➡️ (edit_lista_pg_<n>) → re-renderiza página
              │             └── ↩️ Seções (edit_lista_voltar) → volta aos botões de seção
              └── (sem seções editáveis) → mensagem informativa
```

> **Observação:** o nível 2 **reusa** `EDITAR_CANDIDATOS` + `editar_candidato` + `_oferecer_edicao`
> (`menu.py:479/435`). Só o **nível 1** (seções/paginação/voltar) usa o estado novo `EDITAR_LISTA`.

### Estados e máquina de estados

- **Novo estado:** `EstadoConversa.EDITAR_LISTA = "editar_lista"` (região protegida), adicionado a
  `ORDEM_POR_ACAO[Acao.EDITAR]` como **desvio opcional** (analogia a `EDITAR_CANDIDATOS`).
- `proximo_estado` não é usado no nível 1: os handlers **atribuem o próximo estado diretamente**
  (como já faz `editar_candidato`).
- Transições: `EDITAR_NOME →(edit_listar) EDITAR_LISTA →(edit_sec) EDITAR_CANDIDATOS →(edit_cand) EDITAR_ESCOLHA → …`.

### Callbacks (padrões)

| callback_data | Uso | Existe? |
|---|---|---|
| `edit_listar` | abrir lista de seções | novo |
| `edit_sec_<i>` | escolher seção (índice) | novo |
| `edit_lst_<i>` | escolher comunidade da **lista** (índice **absoluto**) | novo (reusa o handler `editar_candidato`) |
| `edit_lista_pg_<n>` | paginação do nível 2 | novo |
| `edit_lista_voltar` | voltar às seções | novo |

> **Callback data ≤ 64 bytes (limite do Telegram):** usar **índice**, nunca o nome
> (ex.: `edit_sec_12`, `edit_lista_pg_1`). O índice do candidato é **absoluto** na lista da seção.
>
> **Obrigatório nos handlers novos:** aplicar `_autorizado(update)` (R15), `await query.answer()`
> (R16) e tratar índice fora de faixa com "recomece com /editar" (R14).

### Pontos de alteração (arquivo:linha)

- `menu.py:71` — `PERGUNTA_EDITAR_NOME` (mantém texto).
- `menu.py:398-400` — `cmd_editar`: enviar a pergunta com `reply_markup` (botão `edit_listar`).
- `menu.py:202-216` — novos helpers de teclado/texto (seções e páginas), reusando o estilo atual.
- `menu.py:862-881` — registro dos novos `CallbackQueryHandler` nos estados `EDITAR_NOME` e
  `EDITAR_LISTA` (e paginação/voltar em `EDITAR_CANDIDATOS`).
- `state_manager.py:40-49, 77-85` — `EDITAR_LISTA` (enum + ordem), comentário `# ALTERADO [data]`.

### Estrutura proposta (esboço)

```python
LIMITE_LISTA = 8  # itens por página no nível de comunidades

def teclado_secoes(secoes: list[str]) -> InlineKeyboardMarkup:
    botoes = [[InlineKeyboardButton(s, callback_data=f"edit_sec_{i}")]
              for i, s in enumerate(secoes)]
    return InlineKeyboardMarkup(botoes)

def teclado_lista(rotulos: list[str], pagina: int) -> InlineKeyboardMarkup:
    inicio = pagina * LIMITE_LISTA
    fatia = rotulos[inicio:inicio + LIMITE_LISTA]
    linhas = [[InlineKeyboardButton(f"{inicio + i + 1}. {r}", callback_data=f"edit_lst_{inicio + i}")]
              for i, r in enumerate(fatia)]
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"edit_lista_pg_{pagina - 1}"))
    if inicio + LIMITE_LISTA < len(rotulos):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"edit_lista_pg_{pagina + 1}"))
    nav.append(InlineKeyboardButton("↩️ Seções", callback_data="edit_lista_voltar"))
    linhas.append(nav)
    return InlineKeyboardMarkup(linhas)
```

---

## 4. Próximos Passos

- **Não necessárias:** novo serviço; mexer em parser/editor/backup/histórico/git.
- **Obrigatórias (após aprovação):**
  1. `state_manager`: `EDITAR_LISTA` + `ORDEM_POR_ACAO[EDITAR]`.
  2. `menu.py`: botão na pergunta; handlers e helpers; registro de callbacks.
  3. Testes herméticos (R1–R6): teclados, paginação, seleção, voltar, homônimos, estado.
  4. `docs/requisitos.md §2.10`, `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
  5. Validação (`py_compile`, import, `pytest`), deploy (`systemctl restart`) e commit/tag (§12).

---

## 5. Referências

- **Arquivos:** `bot/handlers/menu.py` (candidatos, listar, cmd_editar), `bot/handlers/state_manager.py`,
  `bot/services/busca_service.py` (`rotulo_candidato`, `nomes_duplicados`), `bot/services/readme_service.py`,
  `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py`, `docs/requisitos.md` §2.10,
  `prompts/nova-conversa.md`.
- **AGENTS.md:** §3.1 (protegidas), §4 (ordem/alfabética), §7 (testes), §8 (handlers/callbacks),
  §9 (validação), §10 (aprovação), §11 (checklist), §12 (Git), §13 (deploy), §15/§16 (docs).
- **Prompts:** `prompts/prompt-criacao-planejamento-estrategico.md`,
  `prompts/prompt-revisao-risco-planejamento.md`.

---

## 6. Conformidade com AGENTS.md

- [ ] **Backup (Seção 2):** **N/A** — não escreve no README.
- [ ] **Regiões protegidas (Seção 3.1):** `state_manager` (novo estado) + `menu.py` → justificativa +
  teste + comentário `# ALTERADO [data]` (§7).
- [ ] **Handlers/Callbacks (Seção 8):** `CallbackQueryHandler` **dentro** dos estados; **nunca** global.
- [ ] **Testes herméticos (Seção 7):** sem `.env`/rede; helpers puros + Telegram mockado.
- [ ] **Validação (Seção 9):** `py_compile` + import + `pytest bot/tests/ -v`.
- [ ] **Planejamento/aprovação (Seção 10):** este documento; implementar **só após aprovação**.
- [ ] **Checklist (Seção 11).**
- [ ] **Git/commit (Seção 12):** `feat:`/`docs:`; tag sob autorização.
- [ ] **Deploy (Seção 13):** restart; instância única.
- [ ] **Documentação (Seções 15/16):** `CHANGELOG.md` + `prompts/nova-conversa.md`.
- [ ] **Riscos:** R1–R6 (média) e R14–R15 (média) → requisitos de aceite com teste (§7).

---

## 7. Análise de Riscos de Funcionamento e Mitigações

| ID | Gravidade | Risco | Causa (arquivo:linha) | Efeito observável | Mitigação |
|---|---|---|---|---|---|
| R1 | **Média** | `callback_data` exceder **64 bytes** se carregar o nome | `teclado_candidatos` (`menu.py:202`) | Telegram rejeita (`BadRequest`) e o botão não funciona | Usar **índice** (`edit_sec_<i>`, `edit_lst_<i>`); teste de comprimento |
| R2 | **Média** | Paginação com índice **absoluto** errado (off-by-one) | novo `teclado_lista`/`editar_lista_pagina` | Página errada ou candidato trocado | Índice absoluto + teste de fatias/limites (0, meio, última) |
| R3 | **Média** | Novo estado na região protegida quebra a ordem dos fluxos | `state_manager.py:77-85` | Transições indevidas / fluxo travado | Estado como **desvio opcional** (como `EDITAR_CANDIDATOS`); comentário `# ALTERADO`; teste de transição |
| R4 | **Média** | Registrar callback **global** para os botões (§8) | `menu.py` (registro) | Rouba updates do `ConversationHandler` (fluxo quebra) | Registrar `CallbackQueryHandler` **dentro** dos estados; teste de montagem |
| R5 | **Média** | Lista **obsoleta** (README mudou entre listar e clicar) | `_candidato_escolhido` (`menu.py:417`) | Índice aponta para outra comunidade | Reler o README na seleção + desempate por URL; `conferir_hash` na aprovação (já existente) |
| R6 | **Média** | Callbacks de **teclados antigos** (troca de nível) | mensagens anteriores | Ação inesperada / "mensagem não modificada" | Editar a mensagem ao trocar de nível (aposentar teclado); padrões específicos; teste |
| R7 | Baixa | Seção sem comunidades (vazia) | `editar_lista_secao` | Teclado sem opções | Mensagem informativa + botão "↩️ Seções"; teste |
| R8 | Baixa | Nomes homônimos na lista | `busca_service.rotulo_candidato` | Seleção ambígua | Rótulo com primeiro link (já existente); teste |
| R9 | Baixa | Muitos botões numa página | `LIMITE_LISTA` | Teclado alto/ruim | Limite de página (8) + navegação; teste |
| R10 | Baixa | Guarda de publicação pendente regredir o `/editar` | `cmd_editar` (`menu.py:394`) | Bloqueio indevido | Não alterar a guarda; teste de entrada |
| R11 | Baixa | Testes tocando Telegram real | novos testes | Viola §7 | Helpers puros + fakes (`test_menu.py`) |
| R12 | Baixa | Deploy não efetivado | systemd | Recurso não entra em produção | `systemctl restart` (§13) |
| R13 | Baixa | Ambiguidade de teclado obsoleto (clique antigo resolve contra a lista atual) | prefixos de callback (`menu.py:59`) | Seleção inesperada, porém válida | Revalidação por `(nome, seção, url)` (R5) + editar a mensagem ao trocar de nível (R6); **prefixo `edit_lst_<i>` adotado** (separa a origem lista × fuzzy) |
| R14 | **Média** | Estado em **memória** perdido em restart do serviço (botões antigos) | `gerenciador` em memória (`state_manager.py:199`) | `conversa.candidatos` vazio ⇒ índice inválido ao clicar | Tratar índice inválido com mensagem "recomece com /editar"; teste do índice fora de faixa |
| R15 | **Média** | Novos callbacks sem checagem de **autorização** | handlers novos em `menu.py` | Usuário não autorizado navega/edita | Aplicar `_autorizado(update)` (como `editar_candidato`, `menu.py:483`); teste |
| R16 | Baixa | `query.answer()` ausente nos novos callbacks | handlers novos | "giro" infinito no botão do Telegram | Chamar `await query.answer()` (como o fluxo atual); teste |

### Requisitos de aceite

- **R1 — callbacks curtos:** todo `callback_data` da lista ≤ 64 bytes e baseado em índice.
  *Teste:* maior `callback_data` gerado < 64.
- **R2 — paginação correta:** fatia e índice absoluto corretos em 1ª/meio/última página.
  *Teste:* `teclado_lista` com 19 itens, páginas 0/1/2.
- **R3 — estado coerente:** `EDITAR_LISTA` é desvio opcional; `EDITAR_NOME → EDITAR_LISTA →
  EDITAR_CANDIDATOS → EDITAR_ESCOLHA`. *Teste:* em `test_state_manager.py` e no fluxo de `menu.py`.
- **R4 — sem callback global:** os novos `CallbackQueryHandler` estão **dentro** dos estados.
  *Teste:* `montar_conversation_handler()` não registra esses padrões globalmente.
- **R5 — seleção validada:** escolher e resolver a comunidade relê o README e desempata por URL.
  *Teste:* com homônimos, a seleção correta é resolvida.
- **R6 — teclados aposentados:** ao trocar de nível, a mensagem anterior é editada sem botões clicáveis
  conflitantes. *Teste:* transição seções→comunidades→voltar não deixa teclado ambíguo.
- **R13 — prefixo/teclado obsoleto:** clique em teclado antigo não seleciona comunidade inesperada.
  *Teste:* seleção com `candidatos` de outra lista revalida por `(nome, seção, url)`.
- **R14 — estado perdido:** índice fora de faixa (após restart) → mensagem "recomece com /editar".
  *Teste:* `conversa.candidatos` vazio + `edit_lst_0` não quebra.
- **R15 — autorização:** novos callbacks recusam usuário não autorizado.
  *Teste:* `TELEGRAM_ALLOWED_USER_IDS` sem o usuário ⇒ mensagem de não autorizado.
- **R16 — `answer()`:** novos callbacks chamam `query.answer()`. *Teste:* `FakeQuery.answerado`.

### Risco residual aceito

- Sem busca textual/filtro dentro da lista (navegação por seção apenas) — evolução futura.
- Índice capturado pode ficar levemente defasado em edições concorrentes; mitigado por revalidação e
  hash (R5).

---

## Arquivos que serão alterados ou consultados

- **Alterados:**
  - `bot/handlers/state_manager.py` — estado `EDITAR_LISTA` (+ ordem), comentário `# ALTERADO`.
  - `bot/handlers/menu.py` — botão na pergunta; handlers `editar_listar`/`editar_lista_secao`/
    `editar_lista_pagina`/`editar_lista_voltar`; helpers de teclado/texto; registro de callbacks.
  - `bot/tests/test_menu.py`, `bot/tests/test_state_manager.py` — casos R1–R6.
  - `docs/requisitos.md` (§2.10), `README.md`, `CHANGELOG.md`, `prompts/nova-conversa.md`.
- **Consultados (sem alteração):** `bot/services/busca_service.py`, `bot/services/readme_service.py`,
  `bot/handlers/commands.py`, `bot/main.py`, `AGENTS.md`.

## Dependências e Edge Cases

- **Dependências:** nenhuma nova (PTB já presente); sem alteração em `requirements`.
- **Edge cases:**
  - E1 — Callback data ≤ 64 bytes → índice (R1).
  - E2 — Paginação: 1 página, múltiplas páginas, última parcial (R2).
  - E3 — Seção sem comunidades → mensagem + voltar (R7).
  - E4 — Homônimos → rótulo com URL + desempate na seleção (R5/R8).
  - E5 — README alterado entre listar e selecionar → revalidação por `(nome, seção, url)` (R5).
  - E6 — Teclado antigo clicado → sem efeito/erro; mensagem editada ao trocar de nível (R6).
  - E7 — "↩️ Voltar" no nível 1/2 → reconstrói a lista a partir do README atual.
  - E8 — Modo texto continua funcionando (híbrido) — `editar_nome` permanece como handler.
  - E9 — `allow_reentry`: novo `/editar` reseta a conversa (comportamento atual).
  - E10 — Guarda de publicação pendente mantida na entrada (R10).
  - E11 — Clique em teclado obsoleto → revalidação por `(nome, seção, url)` (R13/R5).
  - E12 — Restart do serviço com botões abertos → índice fora de faixa tratado (R14).
  - E13 — Callback de usuário não autorizado → recusa (R15).
  - E14 — `query.answer()` em todo callback (R16).

## Conformidade com AGENTS.md

- [ ] Backup: Seção 2 — **N/A** (sem escrita no README)
- [ ] Regiões protegidas: Seção 3.1 — `state_manager`/`menu.py` justificados + testes (§7)
- [ ] Handlers/callbacks: Seção 8 — callbacks dentro dos estados (R4)
- [ ] Testes herméticos: Seção 7 — helpers puros + Telegram mockado (R11)
- [ ] Validação: Seção 9 — `py_compile` + import + `pytest`
- [ ] Planejamento (aprovação): Seção 10 — **este documento**; implementar só após aprovação
- [ ] Checklist: Seção 11
- [ ] Git/commit: Seção 12 — `feat:`/`docs:`; tag sob autorização
- [ ] Deploy/systemd: Seção 13 — restart; instância única (R12)
- [ ] Documentação: Seções 15 e 16 — `CHANGELOG.md` + `prompts/nova-conversa.md`
- [ ] Análise de Riscos: R1–R6 e R14–R15 (médias) com teste de regressão — §7

---

## Decisões a aprovar (AGENTS.md §10)

1. **Abordagem de dois níveis** (seções → comunidades), com **paginação** (`LIMITE_LISTA = 8`).
2. **Novo estado `EDITAR_LISTA`** em `state_manager.py` (região protegida), como desvio opcional.
3. **Reuso do handler `editar_candidato`** com **prefixo distinto `edit_lst_<i>`** para a seleção vinda da lista (separa a origem lista × fuzzy; R13).
4. **Híbrido:** mantém o texto (digitar nome) **e** adiciona o botão "📋 Listar comunidades".
5. **`/remover` fora de escopo** nesta entrega (extensão futura com o mesmo padrão).
6. **Sem busca/filtro textual** dentro da lista na v1 (navegação por seção).

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
