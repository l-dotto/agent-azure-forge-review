# Test Plan - Azure Code Reviewer

**Versão:** 1.0
**Data:** 2026-01-03
**Autor:** Engineering Team
**Status:** Em Vigor

---

## 1. VISÃO GERAL

### 1.1 Objetivo

Este plano define a estratégia completa de testes para o sistema Azure Code Reviewer, garantindo:

- **Qualidade:** Código testado em múltiplos níveis (unitário, integração, E2E)
- **Confiabilidade:** Sistema robusto com cobertura > 80%
- **Segurança:** Validação de sanitização e proteção de secrets
- **Performance:** Latência < 2 min por review completo
- **Manutenibilidade:** Testes documentados e facilmente executáveis

### 1.2 Escopo

**Inclui:**
- Testes unitários (componentes isolados)
- Testes de integração (interação entre componentes)
- Testes end-to-end (fluxo completo de review)
- Testes de segurança (sanitização, validação)
- Testes de performance (latência, throughput)
- Testes de regressão (CI/CD)

**Exclui:**
- Testes de carga extrema (1000+ PRs simultâneos)
- Testes de penetração profundos (fora do escopo MVP)
- Testes manuais de UX (Azure DevOps UI)

### 1.3 Princípios

1. **Automação First:** Todo teste deve ser automatizável
2. **Fast Feedback:** Suite completa em < 5 minutos
3. **Determinístico:** Mesma entrada = mesma saída (sem flakiness)
4. **Isolado:** Testes independentes (ordem não importa)
5. **Legível:** Testes como documentação viva

---

## 2. PIRÂMIDE DE TESTES

```
                    /\
                   /  \
                  / E2E \          (10% - 5 testes)
                 /______\
                /        \
               /Integration\       (30% - 20 testes)
              /____________\
             /              \
            /   Unit Tests   \    (60% - 50+ testes)
           /__________________\
```

**Distribuição:**
- **Unit Tests:** 60% (~50 testes) - Componentes isolados
- **Integration:** 30% (~20 testes) - Interação entre componentes
- **End-to-End:** 10% (~5 testes) - Fluxo completo

---

## 3. NÍVEIS DE TESTE

### 3.1 Testes Unitários (60%)

**Objetivo:** Testar componentes isolados com mocks

**Ferramentas:**
- `pytest` - Framework principal
- `pytest-mock` - Mocking
- `pytest-cov` - Cobertura
- `unittest.mock` - Mock objects

**Componentes Críticos:**

#### 3.1.1 Git Diff Parser (`test_git_diff_parser.py`)

```python
class TestGitDiffParser:
    """Test suite for GitDiffParser"""

    # Funcionalidades a testar:
    - ✅ get_pr_diff() retorna DiffResult válido
    - ✅ Sanitização de secrets (API keys, passwords, CPF)
    - ✅ Parsing de arquivos modificados
    - ✅ Contagem de additions/deletions
    - ✅ Handling de diff vazio (sem mudanças)
    - ✅ Handling de diff binário
    - ✅ Escape de caracteres especiais
    - ✅ Validação de path traversal
```

**Casos de Teste:**
- ✅ Diff válido com múltiplos arquivos
- ✅ Diff com secret (deve sanitizar)
- ✅ Diff vazio (0 mudanças)
- ✅ Diff binário (imagens, PDFs)
- ✅ Path traversal attempt (../../../etc/passwd)
- ✅ Caracteres Unicode no diff

#### 3.1.2 Markdown Parser (`test_markdown_parser.py`)

```python
class TestMarkdownParser:
    """Test suite for Markdown Parser"""

    # Funcionalidades a testar:
    - ✅ parse_agent_output() extrai findings corretamente
    - ✅ Parse de severidade (critical, high, medium, low)
    - ✅ Extração de file path e line number
    - ✅ Handling de markdown malformado
    - ✅ Múltiplos findings no mesmo output
    - ✅ Findings sem file/line (warnings gerais)
```

**Casos de Teste:**
- ✅ Output bem formatado (formato esperado)
- ✅ Output com markdown malformado
- ✅ Múltiplos findings (diferentes severidades)
- ✅ Finding sem file/line
- ✅ Markdown com código embutido
- ✅ Caracteres especiais em descrição

#### 3.1.3 LLM Client (`test_llm_client.py`)

```python
class TestLLMClient:
    """Test suite for LLM Client"""

    # Funcionalidades a testar:
    - ✅ create_llm_client() para cada provider
    - ✅ generate() retorna LLMResponse válido
    - ✅ Retry com backoff (rate limit)
    - ✅ Handling de timeout
    - ✅ Validação de API key
    - ✅ Tracking de usage (tokens)
```

**Casos de Teste:**
- ✅ Anthropic client (provider padrão)
- ✅ OpenAI client (provider alternativo)
- ✅ Rate limit (429) → retry com backoff
- ✅ Timeout → retry até max_retries
- ✅ API key inválida → erro claro
- ✅ Usage tracking (input/output tokens)

#### 3.1.4 Finding Deduplicator (`test_finding_deduplicator.py`)

```python
class TestFindingDeduplicator:
    """Test suite for Finding Deduplicator"""

    # Funcionalidades a testar:
    - ✅ deduplicate() remove duplicatas exatas
    - ✅ Similaridade > threshold → merge
    - ✅ Hash baseado em (file, line, category)
    - ✅ Tracking de múltiplos agents
    - ✅ Merge de confidence scores
```

**Casos de Teste:**
- ✅ 2 findings idênticos → 1 finding
- ✅ Similaridade 85% → merge
- ✅ Similaridade 60% → manter separados
- ✅ 3 agents encontraram mesmo issue → metadata correta
- ✅ Diferentes categorias, mesma linha → manter separados

#### 3.1.5 Azure DevOps Client (`test_azure_devops_client.py`)

```python
class TestAzureDevOpsClient:
    """Test suite for Azure DevOps API Client"""

    # Funcionalidades a testar:
    - ✅ create_pr_thread() cria thread no PR
    - ✅ create_pr_thread() com thread_context (inline)
    - ✅ Autenticação com PAT
    - ✅ Retry com backoff (rate limit)
    - ✅ Handling de erros (401, 403, 404, 429)
```

**Casos de Teste:**
- ✅ Create summary thread (sem thread_context)
- ✅ Create inline thread (com file/line)
- ✅ Autenticação válida → 200 OK
- ✅ PAT inválido → 401 Unauthorized
- ✅ Rate limit (429) → retry automático
- ✅ PR não existe → 404 Not Found

#### 3.1.6 Agent Runners

**Security Review Runner** (`test_run_security_review.py`)

```python
class TestSecurityReviewRunner:
    """Test suite for Security Review Runner"""

    # Funcionalidades a testar:
    - ✅ Initialization com defaults
    - ✅ Initialization com custom provider
    - ✅ _load_agent_prompt() remove frontmatter
    - ✅ _execute_git_command() valida whitelist
    - ✅ _substitute_placeholders() substitui !`cmd`
    - ✅ _call_llm() chama API corretamente
    - ✅ run() retorna estrutura esperada
    - ✅ run() com diff vazio → 0 findings
    - ✅ run() com vulnerabilidades → findings corretos
```

**Code Review Runner** (`test_run_code_review.py`)

```python
class TestCodeReviewRunner:
    """Test suite for Code Review Runner"""

    # Similar ao Security, mas:
    - ✅ Model padrão: claude-opus-4-5-20251101
    - ✅ Parse de categorias (Critical/Improvements/Nits)
    - ✅ Agent metadata correto (forge)
```

#### 3.1.7 Normalizer (`test_normalize_results.py`)

```python
class TestNormalizer:
    """Test suite for Result Normalizer"""

    # Funcionalidades a testar:
    - ✅ normalize_results() merge 3 JSONs
    - ✅ Deduplicação de findings
    - ✅ Ordenação por severity (critical → low)
    - ✅ Summary counts corretos
    - ✅ Metadata com timestamp
```

**Casos de Teste:**
- ✅ 3 JSONs válidos → merge correto
- ✅ Duplicatas entre agents → deduplicadas
- ✅ Ordenação por severity → critical no topo
- ✅ Summary counts → totais corretos
- ✅ Metadata → timestamp e stats

#### 3.1.8 PR Publisher (`test_publish_to_pr.py`)

```python
class TestPRPublisher:
    """Test suite for PR Publisher"""

    # Funcionalidades a testar:
    - ✅ publish_to_pr() cria threads corretos
    - ✅ Threshold filtering (critical/high/medium/all)
    - ✅ Template rendering (Jinja2)
    - ✅ Summary thread criado
    - ✅ Inline threads criados (respeitando threshold)
```

**Casos de Teste:**
- ✅ Threshold 'critical' → só critical inline
- ✅ Threshold 'all' → todos inline
- ✅ Template rendering → markdown válido
- ✅ Summary thread → info correta
- ✅ Inline threads → file/line corretos

---

### 3.2 Testes de Integração (30%)

**Objetivo:** Testar interação entre componentes reais

**Ferramentas:**
- `pytest` com fixtures compartilhadas
- `pytest-integration` marker
- Docker Compose (mock services)

**Cenários Críticos:**

#### 3.2.1 Parser + LLM + Findings

```python
class TestParserLLMIntegration:
    """Test integration between Diff Parser → LLM → Markdown Parser"""

    @pytest.mark.integration
    def test_diff_to_findings_flow(self):
        """Test complete flow: diff → LLM → findings"""
        # 1. Parse diff real (fixture)
        # 2. Call LLM API (mock ou real com VCR)
        # 3. Parse markdown output
        # 4. Verificar findings estruturados
```

**Casos de Teste:**
- Diff com SQL injection → LLM detecta → finding correto
- Diff com XSS → LLM detecta → finding correto
- Diff limpo → LLM retorna "no issues" → 0 findings

#### 3.2.2 Normalizer + Deduplicator

```python
class TestNormalizerDeduplicatorIntegration:
    """Test integration between multiple agents and deduplication"""

    @pytest.mark.integration
    def test_multi_agent_deduplication(self):
        """Test deduplication across 3 agents"""
        # 1. Gerar findings de 3 agents (fixtures reais)
        # 2. Normalizar com deduplicação
        # 3. Verificar merge correto
```

**Casos de Teste:**
- 3 agents encontram mesma vuln → 1 finding com metadata
- 2 agents encontram issues diferentes → 2 findings
- Overlapping categories → correta categorização

#### 3.2.3 Publisher + Azure DevOps

```python
class TestPublisherAzureDevOpsIntegration:
    """Test integration with Azure DevOps API"""

    @pytest.mark.integration
    @pytest.mark.skipif("not config.getoption('--run-azure')")
    def test_publish_to_real_pr(self):
        """Test publishing to real PR (requires Azure setup)"""
        # 1. Criar PR de teste
        # 2. Publicar findings
        # 3. Verificar threads criados
        # 4. Cleanup
```

**Casos de Teste:**
- Publish summary thread → verificar criado
- Publish inline threads → verificar file/line corretos
- Threshold filtering → verificar só esperados criados

---

### 3.3 Testes End-to-End (10%)

**Objetivo:** Testar fluxo completo do sistema

**Ferramentas:**
- `pytest-e2e` marker
- Docker Compose (ambiente isolado)
- Mock Azure Pipeline

**Cenários Críticos:**

#### 3.3.1 Fluxo Completo de Review

```python
class TestE2ECodeReview:
    """End-to-end test for complete code review flow"""

    @pytest.mark.e2e
    def test_complete_review_flow(self):
        """Test: PR created → agents run → findings published"""
        # 1. Setup: Mock PR com código vulnerável
        # 2. Execute: Run all 3 agents
        # 3. Normalize: Merge findings
        # 4. Publish: Create threads
        # 5. Verify: Check Azure DevOps PR
```

**Casos de Teste:**
- ✅ PR com vulnerabilidades → findings publicados
- ✅ PR limpo → summary "no issues" publicado
- ✅ Threshold configurado → respeitado

#### 3.3.2 Pipeline Completo

```python
class TestE2EPipeline:
    """End-to-end test for Azure Pipeline"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_azure_pipeline_execution(self):
        """Test complete Azure Pipeline execution"""
        # 1. Trigger pipeline
        # 2. Monitor execution
        # 3. Verify artifacts
        # 4. Verify PR comments
```

---

## 4. TESTES DE SEGURANÇA

### 4.1 Sanitização de Secrets

**Objetivo:** Garantir que secrets não vazam

**Componentes Testados:**
- `GitDiffParser` - Sanitização de diffs
- `LLMClient` - Não logar API keys
- `AzureDevOpsClient` - Não logar PATs

**Casos de Teste:**

```python
class TestSecretSanitization:
    """Test secret sanitization across system"""

    def test_api_key_sanitization(self):
        """Test API keys are sanitized in diffs"""
        diff = "API_KEY=sk-1234567890abcdef"
        result = sanitize_diff(diff)
        assert "sk-1234567890abcdef" not in result
        assert "***REDACTED***" in result

    def test_password_sanitization(self):
        """Test passwords are sanitized"""
        diff = 'password = "mySecretPass123"'
        result = sanitize_diff(diff)
        assert "mySecretPass123" not in result

    def test_cpf_sanitization(self):
        """Test CPF numbers are sanitized"""
        diff = "cpf: 123.456.789-00"
        result = sanitize_diff(diff)
        assert "123.456.789-00" not in result

    def test_credit_card_sanitization(self):
        """Test credit card numbers are sanitized"""
        diff = "card: 4532-1234-5678-9010"
        result = sanitize_diff(diff)
        assert "4532-1234-5678-9010" not in result
```

### 4.2 Path Traversal

**Objetivo:** Prevenir path traversal attacks

```python
class TestPathTraversalProtection:
    """Test path traversal protection"""

    def test_path_traversal_blocked(self):
        """Test path traversal attempts are blocked"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
            "%2e%2e%2f",
        ]
        for path in malicious_paths:
            with pytest.raises(SecurityError):
                validate_file_path(path)
```

### 4.3 Injection Attacks

**Objetivo:** Prevenir command injection e code injection

```python
class TestInjectionProtection:
    """Test injection attack protection"""

    def test_command_injection_blocked(self):
        """Test command injection in git commands"""
        malicious_cmd = "git status; rm -rf /"
        with pytest.raises(SecurityError):
            execute_git_command(malicious_cmd)

    def test_sql_injection_detection(self):
        """Test SQL injection is detected by agents"""
        vulnerable_code = '''
        query = f"SELECT * FROM users WHERE id = {user_id}"
        db.execute(query)
        '''
        findings = run_security_review(vulnerable_code)
        assert any(f.category == 'sql_injection' for f in findings)
```

---

## 5. TESTES DE PERFORMANCE

### 5.1 Latência

**Objetivo:** Garantir review completo < 2 minutos

**Métricas:**
- Diff parsing: < 2s
- Security review: < 45s
- Design review: < 45s
- Code review: < 60s (Opus mais lento)
- Normalização: < 1s
- Publish: < 5s
- **Total:** < 120s (2 min)

**Casos de Teste:**

```python
class TestPerformance:
    """Test performance requirements"""

    @pytest.mark.performance
    def test_diff_parsing_performance(self):
        """Test diff parsing completes in < 2s"""
        large_diff = generate_large_diff(files=50, lines=5000)
        start = time.time()
        result = parse_diff(large_diff)
        elapsed = time.time() - start
        assert elapsed < 2.0

    @pytest.mark.performance
    def test_security_review_performance(self):
        """Test security review completes in < 45s"""
        diff = generate_realistic_diff()
        start = time.time()
        findings = run_security_review(diff)
        elapsed = time.time() - start
        assert elapsed < 45.0

    @pytest.mark.performance
    def test_complete_review_performance(self):
        """Test complete review flow in < 120s"""
        start = time.time()
        run_complete_review()
        elapsed = time.time() - start
        assert elapsed < 120.0
```

### 5.2 Throughput

**Objetivo:** Suportar múltiplos PRs simultâneos

```python
class TestThroughput:
    """Test system throughput"""

    @pytest.mark.performance
    def test_concurrent_reviews(self):
        """Test 5 concurrent reviews complete successfully"""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_review) for _ in range(5)]
            results = [f.result() for f in futures]

        assert all(r['status'] == 'success' for r in results)
```

---

## 6. TESTES DE REGRESSÃO

### 6.1 CI/CD Integration

**Objetivo:** Executar testes automaticamente em cada commit

**Pipeline:**

```yaml
# .github/workflows/test.yml (ou azure-pipelines-test.yml)

stages:
  - stage: Test
    jobs:
      - job: UnitTests
        steps:
          - script: pytest tests/unit -v --cov=scripts --cov-report=xml
            displayName: 'Run unit tests'

      - job: IntegrationTests
        dependsOn: UnitTests
        steps:
          - script: pytest tests/integration -v -m integration
            displayName: 'Run integration tests'

      - job: SecurityTests
        steps:
          - script: pytest tests/ -v -m security
            displayName: 'Run security tests'

      - job: PerformanceTests
        steps:
          - script: pytest tests/ -v -m performance
            displayName: 'Run performance tests'

      - job: CoverageReport
        dependsOn: [UnitTests, IntegrationTests]
        steps:
          - script: |
              pytest --cov=scripts --cov-report=html
              coverage report --fail-under=80
            displayName: 'Generate coverage report (min 80%)'
```

### 6.2 Smoke Tests

**Objetivo:** Validação rápida pós-deploy

```python
class TestSmokeTests:
    """Smoke tests for post-deployment validation"""

    @pytest.mark.smoke
    def test_system_health(self):
        """Test system components are healthy"""
        assert validate_azure_connection() is True
        assert validate_llm_api_key() is True
        assert validate_git_repository() is True

    @pytest.mark.smoke
    def test_end_to_end_minimal(self):
        """Test minimal E2E flow works"""
        result = run_review_on_sample_pr()
        assert result['status'] == 'success'
        assert len(result['findings']) > 0
```

---

## 7. FIXTURES E DADOS DE TESTE

### 7.1 Fixtures Compartilhadas

**Arquivo:** `tests/conftest.py`

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_diff():
    """Sample git diff with vulnerabilities"""
    return Path('tests/fixtures/diffs/vulnerable_code.diff').read_text()

@pytest.fixture
def sample_security_findings():
    """Sample security findings JSON"""
    return {
        "findings": [
            {
                "agent": "sentinel",
                "severity": "high",
                "category": "sql_injection",
                "title": "SQL Injection",
                "file_path": "app.py",
                "line_number": 42,
                "description": "SQL injection vulnerability",
                "recommendation": "Use parameterized queries"
            }
        ],
        "metadata": {
            "agent": "sentinel",
            "total_findings": 1
        }
    }

@pytest.fixture
def mock_llm_client(mocker):
    """Mock LLM client"""
    mock = mocker.Mock()
    mock.generate.return_value = LLMResponse(
        content="# Vulnerability 1: SQL Injection",
        model="test-model",
        usage={"input_tokens": 100, "output_tokens": 50},
        provider="anthropic"
    )
    return mock

@pytest.fixture
def mock_azure_client(mocker):
    """Mock Azure DevOps client"""
    mock = mocker.Mock()
    mock.create_pr_thread.return_value = {"id": 123}
    return mock
```

### 7.2 Dados de Teste Realistas

**Estrutura:**

```
tests/fixtures/
├── diffs/
│   ├── vulnerable_code.diff         # Diff com vulnerabilidades
│   ├── clean_code.diff               # Diff sem issues
│   ├── large_diff.diff               # Diff grande (performance)
│   └── empty.diff                    # Diff vazio
├── markdown_outputs/
│   ├── security_findings.md          # Output Security Agent
│   ├── design_findings.md            # Output Design Agent
│   └── code_findings.md              # Output Code Agent
├── json_results/
│   ├── security.json
│   ├── design.json
│   ├── code.json
│   └── normalized.json
└── pr_data/
    ├── sample_pr.json                # Dados de PR mockado
    └── thread_context.json           # Thread context examples
```

---

## 8. MÉTRICAS E COBERTURA

### 8.1 Metas de Cobertura

**Objetivos:**
- **Cobertura total:** ≥ 80%
- **Componentes críticos:** ≥ 95%
  - `git_diff_parser.py`
  - `markdown_parser.py`
  - `finding_deduplicator.py`
  - `normalize_results.py`
- **Componentes médios:** ≥ 80%
  - Agent runners
  - `publish_to_pr.py`
- **Componentes baixos:** ≥ 60%
  - Utils diversos
  - Scripts auxiliares

### 8.2 Relatórios

**Geração:**

```bash
# Gerar relatório de cobertura
pytest --cov=scripts --cov-report=html --cov-report=term

# Verificar mínimo
coverage report --fail-under=80

# Visualizar HTML
open htmlcov/index.html
```

**Métricas Rastreadas:**
- Line coverage
- Branch coverage
- Function coverage
- Missing lines (linhas não testadas)

---

## 9. COMANDOS ÚTEIS

### 9.1 Execução de Testes

```bash
# Todos os testes
make test

# Apenas unitários
pytest tests/unit -v

# Apenas integração
pytest tests/integration -v -m integration

# Apenas E2E (lentos)
pytest tests/ -v -m e2e

# Com cobertura
pytest --cov=scripts --cov-report=term

# Testes específicos
pytest tests/unit/test_git_diff_parser.py -v

# Testes por marker
pytest -m security -v
pytest -m performance -v

# Debug (verbose + logs)
pytest -vv -s --log-cli-level=DEBUG

# Paralelo (rápido)
pytest -n auto

# Watch mode (desenvolvimento)
ptw -- -v
```

### 9.2 Makefile Targets

```makefile
# Makefile

.PHONY: test test-unit test-integration test-e2e test-security test-performance coverage

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v -m integration

test-e2e:
	pytest tests/ -v -m e2e

test-security:
	pytest tests/ -v -m security

test-performance:
	pytest tests/ -v -m performance

coverage:
	pytest --cov=scripts --cov-report=html --cov-report=term
	@echo "Open htmlcov/index.html to view report"

coverage-ci:
	pytest --cov=scripts --cov-report=xml
	coverage report --fail-under=80
```

---

## 10. ESTRATÉGIA DE TESTES POR FASE

### Fase 1: Setup Básico
- ✅ Testes de configuração (validate_setup.py)
- ✅ Testes de estrutura de diretórios
- ✅ Testes de dependências

### Fase 2: Security Review Agent
- ✅ Testes unitários: GitDiffParser
- ✅ Testes unitários: MarkdownParser
- ✅ Testes unitários: SecurityReviewRunner
- ✅ Testes de integração: Diff → LLM → Findings
- ✅ Testes de segurança: Sanitização

### Fase 3: Design + Code Agents
- ✅ Testes unitários: DesignReviewRunner
- ✅ Testes unitários: CodeReviewRunner
- ✅ Testes de integração: 3 agents em paralelo

### Fase 4: Normalizer
- ✅ Testes unitários: FindingDeduplicator
- ✅ Testes unitários: Normalizer
- ✅ Testes de integração: Multi-agent deduplication

### Fase 5: PR Publisher
- ✅ Testes unitários: AzureDevOpsClient
- ✅ Testes unitários: PRPublisher
- ✅ Testes de integração: Publisher + Azure API
- ✅ Testes E2E: Fluxo completo

### Fase 6: Polish
- ✅ Testes de regressão: Suite completa
- ✅ Testes de performance: Benchmarks
- ✅ Smoke tests: Validação pós-deploy

---

## 11. TRATAMENTO DE FALHAS

### 11.1 Testes Flaky

**Identificação:**
```bash
# Executar 100x para detectar flakiness
pytest tests/integration/test_llm_integration.py --count=100
```

**Mitigação:**
- Usar fixtures determinísticas
- Mock external dependencies
- Usar VCR.py para gravação de requests HTTP
- Evitar sleeps (usar waits condicionais)

### 11.2 Debugging de Testes

**Estratégias:**

```python
# 1. Usar breakpoint()
def test_complex_logic():
    result = complex_function()
    breakpoint()  # Parar aqui
    assert result == expected

# 2. Usar pytest.set_trace()
import pytest
def test_with_trace():
    pytest.set_trace()
    # Debugger ativo

# 3. Logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Comandos:**
```bash
# Debug com pdb
pytest --pdb tests/unit/test_parser.py

# Parar no primeiro erro
pytest -x

# Last failed
pytest --lf

# Verbose output
pytest -vv -s
```

---

## 12. CHECKLIST DE QUALIDADE

Antes de considerar um componente "completo":

- [ ] **Testes unitários:** Cobertura ≥ 95%
- [ ] **Testes de integração:** Casos principais cobertos
- [ ] **Testes de segurança:** Sanitização validada
- [ ] **Testes de performance:** Dentro dos limites (< 2 min)
- [ ] **Documentação:** Docstrings em todas as funções
- [ ] **Type hints:** Python type hints completos
- [ ] **Lint:** `flake8` e `mypy` sem erros
- [ ] **Coverage:** CI passa com ≥ 80%
- [ ] **Code review:** Aprovado por peer
- [ ] **Smoke tests:** Validação manual em ambiente staging

---

## 13. PRÓXIMOS PASSOS

### Curto Prazo (1-2 semanas)
- [ ] Completar testes unitários para todos os componentes
- [ ] Adicionar testes de integração para fluxos críticos
- [ ] Configurar CI/CD com gates de cobertura
- [ ] Criar fixtures realistas para todos os cenários

### Médio Prazo (1 mês)
- [ ] Adicionar testes E2E completos
- [ ] Implementar testes de carga (performance)
- [ ] Adicionar mutation testing (Mutmut)
- [ ] Criar suite de smoke tests para produção

### Longo Prazo (3+ meses)
- [ ] Testes de chaos engineering
- [ ] Property-based testing (Hypothesis)
- [ ] Visual regression testing (Screenshots de comments)
- [ ] Contract testing (OpenAPI compliance)

---

## 14. REFERÊNCIAS

**Ferramentas:**
- [pytest](https://docs.pytest.org/) - Framework principal
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Cobertura
- [pytest-mock](https://pytest-mock.readthedocs.io/) - Mocking
- [VCR.py](https://vcrpy.readthedocs.io/) - HTTP recording
- [Hypothesis](https://hypothesis.readthedocs.io/) - Property-based testing

**Boas Práticas:**
- [Google Testing Blog](https://testing.googleblog.com/)
- [Martin Fowler - Testing Strategies](https://martinfowler.com/tags/testing.html)
- [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

---

**Última Atualização:** 2026-01-03
**Versão:** 1.0
**Manutenção:** Engineering Team
