# Requisitos — Atualização do Repositório de Comunidades

Documento de requisitos e decisões do projeto **Atualização do Repositório de Comunidades**.
Consolida o `docs/prompt-inicial.md` e as respostas de definição de escopo.

- Repositório do projeto (código do bot e docs): https://github.com/JosehRoberto/atualizar-repositorio-comunidades
- Repositório alvo (dados): https://gitlab.com/paralivre/comunidades-de-tecnologia-pa
- Projeto de referência (arquitetura/padrões): `/home/roberto/projetos/agendatipara-bot`

---

## 1. Visão geral

Bot Telegram que cadastra, edita, lista, busca e remove comunidades de tecnologia no `README.md`
do repositório alvo, sem edição manual do arquivo. O bot opera sobre um clone local do repositório
alvo, preservando integralmente a estrutura e a formatação Markdown existentes, com backup,
preview, aprovação explícita e publicação controlada (commit / branch / push / Merge Request).

---

## 2. Decisões confirmadas

### 2.1 Escopo do cadastro (item 1)
- Cada comunidade é cadastrada com **apenas `nome` + `links`**, espelhando o schema real do README
  (`| Comunidade | Links |`).
- **Não** são cadastrados cidade, descrição ou tecnologias (não existem colunas para isso no README).
- `links` é uma lista de pares `{tipo, url}`, onde `tipo` é um serviço do catálogo padronizado (ver 2.4).

### 2.2 Repositórios e pastas (item 2)
- `repositorio/` passa a ser o **clone local** de `https://gitlab.com/paralivre/comunidades-de-tecnologia-pa`.
- O clone antigo em `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa` fica **descontinuado**:
  não será mais usado como pasta de destino. Todo o trabalho passa a ser feito em `repositorio/`.
- O clone contém **mais que o README**: inclui também `LICENSE` (e qualquer arquivo futuro). O bot
  deve tratar o `README.md` como alvo das edições e **preservar os demais arquivos**.
- O README a ser usado é **exclusivamente** o do clone `repositorio/` (fonte da verdade).
- A pasta `/home/roberto/projetos/comunidades/` **não** faz parte deste projeto (uso antigo) e deve
  ser ignorada. A última atualização real do repositório alvo foi feita em
  `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa` e está refletida no clone GitLab.
- O projeto inicia a partir da referência atual do clone: a comunidade **Divas Digitais** é a
  **última adicionada** e, portanto, a **única** que deve exibir o marcador `:triangular_flag_on_post:`.
- A pasta `atualizar-repositorio-comunidades/` será inicializada como repositório git com remote
  `origin` = `https://github.com/JosehRoberto/atualizar-repositorio-comunidades`.
- `backup/` guarda os backups dos arquivos alterados: `backup/README_YYYYMMDD_HHMMSS.bak`.
- `docs/` guarda a documentação do projeto (este arquivo, prompts, planejamentos).
- **Atenção:** o clone `repositorio/` contém `.git` próprio (repositório aninhado) e o repositório
  alvo também possui `LICENSE` (não só o README). O `repositorio/` deve entrar no `.gitignore` do
  projeto para não virar submódulo acidental.

### 2.3 Localização do código (item 3)
- Todo o código do bot fica em `bot/`, seguindo a organização do projeto de referência
  (`bot/handlers`, `bot/models`, `bot/schemas`, `bot/services`, `bot/tests`, `config.py`, `main.py`).

### 2.4 Formato do bloco Markdown (itens 4 e 6)
- **Ordem de inserção das linhas:** alfabética, pelo nome da comunidade (comparação normalizada:
  sem caixa e sem acentos), dentro da seção correspondente.
- **Ordem padronizada dos badges** (ordem canônica única, aplicada a linhas novas e editadas):
  1. Site
  2. GitHub
  3. GitLab
  4. Instagram
  5. Facebook
  6. LinkedIn
  7. X
  8. YouTube
  9. Meetup
  10. Slack
  11. Discord
  12. Telegram
  13. WhatsApp
  14. LinkTree
  15. Google Drive
  16. Outros (ordem de cadastro)
- **Especificação do badge** (formato `shields.io` já usado no README):

  | Serviço     | Cor      | logo=          |
  |-------------|----------|----------------|
  | Site        | `4285F4` | `googlechrome` |
  | GitHub      | `181717` | `github`       |
  | GitLab      | `FC6D26` | `gitlab`       |
  | Instagram   | `E4405F` | `instagram`    |
  | Facebook    | `1877F2` | `facebook`     |
  | LinkedIn    | `0A66C2` | `linkedin`     |
  | X           | `000000` | `x`            |
  | YouTube     | `FF0000` | `youtube`      |
  | Meetup      | `ED1C40` | `meetup`       |
  | Slack       | `4A154B` | `slack`        |
  | Discord     | `5865F2` | `discord`      |
  | Telegram    | `2CA5E0` | `telegram`     |
  | WhatsApp    | `25D366` | `whatsapp`     |
  | LinkTree    | `43E55E` | `linktree`     |
  | Google Drive| `4285F4` | `googledrive`  |

- **Template da linha:**
  `` | **NOME** [MARCADOR] | <a href="URL" title="TIPO"><img src="https://img.shields.io/badge/TIPO-COR?logo=LOGO&logoColor=white" alt="TIPO"/></a> ... | ``
- **Normalização aplicada somente à linha inserida/editada** (item 9: alteração cirúrgica). As demais
  linhas do README **não** são reformatadas.
- Inconsistências existentes no README (ex.: badge Meetup com cor `E4405F`, LinkTree com `E4405F`,
  fechamento `></a>` em vez de `/></a>`) **não serão corrigidas automaticamente** — só em linhas
  editadas pela comunidade correspondente.

### 2.5 Marcador `:triangular_flag_on_post:` (item 5)
Regra definida:
- Ao inserir uma **nova** comunidade, adicionar `:triangular_flag_on_post:` a ela e **remover** o
  marcador da comunidade que o possuía antes (a "última adicionada").
- Ao **editar** uma comunidade, preservar seu marcador atual.
- O marcador fica entre o nome e o pipe: `| **NOME** :triangular_flag_on_post: | ... |`.

**Decisão confirmada (1ª execução):** o estado de referência do projeto é **Divas Digitais como a
única comunidade marcada** com `:triangular_flag_on_post:`. Portanto, na primeira execução o bot deve
**normalizar** o README: remover o marcador de todas as demais comunidades e adicioná-lo à Divas
Digitais. A partir daí, vale a regra acima (ao inserir nova comunidade, o marcador migra para ela).
Observação: o README atual tem marcador em ~10 outras comunidades (Delphi Users Group Pará, LAFC²,
AWS Student Builder Groups, AWS User Groups Castanhal/Parauapebas, Zabbix Belém etc.) e a própria
Divas Digitais está sem marcador — essa normalização inicial corrige essa divergência.

### 2.6 Seções (item 6)
O README tem seções heterogêneas que o parser deve suportar:
- Cabeçalho `##` com emoji + âncora `<a name="..."></a>`.
- Duas seções usam o mesmo emoji 🌐 ("Capítulos Locais" e "Observatório").
- A seção **Observatório Amazônico** usa o schema `| Serviço | Link |` (não `| Comunidade | Links |`).
- Blocos de "Veja também" (cross-references) e a lista "Navegação Rápida".

**Solução padrão proposta para criação de nova seção:**
1. Inserir a âncora `<a name="slug"></a>` a partir do título, com os mesmos separadores `---` das
   seções vizinhas.
2. Inserir o título `## <emoji> <Título>`.
3. Inserir a tabela com o schema padrão `| Comunidade | Links |`.
4. Atualizar a **lista "Navegação Rápida"** (linha `- [emoji Título](#slug)`), inserida na posição
   correspondente à ordem lógica do README.
5. Posicionamento: nova seção é gravada **antes** do bloco `## 🤝 Como Contribuir`.
6. O bot pede o emoji e o título, e mostra a posição sugerida no preview.

### 2.7 Autenticação Git/GitLab (item 7)
- Autenticação por **Personal Access Token (PAT)** do GitLab, como já usado hoje no clone existente,
  porém com o token **fora da URL**:
  - `.env`: `GITLAB_TOKEN=...`, `GITLAB_USERNAME=oauth2` (ou `git`), `GIT_REPO_URL`, `GIT_BRANCH=master`,
    `GIT_USER_NAME=ParaLivre`, `GIT_USER_EMAIL=contato@paralivre.org`.
  - A montagem da URL autenticada é feita em runtime, sem persistir o token no `.git/config`.
- Alternativa avaliada: `credential.helper store` (já ativo globalmente) — descartada por deixar o
  token em `~/.git-credentials`; a variável de ambiente é preferível.
- **Segurança:** o token atual está exposto em texto em
  `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa/.git/config`. Esse token deve ser
  considerado comprometido e rotacionado no GitLab.

### 2.8 Validações (item 8)
Soluções propostas:
- **Campos obrigatórios:** nome não vazio; ao menos 1 link.
- **URLs válidas:** aceitar `http`/`https` (e `tg://`/`telegram.me` quando aplicável); exigir domínio
  válido; normalizar (remover espaços, garantir esquema); opcionalmente checar HTTP 200/301/302 com
  timeout curto (aviso, não bloqueio).
- **Duplicidade:** comparar nome normalizado e URL principal/links contra o README e contra o estado
  do próprio fluxo; bloquear duplicata exata e alertar similaridade.
- **Seção existente:** validar contra a lista de seções parseadas.
- **Consistência do Markdown:** reparsear o resultado e garantir que a contagem de linhas por seção,
  cabeçalhos, âncoras e navegação continuam íntegros; diff deve tocar apenas a linha/bloco alvo.
- **`🧩 Validar README` (comando completo):** varredura do arquivo inteiro verificando
  (a) integridade das tabelas (colunas, separadores), (b) âncoras da navegação x seções existentes,
  (c) duplicidades de nome/URL, (d) URLs sintaticamente inválidas, (e) coerência do marcador
  (no máximo 1 comunidade marcada). Relatório por severidade (erro/aviso).

### 2.9 Persistência (item 9)
- **Estado da conversa:** `python-telegram-bot` com `PicklePersistence` (ou armazenamento JSON em
  `bot/state/`), mantendo o padrão do projeto de referência (`state_manager.py`).
- **Histórico de alterações:** arquivo **JSONL append-only** em `bot/history/historico.jsonl`, com:
  `timestamp`, `usuario_id`, `acao`, `secao`, `comunidade`, `antes`, `depois`, `backup_path`,
  `commit` (quando houver).
- Justificativa: JSON/JSONL é transparente, versionável, sem dependência extra e alinhado ao uso de
  JSON no `agendatipara-bot`. SQLite fica como evolução futura se houver volume.

### 2.10 Identificação para edição/remoção (item 10)
- Chave canônica = **nome normalizado** (minúsculas, sem acentos, sem emoji/marcador, espaços
  colapsados, sem pontuação decorativa).
- Fluxo: match exato pela chave canônica → se não houver, **fuzzy** (ex.: `rapidfuzz`/`difflib`) →
  apresentar lista de candidatos numerada para o usuário escolher. Nunca editar/remover "no escuro".
- Desempate por URL quando houver nomes homônimos.

### 2.11 Rollback (item 11)
Solução proposta:
- `/restaurar` passa a ser **novo item do menu principal** (além de "↩️ Cancelar", que continua
  válido), conforme sugerido no item 11.
- Fluxo: listar backups de `backup/README_*.bak` (mais recente primeiro) → selecionar →
  mostrar **diff/preview** do que será restaurado → confirmação explícita → criar backup do estado
  atual (`README_pre-restauracao_*.bak`) → restaurar → registrar no histórico.
- Rollback de publicação Git = reverter commit/`git revert` (documentado no README do projeto), sem
  nunca fazer `reset --hard` no remoto.

### 2.12 Multi-usuário e sincronização (item 12)
- Já previsto para vários usuários autorizados via `TELEGRAM_ALLOWED_USER_IDS` (lista, não um só id).
- **Concorrência:** `asyncio.Lock` global por arquivo — apenas um fluxo de escrita por vez; demais
  usuários recebem "aguarde, há uma edição em andamento".
- **Sincronização:** antes de qualquer edição, `git fetch` + `git pull --ff-only` (ou verificação de
  `HEAD` x `origin/master`). Se houver divergência local ou alteração remota conflitante, abortar e
  avisar, em vez de sobrescrever.
- **Proteção adicional:** registrar hash do README lido na aprovação e reconferir o hash antes de
  gravar; se mudou, exigir novo preview.

### 2.13 Versões e ambiente (item 13)
- Reaproveitar o `agendatipara-bot`: Python 3.12, `python-telegram-bot>=20`, `python-dotenv>=1.0`,
  `requests>=2.31`, `pydantic>=2.0`; `pytest` para testes; `pytest.ini` no mesmo formato.
- Ambiente virtual dedicado, de preferência em `bot/.env`.

### 2.14 Idioma (item 14)
- Toda a documentação, mensagens do bot e comentários em **português do Brasil (pt-BR)**.

### 2.15 Nome do bot (item 15)
- **Username no Telegram:** `@atualizar_repositorio_bot` (bot já criado).
- **Unit systemd:** `atualizar-repositorio-bot.service`.
- Diretório do código permanece `bot/`.

### 2.16 Fuso horário (item 15, repetido)
- `America/Belem`, usado nos timestamps de backup e de histórico.

---

## 3. Pendências / conflitos

Itens **resolvidos** com as definições do projeto e itens **em aberto** abaixo.

1. **Fonte da verdade (resolvido):** o README é sempre o do clone `repositorio/`. A pasta
   `/home/roberto/projetos/comunidades/` é de uso antigo e está fora do escopo.
2. **Marcador `:triangular_flag_on_post:` (resolvido):** partir de **Divas Digitais** como a única
   comunidade marcada; o bot normaliza as demais marcações na 1ª execução.
3. **Clone único (resolvido):** `repositorio/` é o único clone gerenciado pelo bot. O clone antigo
   em `/home/roberto/projetos/paralivre/comunidades-de-tecnologia-pa` fica descontinuado e fora do
   fluxo.
4. **Token GitLab (resolvido):** token antigo **revogado** e exposição local removida (de
   `~/.git-credentials` e da URL do remote do clone antigo). Novo token `comunidades-bot`
   (`api`, `write_repository`; expira em 20/10/2027) validado e cadastrado em `bot/.env`.

---

## 4. Estrutura de pastas proposta

```
atualizar-repositorio-comunidades/
├── bot/
│   ├── handlers/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   ├── config.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── backup/
│   └── README_YYYYMMDD_HHMMSS.bak
├── docs/
│   ├── prompt-inicial.md
│   └── requisitos.md
├── repositorio/            # clone do GitLab (ignorado no .git do projeto)
│   ├── README.md
│   └── LICENSE
├── .gitignore
├── CHANGELOG.md
└── README.md
```

---

## 5. Variáveis de ambiente (`.env`)

| Variável                     | Descrição                                             |
|------------------------------|-------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`         | Token do bot Telegram                                 |
| `TELEGRAM_ALLOWED_USER_IDS`  | IDs autorizados (separados por vírgula)               |
| `GITLAB_TOKEN`               | Personal Access Token do GitLab                      |
| `GITLAB_USERNAME`            | Usuário para a URL autenticada (ex.: `oauth2`)        |
| `GIT_REPO_URL`               | `https://gitlab.com/paralivre/comunidades-de-tecnologia-pa.git` |
| `GIT_BRANCH`                 | Branch base (ex.: `master`)                           |
| `GIT_USER_NAME`              | Nome do commit (ex.: `ParaLivre`)                     |
| `GIT_USER_EMAIL`             | E-mail do commit (ex.: `contato@paralivre.org`)       |
| `README_PATH`                | Caminho do README no clone (ex.: `repositorio/README.md`) |
| `BACKUP_DIR`                 | Pasta de backups (ex.: `backup`)                      |
| `TIMEZONE`                   | `America/Belem`                                       |

---

## 6. Próximos passos

### Concluído

1. Estrutura inicial do projeto (git, `.gitignore`) — commit `8af47a3`.
2. Clone do repositório alvo em `repositorio/`.
3. `AGENTS.md`, `CHANGELOG.md` e `README.md` do projeto.
4. Esqueleto do bot em `bot/` (config, handlers, models, schemas, services, tests) — commit `ec67e9e`.

### Em andamento

5. Implementar o parser/editor do README (`bot/services/readme_service.py`), o serviço de backup e o
   de histórico — cada um com teste hermético.
6. Implementar `bot/handlers/state_manager.py` e os fluxos do Telegram (menu, preview, aprovação).
7. Implementar a publicação (`/publicar`) e o rollback (`/restaurar`).
8. Escrever testes de fluxo e manter a documentação atualizada.
9. Configurar a unit systemd para deploy (`bot/.env` já configurado).

> Handoff detalhado para a próxima sessão: `docs/nova-sessao.md`.
