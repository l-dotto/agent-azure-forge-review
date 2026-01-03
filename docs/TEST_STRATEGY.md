# Test Strategy & Roadmap - Azure Code Reviewer

**Versão:** 1.0
**Data:** 2026-01-03
**Relacionado:** [TEST_PLAN.md](TEST_PLAN.md) | [TEST_CASES.md](TEST_CASES.md)

---

## 1. VISÃO EXECUTIVA

### 1.1 Objetivo

Garantir que o sistema Azure Code Reviewer seja:
- **Confiável:** Funciona consistentemente sem falhas
- **Seguro:** Protege secrets e previne vulnerabilidades
- **Performático:** Completa reviews em < 2 minutos
- **Manutenível:** Testes servem como documentação

### 1.2 Filosofia de Testes

**Princípios:**
1. **Testes como Especificação:** Cada teste documenta comportamento esperado
2. **Fail Fast:** Detectar erros o mais cedo possível
3. **Automação Total:** Zero testes manuais repetitivos
4. **Feedback Rápido:** Suite completa em < 5 minutos
5. **Confiança para Deploy:** 100% dos testes passando = deploy seguro

---

## 2. ROADMAP DE IMPLEMENTAÇÃO

### Fase 1: Foundation (Semana 1)

**Objetivo:** Setup de infraestrutura de testes

**Tasks:**
- [ ] Configurar pytest com plugins essenciais
- [ ] Criar estrutura de diretórios de testes
- [ ] Implementar fixtures compartilhadas
- [ ] Configurar coverage reporting
- [ ] Setup CI/CD para testes automáticos

**Entregáveis:**
```bash
tests/
├── conftest.py              # Fixtures globais
├── pytest.ini               # Configuração pytest
├── fixtures/                # Dados de teste
│   ├── diffs/
│   ├── markdown_outputs/
│   └── json_results/
├── helpers/                 # Funções auxiliares
│   ├── generators.py        # Geração de dados de teste
│   └── assertions.py        # Assertions customizadas
└── __init__.py
```

**Critérios de Aceitação:**
- [ ] `pytest` executa sem erros
- [ ] Coverage report gerado corretamente
- [ ] CI/CD rodando testes automaticamente

---

### Fase 2: Testes Unitários Críticos (Semana 1-2)

**Objetivo:** Cobrir componentes core com testes unitários

**Prioridades:**

#### 2.1 Alta Prioridade (Crítico)
- [ ] `test_git_diff_parser.py` (10 casos)
  - Parsing de diff válido
  - Sanitização de secrets (API keys, CPF, senhas)
  - Path traversal protection
  - Caracteres especiais e Unicode

- [ ] `test_markdown_parser.py` (8 casos)
  - Parse de findings bem formatados
  - Múltiplos findings
  - Markdown malformado
  - Extração de metadata

- [ ] `test_finding_deduplicator.py` (6 casos)
  - Deduplicação de duplicatas exatas
  - Similaridade por threshold
  - Merge de metadata (múltiplos agents)

**Entregável:** 24 testes unitários passando

#### 2.2 Média Prioridade
- [ ] `test_llm_client.py` (8 casos)
  - Chamadas bem-sucedidas
  - Retry em rate limit
  - Timeout handling
  - Usage tracking

- [ ] `test_run_security_review.py` (10 casos)
  - Initialization
  - Prompt loading
  - Git command execution
  - Finding generation

**Entregável:** +18 testes (total: 42)

---

### Fase 3: Testes de Integração (Semana 2)

**Objetivo:** Validar interação entre componentes

**Componentes:**

- [ ] **Diff → LLM → Findings** (TC-I-001)
  - Flow completo de parsing
  - Validação de findings estruturados

- [ ] **Multi-Agent Deduplication** (TC-I-002)
  - 3 agents encontrando mesma vuln
  - Consolidação correta

- [ ] **Publisher → Azure DevOps** (TC-I-003)
  - Criação de threads
  - Threshold filtering
  - Template rendering

**Entregável:** 10 testes de integração

**Notas:**
- Usar VCR.py para gravação de requests HTTP
- Mock Azure DevOps em ambiente de teste
- Fixtures realistas de findings

---

### Fase 4: Testes de Segurança (Semana 2-3)

**Objetivo:** Garantir proteções de segurança

**Áreas Críticas:**

#### 4.1 Secret Sanitization
- [ ] API keys (Anthropic, OpenAI, Azure)
- [ ] Passwords e tokens
- [ ] CPF, cartões de crédito
- [ ] Dados sensíveis em logs

**Casos de Teste:**
```python
TC-S-001: Path traversal protection
TC-S-002: Command injection prevention
TC-S-003: Secrets not in logs
TC-S-004: API key sanitization
TC-S-005: CPF sanitization
TC-S-006: SQL injection detection
TC-S-007: XSS detection
```

**Entregável:** 10+ testes de segurança passando

#### 4.2 Validação de Inputs
- [ ] Validação de file paths
- [ ] Validação de comandos git
- [ ] Sanitização de diffs
- [ ] Escape de caracteres especiais

---

### Fase 5: Testes E2E (Semana 3)

**Objetivo:** Validar fluxo completo do sistema

**Cenários:**

- [ ] **TC-E2E-001:** PR com vulnerabilidades → findings publicados
- [ ] **TC-E2E-002:** PR vazio → summary "no changes"
- [ ] **TC-E2E-003:** Threshold filtering (critical vs all)
- [ ] **TC-E2E-004:** Multi-file PR → inline comments corretos
- [ ] **TC-E2E-005:** Pipeline completo → verificar artifacts

**Setup:**
- Docker Compose para ambiente isolado
- Mock PR em repositório de teste
- Validação de comentários no Azure DevOps

**Entregável:** 5 testes E2E

**Nota:** Testes E2E são lentos (~30s cada), executar separadamente

---

### Fase 6: Performance & Load Testing (Semana 3)

**Objetivo:** Garantir performance dentro dos limites

**Benchmarks:**

| Componente | Threshold | Métrica |
|-----------|-----------|---------|
| Diff parsing | < 2s | 50 arquivos, 5000 linhas |
| Security review | < 45s | Diff realista |
| Design review | < 45s | Diff realista |
| Code review | < 60s | Diff realista |
| Normalização | < 1s | 100 findings |
| Publish | < 5s | 20 threads |
| **Total** | **< 120s** | Review completo |

**Casos de Teste:**
```python
TC-P-001: Diff parsing performance
TC-P-002: Security review performance
TC-P-003: Complete review performance
TC-P-004: Concurrent reviews (5 PRs)
TC-P-005: Large PR (100 files)
```

**Entregável:** 5 testes de performance + relatório de benchmarks

---

### Fase 7: Polish & Documentation (Semana 4)

**Objetivo:** Finalizar documentação e automação

**Tasks:**
- [ ] Documentar todos os test cases
- [ ] Criar guia de contribuição para testes
- [ ] Setup de mutation testing (Mutmut)
- [ ] Configurar test coverage gates no CI
- [ ] Criar dashboard de métricas de qualidade

**Entregáveis:**
- [ ] README de testes
- [ ] Guia de debugging
- [ ] CI/CD com gates de qualidade
- [ ] Coverage report automatizado

---

## 3. AUTOMAÇÃO CI/CD

### 3.1 Pipeline de Testes

```yaml
# azure-pipelines-test.yml

trigger:
  branches:
    include:
      - main
      - develop
      - feature/*

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: FastTests
    displayName: 'Fast Tests (< 2 min)'
    jobs:
      - job: UnitTests
        displayName: 'Unit Tests'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'

          - script: |
              pip install -r requirements.txt
              pip install pytest pytest-cov pytest-xdist
            displayName: 'Install dependencies'

          - script: |
              pytest tests/unit -v -n auto --cov=scripts --cov-report=xml
            displayName: 'Run unit tests (parallel)'

          - task: PublishCodeCoverageResults@1
            inputs:
              codeCoverageTool: 'Cobertura'
              summaryFileLocation: 'coverage.xml'

      - job: SecurityTests
        displayName: 'Security Tests'
        steps:
          - script: |
              pytest tests/ -v -m security
            displayName: 'Run security tests'

  - stage: SlowTests
    displayName: 'Slow Tests (< 5 min)'
    dependsOn: FastTests
    jobs:
      - job: IntegrationTests
        displayName: 'Integration Tests'
        steps:
          - script: |
              pytest tests/integration -v -m integration
            displayName: 'Run integration tests'

      - job: PerformanceTests
        displayName: 'Performance Tests'
        steps:
          - script: |
              pytest tests/ -v -m performance
            displayName: 'Run performance tests'

  - stage: QualityGates
    displayName: 'Quality Gates'
    dependsOn: [FastTests, SlowTests]
    jobs:
      - job: CoverageGate
        displayName: 'Coverage Gate (min 80%)'
        steps:
          - script: |
              coverage report --fail-under=80
            displayName: 'Verify coverage >= 80%'

      - job: LintGate
        displayName: 'Lint Gate'
        steps:
          - script: |
              flake8 scripts/ --max-line-length=120
              mypy scripts/ --ignore-missing-imports
            displayName: 'Run linters'
```

### 3.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit -v --tb=short
        language: system
        pass_filenames: false
        always_run: true

      - id: pytest-security
        name: Run security tests
        entry: pytest tests/ -v -m security --tb=short
        language: system
        pass_filenames: false
        always_run: true

      - id: coverage-check
        name: Check test coverage
        entry: bash -c 'pytest --cov=scripts --cov-report=term-missing --cov-fail-under=80'
        language: system
        pass_filenames: false
        always_run: true
```

---

## 4. MÉTRICAS E KPIs

### 4.1 Métricas de Qualidade

**Cobertura:**
- **Objetivo:** ≥ 80% cobertura total
- **Crítico:** ≥ 95% em componentes críticos
- **Tracking:** Coverage report em cada PR

**Flakiness:**
- **Objetivo:** 0% testes flaky
- **Métrica:** Mesmos testes passam 100x consecutivas
- **Tracking:** `pytest --count=100`

**Performance:**
- **Objetivo:** Suite completa em < 5 min
- **Tracking:** CI pipeline duration

### 4.2 Dashboard de Métricas

**Ferramentas:**
- SonarQube (análise estática + coverage)
- Azure DevOps Test Analytics
- Custom dashboard (opcional)

**Métricas Rastreadas:**
- Coverage trend (linha de tendência)
- Test execution time
- Flaky test detection
- Test failure rate
- Code quality score

---

## 5. ESTRATÉGIA DE DEBUGGING

### 5.1 Debugging Local

**Comandos Úteis:**

```bash
# Debug teste específico
pytest tests/unit/test_parser.py::test_parse_markdown -vv -s --pdb

# Executar com logs detalhados
pytest -vv -s --log-cli-level=DEBUG

# Parar no primeiro erro
pytest -x

# Re-executar últimos failed
pytest --lf

# Executar com coverage e mostrar missing
pytest --cov=scripts --cov-report=term-missing
```

### 5.2 Debugging em CI

**Estratégias:**

1. **Aumentar verbosidade:**
```yaml
- script: pytest -vv -s --tb=long
```

2. **Coletar artifacts:**
```yaml
- task: PublishTestResults@2
  inputs:
    testResultsFiles: '**/test-results.xml'

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'htmlcov'
    artifactName: 'coverage-report'
```

3. **Logs estruturados:**
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 6. MANUTENÇÃO DE TESTES

### 6.1 Revisão Periódica

**Mensal:**
- [ ] Revisar testes flaky
- [ ] Atualizar fixtures para refletir código atual
- [ ] Remover testes obsoletos
- [ ] Adicionar testes para novos bugs encontrados

**Trimestral:**
- [ ] Refactor de testes duplicados
- [ ] Otimizar testes lentos
- [ ] Atualizar documentação de testes
- [ ] Revisar cobertura de áreas críticas

### 6.2 Cultura de Testes

**Práticas:**
1. **Testes com código:** Todo PR inclui testes
2. **TDD quando possível:** Escrever teste antes do código
3. **Code review de testes:** Revisar qualidade dos testes
4. **Documentation:** Testes como documentação viva

**Checklist de PR:**
- [ ] Testes unitários adicionados
- [ ] Coverage não diminuiu
- [ ] Testes passando no CI
- [ ] Testes documentados (docstrings)

---

## 7. RISCOS E MITIGAÇÕES

### 7.1 Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Testes flaky | Média | Alto | Mock external deps, fixtures determinísticas |
| Suite lenta (> 5 min) | Alta | Médio | Paralelização (pytest-xdist), otimizar fixtures |
| Coverage baixa | Média | Alto | Gates no CI, code review rigoroso |
| Testes desatualizados | Média | Médio | Revisão mensal, refactor contínuo |
| Secrets vazados em tests | Baixa | Crítico | Usar mock keys, nunca commit secrets |

### 7.2 Plano de Contingência

**Se coverage < 80%:**
1. Identificar componentes sem cobertura
2. Priorizar testes para áreas críticas
3. Block merges até coverage >= 80%

**Se suite > 5 min:**
1. Profile testes lentos (`pytest --durations=10`)
2. Paralelizar com `pytest-xdist`
3. Mover testes E2E para pipeline separado

---

## 8. PRÓXIMOS PASSOS

### Imediato (Esta Semana)
- [ ] Configurar pytest e estrutura de testes
- [ ] Implementar primeiros 10 testes unitários
- [ ] Setup CI/CD com coverage reporting

### Curto Prazo (2 Semanas)
- [ ] Completar testes unitários críticos (42 testes)
- [ ] Implementar testes de integração (10 testes)
- [ ] Adicionar testes de segurança (10 testes)
- [ ] Atingir 80% de cobertura

### Médio Prazo (1 Mês)
- [ ] Adicionar testes E2E (5 testes)
- [ ] Performance benchmarks
- [ ] Mutation testing setup
- [ ] Documentation completa

### Longo Prazo (3+ Meses)
- [ ] Property-based testing (Hypothesis)
- [ ] Chaos engineering tests
- [ ] Visual regression testing
- [ ] Contract testing

---

## 9. RECURSOS E REFERÊNCIAS

### 9.1 Ferramentas

**Testing:**
- [pytest](https://docs.pytest.org/) - Framework principal
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage
- [pytest-xdist](https://pytest-xdist.readthedocs.io/) - Paralelização
- [pytest-mock](https://pytest-mock.readthedocs.io/) - Mocking
- [VCR.py](https://vcrpy.readthedocs.io/) - HTTP recording

**Quality:**
- [SonarQube](https://www.sonarqube.org/) - Análise estática
- [Mutmut](https://mutmut.readthedocs.io/) - Mutation testing
- [Hypothesis](https://hypothesis.readthedocs.io/) - Property testing

### 9.2 Leitura Recomendada

**Livros:**
- "Python Testing with pytest" - Brian Okken
- "Test Driven Development" - Kent Beck
- "Growing Object-Oriented Software, Guided by Tests" - Freeman & Pryce

**Artigos:**
- [Google Testing Blog](https://testing.googleblog.com/)
- [Martin Fowler - Testing](https://martinfowler.com/tags/testing.html)
- [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

---

## 10. GLOSSÁRIO

**Coverage:** Percentual de código executado pelos testes
**Flaky Test:** Teste que falha intermitentemente
**Fixture:** Dados ou setup compartilhado entre testes
**Mock:** Objeto fake que simula comportamento real
**TDD:** Test-Driven Development (teste antes do código)
**E2E:** End-to-End (teste completo do sistema)
**CI/CD:** Continuous Integration / Continuous Deployment
**VCR:** Video Cassette Recorder (grava requests HTTP)
**Mutation Testing:** Valida qualidade dos testes alterando código

---

**Última Atualização:** 2026-01-03
**Versão:** 1.0
**Responsável:** Engineering Team
**Status:** Em Vigor
