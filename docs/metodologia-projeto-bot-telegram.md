# Metodologia — Criação de um Bot Telegram

> **Esta metodologia foi promovida a SKILL.** O conteúdo completo (fases 0–7, templates,
> políticas e o scaffold `bootstrap.py`) vive na skill **`criacao-bot-telegram`** — este
> documento é mantido apenas como **ponteiro**, para evitar duplicação (fonte única de verdade).

- **Skill:** `criacao-bot-telegram`
- **Fonte (repositório):** https://github.com/JosehRoberto/criacao-bot-telegram
- **Instalação neste computador:** `~/.config/opencode/skills/criacao-bot-telegram` (symlink)
- **Quando é acionada:** ao criar/começar/iniciar um bot no Telegram ("novo bot", "bootstrap de bot",
  "estrutura inicial de bot") ou ao gerar os arquivos iniciais (`AGENTS.md`, `CHANGELOG.md`) de um
  projeto de bot.
- **Conteúdo da skill:** `SKILL.md`, `references/` (requisitos, arquitetura, políticas, deploy),
  `assets/templates/`, `scripts/bootstrap.py`, `evals/`.

## Uso rápido

```bash
python3 ~/projetos/criacao-bot-telegram/scripts/bootstrap.py \
    --project-dir <destino> --name <nome> --data-dir <pasta-de-dados> \
    --remote <url-do-repo> --date DD/MM/AAAA
```

Histórico da criação e validação desta metodologia: ver `CHANGELOG.md` deste projeto.

> **Nota:** este documento não contém mais o passo a passo — consulte a skill.
