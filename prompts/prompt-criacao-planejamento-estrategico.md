# Prompt: Criação de Planejamento Estratégico

**Data:** 21/10/2026
**Versão:** 1.0
**Finalidade:** Padronizar a criação de planejamentos estratégicos para o bot Atualização do
Repositório de Comunidades, garantindo conformidade com as diretrizes do `AGENTS.md` e a
**análise obrigatória de riscos de funcionamento**.
**Fluxo em duas fases:** (1) criação do planejamento (seções 1–7); (2) revisão de risco completa →
requisitos `R1…Rn` (§ *Prompt de Revisão de Risco*).

---

## Quando usar

- Ao planejar uma **feature/atualização** (novo fluxo, novo comando, evolução de serviço), em
  contraste com o planejamento de **correção de bug**
  (`prompt-criacao-planejamento-correcao-bug.md`).
- Quando o plano alterar **código em execução** (`bot/handlers/`, `bot/services/`, `bot/models/`,
  `bot/schemas/`, `bot/config.py`) — a Análise de Riscos (§7) é obrigatória nesse caso.
- **Antes** de implementar: o plano deve ser apresentado e **aprovado explicitamente** (§10).

---

## Prompt Padrão para Criar Planejamentos Estratégicos

```
Salve este planejamento estratégico em um arquivo markdown na pasta docs/.
Ex.: docs/planejamento-<feature>.md

Neste planejamento siga rigorosamente as diretrizes do AGENTS.md:

### Escopo e regras de negócio
- docs/requisitos.md é a fonte canônica do escopo (seções do README, badges, marcador
  :triangular_flag_on_post:, Observatório não editável)
- Regras de negócio do README: Seção 4

### Backup, Rollback e Validação
- Seção 2 (Política de Backup) — obrigatória antes de qualquer escrita no README
- Seção 9 (Validação Após Alterações) — py_compile, importações e pytest bot/tests/

### Testes herméticos e isolamento
- Seção 7 — sem .env real, sem rede; tmp_path + monkeypatch; mockar requests, subprocess
  e a API do Telegram

### Handlers e ConversationHandler
- Seção 8 — ordem de registro em create_application(); nunca CallbackQueryHandler global
  para callbacks do fluxo

### Segredos e autenticação
- Seção 5 — GITLAB_TOKEN fora do remote/`git config`; nunca logar/commitar .env

### Atualização de Documentação e Encerramento
- Seção 15 (CHANGELOG, conforme skill changelog-convention) e Seção 16 (resumo da sessão)

### Políticas de Git e Commits
- Seção 11 (Checklist de Alteração) — pré e pós alteração
- Seção 12 (Política de Git; §12.4 mensagem de commit; §12.6 tags; §12.8 operações no repo alvo
  exigem confirmação explícita no Telegram)

### Deploy
- Seção 13 — systemd (instância única; o commit não faz deploy)

### Estrutura Obrigatória do Planejamento
- Seção 10: Lista explícita de "Arquivos que serão alterados ou consultados"
- "Dependências e edge cases"
- "Análise de Riscos de Funcionamento e Mitigações" — obrigatória quando o plano alterar
  código em execução

Formato recomendado:
```
## Arquivos que serão alterados ou consultados
- [lista]

## Dependências e Edge Cases
- [análise]

## Análise de Riscos de Funcionamento e Mitigações
- [risco → gravidade → causa (arquivo:linha) → efeito → mitigação (R1, R2, …) → teste]

## Conformidade com AGENTS.md
- Backup: Seção 2
- Testes herméticos: Seção 7
- Handlers: Seção 8
- Validação: Seção 9
- Planejamento (aprovação): Seção 10
- Checklist: Seção 11
- Git/commit: Seção 12
- Deploy: Seção 13
- Documentação: Seções 15 e 16
```
```

---

## Seções Obrigatórias em Cada Planejamento

### 1. Resumo Executivo
- Objetivo do planejamento
- Escopo (o que é incluído e o que **não** é)
- Conclusão principal

### 2. Viabilidade Técnica
- O que já existe (funcionando)
- O que não é necessário (já existente)
- Onde o dado é coletado e usado
- Impacto em cada serviço/módulo do bot

### 3. Fluxo Detalhado
- Estados envolvidos (`bot/handlers/state_manager.py`: `EstadoConversa`, `Acao`, `ORDEM_POR_ACAO`)
- Sequência de perguntas/respostas e callbacks
- Integração com os estados existentes (nova/editar/remover/buscar/publicar/restaurar)
- Impacto técnico em cada arquivo

### 4. Próximos Passos
- Ações não necessárias (já implementadas)
- Ações obrigatórias (documentação, backup, testes, deploy)

### 5. Referências
- Arquivos do projeto relacionados (`docs/requisitos.md`, `prompts/nova-conversa.md`)
- Seções do `AGENTS.md` aplicáveis
- Documentação complementar

### 6. Conformidade com AGENTS.md (seção obrigatória)
- Backup e rollback: Seção 2
- Testes herméticos: Seção 7
- Handlers/ConversationHandler: Seção 8
- Validação pós-alteração: Seção 9
- Planejamento e aprovação: Seção 10
- Checklist de alteração: Seção 11
- Git: Seção 12
- Deploy: Seção 13
- Documentação/CHANGELOG: Seções 15 e 16

### 7. Análise de Riscos de Funcionamento e Mitigações (obrigatória quando o plano alterar código em execução)
- Inventário de riscos pelas dimensões do *Prompt de Revisão de Risco* (abaixo)
- Para cada risco: **gravidade** (alta/média/baixa), **causa no código atual** (`arquivo:linha`),
  **efeito observável**, **mitigação** e **teste de regressão**
- Todo risco de gravidade **alta/média** vira **REQUISITO DE ACEITE** (`R1`, `R2`, …)
- Referenciar os *edge cases* por ID; **não** repetir a tabela de edge cases
- Registrar o **risco residual** aceito (o que fica deliberadamente sem mitigação)

---

## Checklist de Criação de Planejamento

Antes de salvar o planejamento, verificar:

```
[ ] 1. O arquivo está na pasta docs/
[ ] 2. O arquivo tem extensão .md
[ ] 3. O título do arquivo é descritivo (ex: planejamento-<feature>.md)
[ ] 4. O planejamento inclui a seção "Arquivos que serão alterados ou consultados" (§10)
[ ] 5. O planejamento inclui a seção "Dependências e Edge Cases"
[ ] 6. O planejamento inclui a seção "Conformidade com AGENTS.md"
[ ] 7. Todas as referências do AGENTS.md estão corretas
[ ] 8. O formato de commit (§12.4) está documentado
[ ] 9. (Se altera código em execução) O plano inclui a "Análise de Riscos de Funcionamento e
        Mitigações" com requisitos R1…Rn, causa (arquivo:linha) e teste de regressão?
[ ] 10. Backup do README previsto quando houver escrita (§2)
```

---

## Exemplo de Estrutura Completa

```markdown
# Planejamento Estratégico: [Título]

**Data:** [data]
**Versão:** 1.0
**Foco:** [área do projeto]

---

## 1. Resumo Executivo
[Resumo]

## 2. Viabilidade Técnica
[Análise]

## 3. Fluxo Detalhado
[Fluxo]

## 4. Próximos Passos
[Ações]

## 5. Referências
[Arquivos e seções]

## 6. Conformidade com AGENTS.md
[Checklist]

## 7. Análise de Riscos de Funcionamento e Mitigações
[Riscos → gravidade → causa (arquivo:linha) → efeito → mitigação (R1, R2, …) → teste]

## Arquivos que serão alterados ou consultados
- [Lista]

## Dependências e Edge Cases
[Análise]
```

---

## Prompt de Revisão de Risco (Fase 2)

> **Uso:** após o planejamento estar redigido (ou a cada alteração relevante). Produz a Seção 7 e
> os requisitos `R1…Rn`. Para planos que alteram código em execução, esta fase é **obrigatória**.

```
Atue como revisor de risco do bot Atualização do Repositório de Comunidades.

1) Produza um resumo objetivo do planejamento: objetivo, fluxo, arquivos, decisões e o que
   NÃO muda.
2) Avalie se a execução pode causar problema de funcionamento em produção, cobrindo
   OBRIGATORIAMENTE as dimensões:
   - Concorrência e idempotência (escrita_service: asyncio.Lock, sincronizar_seguro, conferir_hash)
   - ConversationHandler/handlers (ordem em create_application; entry points; callbacks;
     nenhum CallbackQueryHandler global)
   - Regiões protegidas (§3.1): parser/editor do README, normalização do marcador, backup,
     histórico, git/GitLab, create_application, state_manager, config.py
   - Integridade do README (edição cirúrgica; ordem alfabética; schema das tabelas; Observatório)
   - Marcador :triangular_flag_on_post: (no máximo 1 comunidade)
   - Persistência e histórico (JSONL append-only; backward compatibility)
   - Datas e timezone (America/Belem via tempo.timestamp_belem)
   - Git/GitLab e segredos (token fora do remote; sem reset --hard; confirmação explícita no
     Telegram; nada de token logado/commitado)
   - Deploy/systemd (instância única; 409 Conflict; restart via systemd)
   - Isolamento de testes (sem .env, sem rede, requests/subprocess/Telegram mockados)
   - Backup e rollback (backup antes de toda escrita; rollback documentado)
3) Para cada risco, informe: gravidade (alta/média/baixa), causa no código atual
   (arquivo:linha), efeito observável e mitigação.
4) Converta todo risco de gravidade alta/média em REQUISITO DE ACEITE (R1, R2, …) com teste
   de regressão.
5) Incorpore os requisitos ao planejamento em docs/ e atualize o checklist de conformidade
   (Seção 6).
```

**Dimensões avaliadas (checklist rápida):**

| # | Dimensão | Pergunta-chave |
|---|---|---|
| 1 | Concorrência/idempotência | Duas operações podem gravar/publicar o mesmo README ao mesmo tempo? |
| 2 | ConversationHandler/handlers | Novo handler intercepta/rouba update do fluxo existente? |
| 3 | Regiões protegidas | Alterou parser/editor do README, marcador, backup, histórico, git, `create_application`, `state_manager` ou `config.py`? |
| 4 | Integridade do README | A edição é cirúrgica? `comparar_estrutura` preservado? Ordem alfabética e schema mantidos? |
| 5 | Marcador `:triangular_flag_on_post:` | Continua no máximo 1 comunidade marcada? |
| 6 | Persistência/histórico | JSONL append-only válido? Backward-compatible? |
| 7 | Datas/timezone | Usa `America/Belem` (`tempo.timestamp_belem`)? |
| 8 | Git/GitLab e segredos | Token fora do remote? Sem `reset --hard`? Confirmação explícita no Telegram? Nenhum segredo exposto? |
| 9 | Deploy/systemd | Instância única (sem `409 Conflict`)? Restart via systemd (§13)? |
| 10 | Isolamento de testes | Testes herméticos (sem `.env`, rede, `requests`/`subprocess` mockados)? |
| 11 | Backup/rollback | Backup antes de toda escrita no README? Rollback documentado? |

---

*Este prompt deve ser usado em todas as novas sessões de planejamento estratégico para garantir
conformidade com as diretrizes do `AGENTS.md`.*

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
