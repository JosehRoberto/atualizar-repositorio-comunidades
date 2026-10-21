# Prompt: Revisão de Risco de Planejamento

**Data:** 21/10/2026
**Versão:** 1.0
**Finalidade:** Padronizar a **revisão de risco** de um planejamento (de correção de bug ou
estratégico) do bot Atualização do Repositório de Comunidades, produzindo os requisitos de aceite
`R1…Rn` e o checklist de conformidade com o `AGENTS.md`.
**Quando usar:** após o planejamento estar redigido (ou a cada alteração relevante), antes de
implementar. Para planos que alteram código em execução, é **obrigatória**.

---

## Prompt Padrão

```
Atue como revisor de risco do bot Atualização do Repositório de Comunidades
(@atualizar_repositorio_bot; repo alvo GitLab paralivre/comunidades-de-tecnologia-pa;
clone local em repositorio/; deploy via systemd, instância única).

1) Produza um resumo objetivo do planejamento estratégico atualizado: objetivo, fluxo (estados/ConversationHandler),
   arquivos afetados, decisões e o que NÃO muda.
2) Avalie se a execução pode causar problema de funcionamento em produção, cobrindo
   OBRIGATORIAMENTE as dimensões:
   - Concorrência e idempotência (escrita_service: asyncio.Lock, sincronizar_seguro,
     conferir_hash; disputa entre /publicar, aprovação de preview e /restaurar)
   - Loops e retries (polling/getUpdates do Telegram; retries de transporte; nenhuma
     falha que se repita sem fim)
   - ConversationHandler/handlers (ordem de registro em create_application(); entry points;
     callbacks; NUNCA CallbackQueryHandler global para callbacks do fluxo)
   - Regiões protegidas (§3.1) e ordem de registro em create_application(): parser/editor do
     README, normalização do marcador, backup, histórico, git/GitLab, create_application,
     state_manager, config.py
   - Persistência e histórico (bot/history/historico.jsonl append-only; backward compatibility)
   - Integridade do README (edição cirúrgica; ordem alfabética por nome_normalizado; schema das
     tabelas; Observatório não editável; marcador :triangular_flag_on_post: em no máximo 1
     comunidade)
   - Datas e timezone (America/Belem via tempo.timestamp_belem)
   - Limites externos (API do Telegram; API v4 do GitLab; rate limit/quota)
   - Git/GitLab e segredos (GITLAB_TOKEN fora do remote e do .git/config; sem reset --hard em
     main publicada; commit/branch/push/MR só com confirmação explícita no Telegram; nenhum
     segredo logado ou commitado)
   - Deploy/systemd (instância única; evitar 409 Conflict no getUpdates; restart via systemd)
   - Isolamento de testes (sem .env real, sem rede; tmp_path + monkeypatch; mockar requests,
     subprocess e a API do Telegram)
   - Backup e rollback (backup do README antes de toda escrita; rollback documentado)
3) Para cada risco, informe: gravidade (alta/média/baixa), causa no código atual
   (arquivo:linha), efeito observável e mitigação.
4) Converta todo risco de gravidade alta/média em requisito explícito de aceite (R1, R2, …),
   com teste de regressão.
5) Se eu autorizar, incorpore os requisitos ao planejamento em docs/ e atualize o checklist
   de conformidade (Conformidade com AGENTS.md).
```

---

## Dimensões Avaliadas (checklist rápida)

| # | Dimensão | Pergunta-chave |
|---|---|---|
| 1 | Concorrência/idempotência | Duas operações podem gravar/publicar o mesmo README ao mesmo tempo? |
| 2 | Loops e retries | Alguma falha re-executa sem fim (polling, retry de transporte)? |
| 3 | ConversationHandler/handlers | Novo handler intercepta/rouba update do fluxo existente? |
| 4 | Regiões protegidas | Alterou parser/editor do README, marcador, backup, histórico, git, `create_application`, `state_manager` ou `config.py`? |
| 5 | Persistência/histórico | `historico.jsonl` append-only válido? Backward-compatible? |
| 6 | Integridade do README | A edição é cirúrgica? Ordem alfabética e schema mantidos? Observatório intacto? |
| 7 | Marcador `:triangular_flag_on_post:` | Continua no máximo 1 comunidade marcada? |
| 8 | Datas/timezone | Usa `America/Belem` (`tempo.timestamp_belem`)? |
| 9 | Limites externos | Rate limit/quota da API do Telegram e da API v4 do GitLab tratados? |
| 10 | Git/GitLab e segredos | Token fora do remote? Sem `reset --hard`? Confirmação explícita no Telegram? Nenhum segredo exposto? |
| 11 | Deploy/systemd | Instância única (sem `409 Conflict`)? Restart via systemd (§13)? |
| 12 | Isolamento de testes | Testes herméticos (sem `.env`, rede, `requests`/`subprocess`/Telegram mockados)? |
| 13 | Backup/rollback | Backup antes de toda escrita no README? Rollback documentado? |

---

## Saída esperada

Para cada risco:

```
[gravidade] <descrição> — causa: <arquivo:linha> — efeito: <observável> — mitigação: <ação>
```

Todo risco de gravidade **alta/média** vira **REQUISITO DE ACEITE** (`R1`, `R2`, …) com **teste de
regressão**; os requisitos são incorporados ao planejamento em `docs/` **somente após autorização**
(§10, §12.1), atualizando o bloco "Conformidade com AGENTS.md". Registrar também o **risco residual**
aceito (o que fica deliberadamente sem mitigação).

---

*Projeto: Atualização do Repositório de Comunidades | Mantenedor: José Roberto*
