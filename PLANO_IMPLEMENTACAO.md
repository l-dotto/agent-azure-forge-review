# 🏗️ PLANO DE IMPLEMENTAÇÃO: Sistema de Code Review Automatizado

**Status:** 🟡 Em Progresso
**Data Início:** 2025-12-30
**Estimativa:** 11 dias úteis (~2.5 semanas)
**Versão:** 1.0 (MVP)

---

## 📊 PROGRESSO GERAL

```
Fase 1: Setup Básico              [ ] 0% (0/4 tasks)
Fase 2: Security Review Agent     [ ] 0% (0/5 tasks)
Fase 3: Design + Code Agents      [ ] 0% (0/4 tasks)
Fase 4: Normalizer                [ ] 0% (0/3 tasks)
Fase 5: PR Publisher              [ ] 0% (0/5 tasks)
Fase 6: Polish e Documentação     [ ] 0% (0/5 tasks)

Total: 0/26 tasks concluídas (0%)
```

---

## 🎯 VISÃO EXECUTIVA

### Objetivo
Sistema automatizado de code review que:
- ✅ Analisa Pull Requests no Azure DevOps
- ✅ Executa 3 agents especializados (Sentinel/Atlas/Forge)
- ✅ Publica comentários estruturados diretamente no PR
- ✅ Threshold configurável para inline comments
- ✅ Extensível para analytics futuros (sem refactor)

### Princípios de Design
1. **PR é a fonte da verdade operacional** - Resultados em JSON permitem expansão futura
2. **Branding técnico, não hype** - ❌ Nunca mencionar "AI/LLM/Claude" no PR
3. **Simplicidade agora, extensibilidade depois** - MVP clean, V2 com dashboard
4. **Open-source e atualidade** - Bibliotecas oficiais 2025

### Decisões Aprovadas
- ✅ Trigger: **em cada push no PR** (feedback contínuo)
- ✅ Inline comments: **configurável** via `INLINE_SEVERITY_THRESHOLD` (default: `high`)
- ✅ Scope: **Todos os 3 agents** (Security, Design, Code)
- ✅ Stack: **Python + Azure Pipelines YAML + Claude API**

---

## 📝 FASE 1: Setup Básico (1 dia)

**Objetivo:** Configurar infraestrutura mínima

### Tasks

- [ ] **1.1** Criar estrutura de diretórios
  ```bash
  mkdir -p scripts/{agents,utils,templates}
  ```
  - `scripts/agents/` - Runners dos agents
  - `scripts/utils/` - Utilitários (git, markdown parser, Azure client)
  - `scripts/templates/` - Templates Jinja2

- [ ] **1.2** Criar `requirements.txt`
  ```
  anthropic==0.39.0
  pyyaml==6.0.1
  requests==2.31.0
  markdown-it-py==3.0.0
  Jinja2==3.1.2
  tenacity==8.2.3
  ```

- [ ] **1.3** Criar `azure-pipelines.yml` (skeleton)
  - Trigger: `pr: branches: include: ['*']`
  - Pool: `ubuntu-latest`
  - Variables: `INLINE_SEVERITY_THRESHOLD=high`
  - Stages: `CodeReview` (vazio por enquanto)

- [ ] **1.4** Configurar Azure DevOps
  - [ ] Pipelines → Library → Variable Groups
  - [ ] Criar grupo `code-review-secrets`
  - [ ] Adicionar `ANTHROPIC_API_KEY` (Secret)
  - [ ] Project Settings → Repositories → Security
  - [ ] Conceder Build Service: `Contribute to Pull Requests`

**Critérios de Aceitação:**
- ✅ Pipeline roda sem erros (mesmo que vazio)
- ✅ Secrets carregados corretamente
- ✅ Build Service tem permissões

---

## 🛡️ FASE 2: Agent Runner - Security Review (2 dias)

**Objetivo:** Primeiro agent funcionando end-to-end

### Tasks

- [ ] **2.1** Implementar `scripts/utils/git_diff_parser.py`
  - Função `get_pr_diff(pr_id: int) -> str`
  - Executa: `git diff --merge-base origin/main`
  - Sanitiza secrets (regex para api_key, password, CPF, email)

- [ ] **2.2** Implementar `scripts/utils/markdown_parser.py`
  - Função `parse_security_markdown(md: str) -> list[dict]`
  - Parse com regex ou AST (`markdown-it-py`)
  - Extrai: severity, file, line, title, description, recommendation

- [ ] **2.3** Implementar `scripts/agents/run_security_review.py`
  - Carrega `.claude/agents/security-review-slash-command.md`
  - Substitui placeholders: `!`git diff...`` → diff real
  - Chama Claude API (model: `claude-sonnet-4-5-20250929`)
  - Parse markdown → JSON
  - Salva `findings/security.json`

- [ ] **2.4** Adicionar step no `azure-pipelines.yml`
  ```yaml
  - script: python scripts/agents/run_security_review.py --pr-id $(System.PullRequest.PullRequestId) --output findings/security.json
    env:
      ANTHROPIC_API_KEY: $(ANTHROPIC_API_KEY)
  ```

- [ ] **2.5** Testar em PR real
  - Criar PR com código vulnerável (SQL injection propositalmente)
  - Verificar `findings/security.json` gerado

**Critérios de Aceitação:**
- ✅ Agent executa e gera `findings/security.json`
- ✅ JSON estruturado corretamente
- ✅ Vulnerabilidades identificadas (teste com código vulnerável)

---

## 🎨 FASE 3: Agents Design e Code Review (2 dias)

**Objetivo:** Completar orquestração dos 3 agents

### Tasks

- [ ] **3.1** Implementar `scripts/agents/run_design_review.py`
  - Duplicar lógica de Security Review
  - Carregar `.claude/agents/design-review-slash-command.md`
  - Parser adaptado para findings de design (UX, acessibilidade)
  - Salvar `findings/design.json`

- [ ] **3.2** Implementar `scripts/agents/run_code_review.py`
  - Carregar `.claude/agents/pragmatic-code-review-subagent.md`
  - Usar model: `claude-opus-4-5-20251101` (mais profundo)
  - Parser para categorias: Critical/Improvements/Nits
  - Salvar `findings/code.json`

- [ ] **3.3** Adicionar steps no pipeline (sequencial)
  ```yaml
  - script: python scripts/agents/run_design_review.py ...
  - script: python scripts/agents/run_code_review.py ...
  ```

- [ ] **3.4** Testar execução dos 3 agents
  - Verificar tempo total < 5 minutos
  - Validar 3 JSONs gerados
  - Cada JSON reflete especialização do agent

**Critérios de Aceitação:**
- ✅ 3 JSONs gerados: `security.json`, `design.json`, `code.json`
- ✅ Cada JSON reflete especialização do agent
- ✅ Tempo de execução < 5 minutos (total)

---

## 🔄 FASE 4: Normalizer (1 dia)

**Objetivo:** Consolidar resultados dos 3 agents

### Tasks

- [ ] **4.1** Implementar `scripts/normalize_results.py`
  - Carregar 3 JSONs: `security.json`, `design.json`, `code.json`
  - Merge findings em lista única
  - Deduplicate por (file, line, category)
  - Sort por severity: critical > high > medium > low
  - Gerar `reviewResult.json` (formato canônico)

- [ ] **4.2** Implementar `scripts/utils/finding_deduplicator.py`
  - Hash de findings: `hash(file + line + category)`
  - Lógica de similaridade (Levenshtein distance para descrições)
  - Se similaridade > 80%, considerar duplicata

- [ ] **4.3** Adicionar step no pipeline
  ```yaml
  - script: python scripts/normalize_results.py --input-dir findings/ --output reviewResult.json
  ```

**Critérios de Aceitação:**
- ✅ `reviewResult.json` contém findings únicos
- ✅ Ordenação correta por severidade
- ✅ Summary counts corretos (critical, high, medium, low)

---

## 📤 FASE 5: PR Publisher (2 dias)

**Objetivo:** Publicar comentários no Azure DevOps PR

### Tasks

- [ ] **5.1** Implementar `scripts/utils/azure_devops_client.py`
  - Classe `AzureDevOpsClient(org, project, token)`
  - Método `create_pr_thread(repo_id, pr_id, content, thread_context=None)`
  - Autenticação: `Basic` com PAT (base64)
  - Retry com backoff exponencial (tenacity)
  - Error handling: rate limit (429), auth (401, 403)
  - API version: `7.1`

- [ ] **5.2** Implementar templates Jinja2
  - `scripts/templates/summary.md.jinja2`
    - Resumo dos 3 agents (Sentinel/Atlas/Forge)
    - Counts por severidade
    - Info do threshold configurado
  - `scripts/templates/finding.md.jinja2`
    - Emoji do agent (🛡️/🎨/🧠)
    - Severity, File, Line
    - Description, Exploit Scenario, Recommendation
    - Links para OWASP, regras do projeto

- [ ] **5.3** Implementar `scripts/publish_to_pr.py`
  - Argumento `--inline-threshold` (critical/high/medium/all)
  - Lógica de threshold:
    ```python
    severity_levels = {
      'critical': ['critical'],
      'high': ['critical', 'high'],
      'medium': ['critical', 'high', 'medium'],
      'all': ['critical', 'high', 'medium', 'low']
    }
    ```
  - Renderizar templates com Jinja2
  - Criar summary thread (top-level, sem thread_context)
  - Criar inline threads (com thread_context: filePath, line)

- [ ] **5.4** Adicionar step final no pipeline
  ```yaml
  - script: |
      python scripts/publish_to_pr.py \
        --review-file reviewResult.json \
        --pr-id $(System.PullRequest.PullRequestId) \
        --org $(System.CollectionUri) \
        --project $(System.TeamProject) \
        --repo $(Build.Repository.ID) \
        --inline-threshold $(INLINE_SEVERITY_THRESHOLD)
    env:
      AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)
  ```

- [ ] **5.5** Testar publicação em PR de desenvolvimento
  - Testar threshold: `critical`, `high`, `medium`, `all`
  - Verificar summary thread aparece
  - Verificar inline comments nos arquivos corretos
  - Verificar links para linhas de código funcionam

**Critérios de Aceitação:**
- ✅ Summary thread aparece no PR com info do threshold
- ✅ Inline comments respeitam threshold configurado
- ✅ Links para linhas de código funcionam
- ✅ Markdown renderizado corretamente
- ✅ Documentação explica como customizar threshold

---

## 📚 FASE 6: Polish e Documentação (1 dia)

**Objetivo:** Finalizar MVP

### Tasks

- [ ] **6.1** Criar `README.md`
  - Descrição do projeto
  - Como funciona (diagrama arquitetura)
  - Setup (Azure DevOps, permissions, secrets)
  - Configuração de `INLINE_SEVERITY_THRESHOLD`
  - Screenshots (exemplo de PR comentado)
  - FAQ

- [ ] **6.2** Criar `docs/ARCHITECTURE.md`
  - Copiar plano técnico completo
  - Adicionar diagramas (Mermaid ou ASCII)
  - Decisões arquiteturais detalhadas
  - Trade-offs e riscos

- [ ] **6.3** Criar `docs/DEPLOYMENT.md`
  - Setup passo-a-passo:
    1. Configurar Variable Group
    2. Adicionar ANTHROPIC_API_KEY
    3. Conceder permissões Build Service
    4. Configurar Branch Policy
    5. Testar em PR de dev
  - Troubleshooting (erros comuns)
  - Rollback procedure

- [ ] **6.4** Adicionar logs estruturados
  ```python
  import logging
  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )
  logger = logging.getLogger(__name__)
  logger.info(f"✅ Security review completed: {len(findings)} findings")
  ```

- [ ] **6.5** Code review final
  - Executar `pragmatic-code-review-subagent` no próprio código
  - Corrigir issues críticos identificados
  - Validar que não há secrets hardcoded

**Critérios de Aceitação:**
- ✅ README claro e conciso
- ✅ Documentação técnica completa
- ✅ Logs ajudam debugging
- ✅ Code review não identifica issues críticos

---

## ✅ CHECKLIST DE DEPLOY

### Pré-Produção
- [ ] Azure DevOps Variable Group criado
- [ ] ANTHROPIC_API_KEY adicionado (Secret)
- [ ] INLINE_SEVERITY_THRESHOLD configurado (default: `high`)
- [ ] Build Service com permissão `Contribute to Pull Requests`
- [ ] Branch Policy configurado (Build Validation para PRs)
- [ ] Pipeline testado em branch de dev
- [ ] Documentar como usuários podem customizar INLINE_SEVERITY_THRESHOLD

### Produção
- [ ] README.md atualizado (incluindo configuração de threshold)
- [ ] docs/ completo
- [ ] Merge para `main`
- [ ] Tag de release (v1.0.0)
- [ ] Monitoramento ativado (Azure Pipeline logs)
- [ ] Comunicar time sobre nova feature

---

## 📊 MÉTRICAS DE SUCESSO (MVP)

- ✅ Pipeline executa em 100% dos PRs (cobertura)
- ✅ < 2 minutos de latência média
- ✅ ≥ 80% de precisão (vulnerabilidades confirmadas / total reportado)
- ✅ Zero vazamento de secrets em logs

---

## 🔮 ROADMAP FUTURO

### V2.0 (Q2 2025)
- Dashboard web (React + TypeScript)
- Persistência em PostgreSQL
- Métricas e analytics
- API REST de consulta
- Alertas em Slack/Teams
- **Esforço:** ~4 semanas

### V3.0 (Q3 2025)
- Fine-tuning de agents com exemplos do projeto
- Modo "auto-fix" (gera PRs de correção)
- Integração com SonarQube/Checkmarx
- Suporte multi-repo
- **Esforço:** ~6 semanas

---

## 📝 NOTAS E DECISÕES

### Decisão: Python vs Node.js vs Java
**Escolhido:** Python (MVP)
- ✅ Rápido para iteração
- ✅ SDK oficial Anthropic
- ✅ Fácil parsing markdown
- ⚠️ Stack diferente do backend (Java 21)
- 🔄 V2 pode migrar para Node.js/Java se necessário

### Decisão: Sequencial vs Paralelo (Agents)
**Escolhido:** Sequencial (MVP)
- ✅ Simples de implementar
- ✅ Evita rate limit Claude API
- ⚠️ ~90s total (3 agents × 30s)
- 🔄 V2 pode paralelizar com `asyncio`

### Decisão: Markdown Parsing vs Structured Output
**Escolhido:** Markdown parsing (MVP)
- ✅ Agents já retornam markdown
- ✅ Sem refactor dos agents
- ⚠️ Parsing com regex frágil
- 🔄 V2: migrar para Claude Structured Output

---

## 🚨 RISCOS IDENTIFICADOS

1. **Claude API Rate Limit** (Probabilidade: Média, Impacto: Alto)
   - Mitigação: Retry + backoff, tier pago, queue (V2)

2. **Parsing de Markdown Frágil** (Probabilidade: Alta, Impacto: Médio)
   - Mitigação: AST parser, fallback para markdown raw, testes unitários

3. **Secrets Vazados em Logs** (Probabilidade: Baixa, Impacto: Crítico)
   - Mitigação: Sanitizar diff, nunca logar API keys, code review rigoroso

---

## 📞 CONTATO E SUPORTE

**Documentação Completa:** [/Users/premiersoft/.claude/plans/curried-kindling-parasol.md](file:///Users/premiersoft/.claude/plans/curried-kindling-parasol.md)

**Última Atualização:** 2025-12-30

---

**🎯 Próximos Passos:** Iniciar FASE 1 - Setup Básico
