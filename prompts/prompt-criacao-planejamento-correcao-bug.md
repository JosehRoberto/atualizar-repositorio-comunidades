# Prompt: Criação de Planejamento de Correção de Bug

**Data:** 21/10/2026
**Versão:** 1.0
**Finalidade:** Padronizar a criação de **planejamentos de correção de bug/erro** para o bot
Atualização do Repositório de Comunidades, garantindo conformidade com o `AGENTS.md`.
Complementa o protocolo de diagnóstico (§14.1) e o prompt de planejamento de **feature**
(`prompt-criacao-planejamento-estrategico.md`).

---

## Quando usar

- **Depois** que o diagnóstico (§14.1) estiver concluído e **confirmado** pelo usuário
  (comportamento atual, comportamento esperado e ponto exato da divergência).
- Quando a correção for de **médio/alto risco** (§14.3) **ou** tocar alguma **região protegida**
  (§3.1).
- **Não** é necessário para correções triviais de **baixo risco** (§14.3): nesse caso, confirmar o
  diagnóstico e aplicar direto.

> Diferença em relação ao prompt genérico: o genérico é orientado a **feature** (viabilidade,
> fluxo de estados, impacto). Este é orientado a **bug** (diagnóstico §14.1 → causa raiz → correção
> mínima → regressão).

---

## Prompt Padrão para Criar Planejamentos de Correção de Bug

```
Salve este planejamento de correção de bug em um arquivo markdown na pasta docs/.
Ex.: docs/planejamento-correcao-<problema>.md

Neste planejamento siga rigorosamente as diretrizes do AGENTS.md:

### Diagnóstico (base do plano) — Seção 14.1
- Comportamento atual, com referência arquivo:linha
- Comportamento esperado
- Ponto exato da divergência
- Evidência (logs, trechos de código, reprodução, testes READ-ONLY)

### Causa raiz
- Explicação técnica com evidência no código/API/serviço externo (ex.: API do Telegram)
- Hipóteses investigadas e descartadas (e por quê)

### Correção proposta
- Mudança mínima; arquivos e funções afetadas
- Dependências e edge cases (Seção 10)
- Riscos: toca região protegida? (Seção 3.1)

### Natureza e critério — Seção 14.2
- É correção (comportamento muda) ou refatoração (comportamento preservado)?
- Se refatoração: critério único (legibilidade | performance | estabilidade)

### Backup, Rollback e Validação — Seções 2, 11 e 9
- Backup do README antes de qualquer escrita (timestamp único em America/Belem;
  confirmar com ls -lh backup/README_<TS>.bak)
- Rollback (cp backup/README_<TS>.bak repositorio/README.md)
- Validação: py_compile, importações e pytest bot/tests/ (suíte hermética)

### Testes herméticos — Seção 7
- Sem .env real, sem rede; isolar caminhos com tmp_path + monkeypatch;
  mockar requests, subprocess e a API do Telegram

### Atualização de Documentação e Encerramento — Seções 15 e 16
### Políticas de Git e Commits — Seções 11, 12 e 14.3

Formato recomendado:
```
## Arquivos que serão alterados ou consultados
- [lista]

## Dependências e Edge Cases
- [análise]

## Conformidade com AGENTS.md
- Backup: Seção 2
- Regiões protegidas: Seção 3.1
- Testes herméticos: Seção 7
- Validação: Seção 9
- Planejamento (aprovação antes de implementar): Seção 10
- Checklist: Seção 11
- Git/commit: Seção 12
- Deploy/systemd: Seção 13
- Diagnóstico/risco: Seções 14.1 e 14.3
- CHANGELOG: Seção 15
- Encerramento: Seção 16
```
```

---

## Seções Obrigatórias em Cada Planejamento de Correção

1. **Resumo Executivo** — problema, causa raiz e correção em 1 frase; escopo (o que é e o que
   **não** é incluído).
2. **Diagnóstico detalhado** (§14.1) — comportamento atual × esperado × divergência, com
   `arquivo:linha` e evidência.
3. **Causa raiz** — técnica, com evidência; hipóteses descartadas.
4. **Correção proposta** — mudança mínima, arquivos, dependências e edge cases.
5. **Riscos e natureza** (§3.1, §14.2, §14.3) — região protegida? correção × refatoração?
   baixo/médio/alto risco?
6. **Testes de regressão** (§7) — casos que devem continuar passando + o novo caso que cobre o bug.
7. **Rollback** — como reverter (§2).
8. **Referências** — arquivos e seções do `AGENTS.md`.
9. **Conformidade com AGENTS.md** — checklist.

---

## Checklist de Criação de Planejamento de Correção

```
[ ] 1. O arquivo está na pasta docs/
[ ] 2. O arquivo tem extensão .md
[ ] 3. O título é descritivo (ex: planejamento-correcao-<problema>.md)
[ ] 4. Inclui Diagnóstico (§14.1) e Causa raiz
[ ] 5. Inclui "Arquivos que serão alterados ou consultados" (§10)
[ ] 6. Inclui "Dependências e Edge Cases"
[ ] 7. Inclui "Conformidade com AGENTS.md"
[ ] 8. O formato de commit (§12.4) está documentado
[ ] 9. Não corrige sem confirmação do diagnóstico (§14.1)
[ ] 10. Backup do README previsto quando houver escrita (§2)
```

---

## Exemplo de Estrutura Completa

```markdown
# Planejamento de Correção: [Problema]

**Data:** [data]
**Versão:** 1.0
**Foco:** [área do projeto]

---

## 1. Resumo Executivo
[Problema, causa raiz, correção — em poucas linhas]

## 2. Diagnóstico (§14.1)
- Comportamento atual: [arquivo:linha]
- Comportamento esperado: [...]
- Divergência: [...]
- Evidência: [logs/testes read-only]

## 3. Causa raiz
[...] (+ hipóteses descartadas)

## 4. Correção proposta
[Arquivos, funções, edge cases]

## 5. Riscos e natureza (§3.1, §14.2, §14.3)
[Região protegida? Correção × refatoração? Nível de risco?]

## 6. Testes de regressão
[Casos]

## 7. Rollback
[Comandos]

## 8. Referências
[Arquivos e seções do AGENTS.md]

## 9. Conformidade com AGENTS.md
[Checklist]

## Arquivos que serão alterados ou consultados
- [Lista]

## Dependências e Edge Cases
[Análise]
```

> **Exemplo real deste projeto:** `docs/planejamento-correcao-markdown-escape.md`
> (correção do erro `Can't parse entities` por URL com `_` em `parse_mode="Markdown"`).

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
