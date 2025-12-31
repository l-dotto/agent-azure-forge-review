# Azure Code Reviewer

Sistema automatizado de code review para Azure DevOps Pull Requests.

## Status do Projeto

**Em Desenvolvimento:** MVP - Sistema de Code Review Automatizado
**Progresso:** Estrutura criada, iniciando Fase 1
**Plano:** [PLANO_IMPLEMENTACAO.md](PLANO_IMPLEMENTACAO.md)

## Stack Tecnológica

### MVP - Foco Atual (Sistema de Code Review Automatizado)
- **Orquestração:** Python 3.11+ (scripts de pipeline)
- **LLM:** Anthropic Claude API (Sonnet 4.5 + Opus 4.5)
- **Pipeline:** Azure Pipelines (YAML)
- **API Integration:** Azure DevOps REST API v7.1
- **Templates:** Jinja2 para geração de comentários
- **Parsing:** Markdown-it-py para análise de outputs

### Futuro - V2.0+ (Dashboard e Analytics - não implementado)
- **Backend:** Node.js/TypeScript + Express/Fastify
- **Frontend:** React + Vite + TypeScript
- **Database:** PostgreSQL (persistência de findings)
- **Cache:** Redis (otimização de queries)
- **Deploy:** Docker + Azure Container Instances / AWS ECS

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
- ✅ Code review automático antes de commits
- ✅ Testes obrigatórios para lógica crítica
- ✅ Clean Architecture (separation of concerns)
- ✅ Documentação clara em PRs

## Workflow de Desenvolvimento

```bash
# 1. Criar branch
git checkout -b feature/nome-da-feature

# 2. Desenvolver e testar localmente
pytest tests/

# 3. Code review antes de commit
make lint
make format

# 4. Commit seguindo Conventional Commits
git commit -m "feat(agents): add security review parser"

# 5. Push e criar PR
git push -u origin feature/nome-da-feature
```

## Review Agents (Core do MVP)

O sistema utiliza três agents especializados que executam automaticamente via Azure Pipeline:

### Sentinel - Security Review Agent
- **Arquivo:** [`.claude/agents/security-review-slash-command.md`](.claude/agents/security-review-slash-command.md)
- **Foco:** Vulnerabilidades exploráveis (SQLi, XSS, RCE, auth bypass, secrets exposure)
- **Modelo:** Claude Sonnet 4.5
- **Confiança mínima:** 80%
- **Output:** Markdown → JSON estruturado com exploit scenarios
- **Runner:** `scripts/agents/run_security_review.py` (Fase 2)

### Atlas - Design Review Agent
- **Arquivo:** [`.claude/agents/design-review-slash-command.md`](.claude/agents/design-review-slash-command.md)
- **Foco:** UX, acessibilidade (WCAG), design systems, visual consistency
- **Modelo:** Claude Sonnet 4.5
- **Padrões:** Stripe, Airbnb, Linear, Vercel
- **Output:** Markdown → JSON com findings de design
- **Runner:** `scripts/agents/run_design_review.py` (Fase 3)

### Forge - Code Review Agent
- **Arquivo:** [`.claude/agents/pragmatic-code-review-subagent.md`](.claude/agents/pragmatic-code-review-subagent.md)
- **Foco:** Arquitetura, qualidade, manutenibilidade, performance
- **Modelo:** Claude Opus 4.5 (análise mais profunda)
- **Framework:** Net Positive over Perfection
- **Output:** Markdown → JSON (Critical/Improvements/Nits)
- **Runner:** `scripts/agents/run_code_review.py` (Fase 3)

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

### Componentes Principais (Implementação por Fase)

1. **Azure Pipeline** ([`azure-pipelines.yml`](azure-pipelines.yml)) - Fase 1
   - Trigger automático em cada push no PR
   - Execução sequencial dos 3 agents
   - Normalização e publicação de resultados

2. **Agent Runners** (`scripts/agents/`) - Fases 2-3
   - [`run_security_review.py`](scripts/agents/) - Sentinel (Fase 2)
   - [`run_design_review.py`](scripts/agents/) - Atlas (Fase 3)
   - [`run_code_review.py`](scripts/agents/) - Forge (Fase 3)

3. **Utilities** (`scripts/utils/`) - Fases 2-5
   - [`git_diff_parser.py`](scripts/utils/) - Extração e sanitização de diffs (Fase 2)
   - [`markdown_parser.py`](scripts/utils/) - Parse de findings Markdown → JSON (Fase 2)
   - [`azure_devops_client.py`](scripts/utils/) - API client para Azure DevOps (Fase 5)
   - [`finding_deduplicator.py`](scripts/utils/) - Deduplicação inteligente (Fase 4)

4. **Normalizer** ([`scripts/normalize_results.py`](scripts/)) - Fase 4
   - Merge findings dos 3 agents
   - Deduplicação por hash e similaridade
   - Ordenação por severity (critical → low)
   - Geração de `reviewResult.json` canônico

5. **PR Publisher** ([`scripts/publish_to_pr.py`](scripts/)) - Fase 5
   - Templates Jinja2 para comentários
   - Summary thread (top-level)
   - Inline comments com threshold configurável

### Configuração

**Variáveis de Ambiente:**
- `ANTHROPIC_API_KEY` - Secret no Variable Group `code-review-secrets`
- `INLINE_SEVERITY_THRESHOLD` - `critical` | `high` (default) | `medium` | `all`

**Permissões Azure DevOps:**
- Build Service: `Contribute to Pull Requests`
- Branch Policy: Build Validation habilitado

## Estrutura do Projeto

```
azure-code-reviewer/
├── .claude/                           # Configuração Claude Code
│   ├── agents/                        # Review agents (core do sistema)
│   │   ├── security-review-slash-command.md      # Sentinel
│   │   ├── design-review-slash-command.md        # Atlas
│   │   └── pragmatic-code-review-subagent.md     # Forge
│   ├── rules/                         # Regras de desenvolvimento
│   │   ├── git-commit.md              # Conventional Commits, branching
│   │   ├── security.md                # Validação, sanitização, criptografia
│   │   ├── api-standards.md           # Clean Architecture, DTOs
│   │   ├── frontend-security.md       # Tokens, XSS, sanitização
│   │   ├── performance.md             # Otimizações, queries
│   │   ├── pipeline.md                # CI/CD, scanners
│   │   └── aws-infrastructure.md      # VPC, SG, IAM (futuro)
│   ├── hooks/                         # Git hooks customizados
│   ├── settings.json                  # Configurações compartilhadas
│   └── .gitignore
│
├── scripts/                           # Implementação Python (MVP)
│   ├── agents/                        # Agent runners
│   │   ├── run_security_review.py     # Fase 2
│   │   ├── run_design_review.py       # Fase 3
│   │   └── run_code_review.py         # Fase 3
│   ├── utils/                         # Utilitários
│   │   ├── git_diff_parser.py         # Fase 2
│   │   ├── markdown_parser.py         # Fase 2
│   │   ├── azure_devops_client.py     # Fase 5
│   │   └── finding_deduplicator.py    # Fase 4
│   ├── templates/                     # Templates Jinja2
│   │   ├── summary.md.jinja2          # Fase 5
│   │   └── finding.md.jinja2          # Fase 5
│   ├── normalize_results.py           # Fase 4
│   └── publish_to_pr.py               # Fase 5
│
├── tests/                             # Test suite
│   ├── unit/                          # Testes unitários
│   ├── integration/                   # Testes de integração
│   └── fixtures/                      # Dados de teste
│
├── docs/                              # Documentação
│   ├── guides/                        # Guias de usuário
│   ├── architecture/                  # Arquitetura técnica
│   └── examples/                      # Exemplos de uso
│
├── findings/                          # Outputs gerados (gitignored)
│   ├── security.json
│   ├── design.json
│   └── code.json
│
├── azure-pipelines.yml                # Pipeline principal
├── requirements.txt                   # Dependências Python
├── pytest.ini                         # Configuração de testes
├── Makefile                           # Comandos de desenvolvimento
├── README.md                          # Documentação principal
├── CLAUDE.md                          # Este arquivo (instruções)
├── PLANO_IMPLEMENTACAO.md            # Plano detalhado
├── CONTRIBUTING.md                    # Guia de contribuição
└── LICENSE                            # MIT License
```

## Roadmap

### V1.0 - MVP (Em Desenvolvimento)
**Objetivo:** Sistema funcional de code review automatizado

**Fases:**
1. Setup Básico - Infraestrutura e configuração
2. Security Review Agent - Primeiro agent funcionando
3. Design e Code Agents - Completar os 3 agents
4. Normalizer - Consolidação de resultados
5. PR Publisher - Publicação no Azure DevOps
6. Polish e Documentação - Finalização

**Entrega:** Sistema publicando comentários estruturados em PRs do Azure DevOps

### V2.0 - Dashboard e Analytics (Futuro)
**Stack:** Node.js/TypeScript + React + Vite + PostgreSQL

**Features:**
- Dashboard web para visualização histórica
- Métricas e analytics de qualidade do código
- API REST para consulta de findings
- Persistência em PostgreSQL
- Notificações (Slack/Teams)

**Estimativa:** 4 semanas após V1.0

### V3.0 - Advanced Features (Futuro)
**Features:**
- Fine-tuning de agents com exemplos do projeto
- Modo auto-fix (gera PRs de correção)
- Integração SonarQube/Checkmarx
- Suporte multi-repo

**Estimativa:** 6 semanas após V2.0

## Recursos e Ferramentas

### Serena MCP (Navegação de Código)
Este projeto usa Serena MCP para navegação semântica eficiente:
- `find_symbol` - Localiza classes, funções, variáveis
- `search_for_pattern` - Busca padrões no código
- `find_file` - Encontra arquivos por nome
- `list_dir` - Lista estrutura de diretórios

### Comandos Make (Desenvolvimento)
```bash
make install    # Instalar dependências
make test       # Executar testes com coverage
make lint       # Linters (flake8, mypy)
make format     # Formatar código (black)
make clean      # Limpar arquivos gerados
```

## Para Reutilizar em Outros Projetos

1. **Copie a estrutura base:**
   ```bash
   cp -r .claude/ novo-projeto/
   cp CLAUDE.md novo-projeto/
   cp azure-pipelines.yml novo-projeto/
   ```

2. **Ajuste para seu contexto:**
   - Edite `.claude/rules/` conforme stack do projeto
   - Adapte agents em `.claude/agents/` se necessário
   - Configure `INLINE_SEVERITY_THRESHOLD` no pipeline

3. **Configure Azure DevOps:**
   - Variable Group: `code-review-secrets`
   - Secret: `ANTHROPIC_API_KEY`
   - Permissão Build Service: `Contribute to Pull Requests`
   - Branch Policy: Build Validation

4. **Customize templates:**
   - `scripts/templates/summary.md.jinja2`
   - `scripts/templates/finding.md.jinja2`
