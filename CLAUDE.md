# Azure Code Reviewer

Sistema automatizado de code review para Azure DevOps Pull Requests usando Claude AI.

## 🚀 Status do Projeto

**Em Desenvolvimento:** MVP - Sistema de Code Review Automatizado
**Progresso:** 0/26 tasks concluídas (0%)
**Plano:** [PLANO_IMPLEMENTACAO.md](PLANO_IMPLEMENTACAO.md)

## Stack Tecnológica

### MVP (Sistema de Code Review)
- **Orquestração:** Python 3.11+ (scripts de pipeline)
- **LLM:** Anthropic Claude (Sonnet 4.5 + Opus 4.5)
- **Pipeline:** Azure Pipelines (YAML)
- **API Integration:** Azure DevOps REST API v7.1

### Futuro (Backend Principal - não implementado)
- **Backend:** Java 21/Spring Boot 3.3.4
- **Frontend:** React/Vite/TypeScript
- **Database:** PostgreSQL
- **Cache:** Redis
- **Cloud:** AWS (S3, SES, EventBridge)
- **Build:** Gradle/Kotlin DSL

## Regras de Desenvolvimento

Este projeto segue regras rigorosas de qualidade, segurança e governança.

**IMPORTANTE:** Todas as regras detalhadas estão em [.claude/rules/](.claude/rules/) e são aplicadas automaticamente:

- **[git-commit.md](.claude/rules/git-commit.md)** - Conventional Commits, branching, nunca mencionar AI
- **[security.md](.claude/rules/security.md)** - Validação, sanitização, criptografia, sem secrets
- **[api-standards.md](.claude/rules/api-standards.md)** - Clean Architecture, DTOs, idempotência
- **[frontend-security.md](.claude/rules/frontend-security.md)** - Tokens httpOnly, sanitização XSS
- **[aws-infrastructure.md](.claude/rules/aws-infrastructure.md)** - VPC, SG, criptografia, IAM mínimo
- **[performance.md](.claude/rules/performance.md)** - Otimizações, queries eficientes
- **[pipeline.md](.claude/rules/pipeline.md)** - CI/CD, scanners de segurança

## Regras Críticas (Resumo)

### Git & Commits
- ❌ **NUNCA** citar Claude, AI ou incluir "Generated with Claude Code"
- ❌ **NUNCA** commitar direto em master/main
- ✅ Sempre criar feature branch: `git checkout -b feature/nome`
- ✅ Conventional Commits: `feat:`, `fix:`, `chore:`, `refactor:`
- ✅ Commits pequenos (< 400 linhas) e focados

### Segurança
- ❌ **NUNCA** incluir secrets, tokens, chaves ou dados sensíveis
- ✅ Validar e sanitizar **TODAS** as entradas
- ✅ Proteger contra: SQL Injection, XSS, CSRF
- ✅ Mascarar dados sensíveis em logs (CPF, cartão, senhas)

### Qualidade
- ✅ Code review automático antes de commits (solicite ao Claude)
- ✅ Testes obrigatórios para lógica financeira
- ✅ Clean Architecture (domain, use-cases, infra)
- ✅ Documentação clara em PRs

## Workflow de Desenvolvimento

```bash
# 1. Criar branch
git checkout -b feature/nome-da-feature

# 2. Desenvolver e testar localmente

# 3. Antes de commitar, solicitar code review
# No chat: "Execute o code review completo"

# 4. Commit seguindo Conventional Commits
git commit -m "feat(payment): add PIX confirmation flow"

# 5. Push e criar PR
git push -u origin feature/nome-da-feature
```

## Agents Disponíveis

### Agents de Code Review (Automatizados via Pipeline)

- **🛡️ Sentinel** (`security-review-slash-command`) - Análise de segurança
  - Foco: Vulnerabilidades exploráveis (SQLi, XSS, RCE, auth bypass)
  - Modelo: Claude Sonnet 4.5
  - Confiança mínima: 80%
  - Output: Markdown → JSON com exploit scenarios

- **🎨 Atlas** (`design-review-slash-command`) - Revisão de design e UX
  - Foco: UX, acessibilidade, visual design
  - Modelo: Claude Sonnet 4.5
  - Padrões: Stripe, Airbnb, Linear
  - Output: Markdown → JSON com findings de design

- **🧠 Forge** (`pragmatic-code-review-subagent`) - Revisão pragmática de código
  - Foco: Arquitetura, qualidade, manutenibilidade, performance
  - Modelo: Claude Opus 4.5 (mais profundo)
  - Framework: Net Positive > Perfection
  - Output: Markdown → JSON (Critical/Improvements/Nits)

### Como Funciona

1. Developer cria/atualiza PR no Azure DevOps
2. Branch Policy trigger pipeline automaticamente
3. Pipeline executa 3 agents em sequência
4. Resultados normalizados e publicados como comentários no PR
5. Threshold configurável via `INLINE_SEVERITY_THRESHOLD` (critical/high/medium/all)

## Arquitetura do Sistema de Code Review

```
PR Created/Updated (Azure DevOps)
        ↓
Azure Pipeline (Triggered by Branch Policy)
        ↓
┌───────┼───────┬───────────┐
↓       ↓       ↓           ↓
Sentinel Atlas  Forge       git diff
↓       ↓       ↓           ↓
security design code   →  Normalizer
.json   .json   .json      ↓
                    reviewResult.json
                           ↓
                    PR Publisher
                           ↓
        ┌──────────────────┼──────────────────┐
        ↓                                     ↓
Summary Thread                        Inline Comments
(top-level)                          (file-specific)
```

### Componentes Principais

1. **Azure Pipeline** (`azure-pipelines.yml`)
   - Trigger: em cada push no PR
   - Execução sequencial dos 3 agents
   - Normalização e publicação

2. **Agent Runners** (`scripts/agents/`)
   - `run_security_review.py` - Sentinel
   - `run_design_review.py` - Atlas
   - `run_code_review.py` - Forge

3. **Normalizer** (`scripts/normalize_results.py`)
   - Merge findings dos 3 agents
   - Deduplicação e ordenação por severity

4. **PR Publisher** (`scripts/publish_to_pr.py`)
   - Cria summary thread
   - Cria inline comments (threshold configurável)

### Configuração

**Variáveis de Ambiente:**
- `ANTHROPIC_API_KEY` - Secret no Variable Group `code-review-secrets`
- `INLINE_SEVERITY_THRESHOLD` - `critical` | `high` (default) | `medium` | `all`

**Permissões Azure DevOps:**
- Build Service: `Contribute to Pull Requests`
- Branch Policy: Build Validation habilitado

## Estrutura Claude Code

```
.claude/
├── settings.json           # Configurações compartilhadas (hooks, permissions)
├── settings.local.json     # Configurações pessoais (não versionado)
├── rules/                  # Regras detalhadas do projeto
│   ├── api-standards.md
│   ├── aws-infrastructure.md
│   ├── frontend-security.md
│   ├── git-commit.md
│   ├── performance.md
│   ├── pipeline.md
│   └── security.md
├── agents/                 # Agents customizados
│   ├── design-review-slash-command.md
│   ├── security-review-slash-command.md
│   └── pragmatic-code-review-subagent.md
└── .gitignore              # Ignora settings.local.json
```

## Para Reutilizar em Outros Projetos

1. Copie a pasta `.claude/` completa
2. Copie `CLAUDE.md` e `PLANO_IMPLEMENTACAO.md`
3. Copie `scripts/` e `azure-pipelines.yml` (quando implementados)
4. Configure Azure DevOps:
   - Variable Group `code-review-secrets`
   - Permissões Build Service
   - Branch Policy
5. Customize regras em `.claude/rules/` conforme necessário

## Serena MCP

Este projeto usa **Serena MCP** para navegação semântica no código:

- `find_symbol` - Encontra classes, funções, variáveis
- `search_for_pattern` - Busca padrões de código
- `find_file` - Localiza arquivos
- `list_dir` - Lista diretórios

**Uso eficiente:** Serena permite ler código simbolicamente sem carregar arquivos inteiros, economizando tokens.
