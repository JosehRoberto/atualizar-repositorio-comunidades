Analise o projeto local `agendatipara-bot` e crie um novo bot Telegram, reutilizando a mesma arquitetura, padrões de código, fluxo conversacional, validação, preview, aprovação e organização de handlers já usados neste projeto.

Objetivo do novo bot:
Facilitar a atualização do arquivo `README.md` do repositório GitLab:
https://gitlab.com/paralivre/comunidades-de-tecnologia-pa

O bot deve permitir cadastrar, editar, listar, buscar e remover comunidades de tecnologia nas seções já existentes do README.md, sem que o usuário precise editar o arquivo manualmente.

Requisitos obrigatórios:

1. O bot deve operar sobre um clone local do repositório no computador Ubuntu 24.04.
2. Antes de qualquer modificação, criar backup do README.md em `backup/`, usando o padrão:
   backup/README_YYYYMMDD_HHMMSS.bak
3. Ler e interpretar o README.md preservando integralmente sua estrutura, títulos, seções, ordem, formatação Markdown e estilo atual.
4. Implementar um menu principal no Telegram com:
   - ➕ Nova comunidade
   - 🔍 Buscar comunidade
   - ✏️ Editar comunidade
   - 🗑️ Remover comunidade
   - 📋 Listar comunidades
   - 🧩 Validar README
   - 📜 Histórico de alterações
   - ⬆️ Publicar alterações
   - ↩️ Cancelar
5. No fluxo de nova comunidade, perguntar:
   - Seção de destino no README
   - Nome oficial da comunidade
   - Cidade ou região
   - Descrição curta
   - Tecnologias, áreas ou temas
   - Links oficiais: site, GitHub/GitLab, Instagram, LinkedIn, YouTube, Discord, Telegram e outros
6. Validar:
   - Campos obrigatórios
   - URLs válidas
   - Duplicidade de comunidade por nome ou URL principal
   - Se a seção escolhida existe no README
   - Consistência do Markdown gerado
7. Antes de gravar qualquer alteração, enviar ao usuário um preview claro do bloco Markdown final e permitir:
   - ✅ Aprovar
   - ✏️ Editar campo
   - 🔀 Trocar seção
   - ❌ Cancelar
8. Somente após aprovação explícita:
   - Criar backup
   - Aplicar a alteração no README.md local
   - Registrar a operação em histórico local
9. A alteração deve ser cirúrgica: inserir, atualizar ou remover apenas o bloco da comunidade, sem reformatar ou reescrever outras partes do README.
10. Implementar o comando `/publicar` apenas como etapa separada, com opções:
   - Commit local
   - Criar branch e commit
   - Push para branch remota
   - Criar Merge Request no GitLab
11. Nenhum commit, push ou Merge Request pode ser executado sem confirmação explícita do usuário.
12. Restringir o uso do bot a usuários autorizados por `TELEGRAM_ALLOWED_USER_IDS`.
13. Armazenar segredos apenas em `.env`, com `.env.example` documentando todas as variáveis necessárias.
14. Criar testes automatizados para:
   - Parser das seções do README
   - Detecção de duplicidades
   - Inserção de nova comunidade
   - Edição de comunidade existente
   - Remoção de comunidade
   - Preservação da formatação Markdown
   - Validação de URLs
   - Fluxo de aprovação
15. Criar documentação em README.md do novo projeto contendo:
   - Objetivo
   - Instalação
   - Configuração do `.env`
   - Comandos do bot
   - Fluxo de uso
   - Estrutura do projeto
   - Política de backup
   - Instruções de deploy local via systemd
   - Instruções de rollback

Entregáveis esperados:
- Estrutura completa do novo projeto
- Código-fonte funcional do bot
- Parser e editor seguro de Markdown
- Handlers do Telegram
- Modelo de dados da comunidade
- Serviço de backup
- Serviço de histórico
- Serviço Git/GitLab opcional
- Testes pytest
- `.env.example`
- README.md do novo projeto
- CHANGELOG.md inicial