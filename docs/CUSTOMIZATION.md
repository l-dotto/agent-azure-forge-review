# Customization Guide

This guide shows you how to customize Azure Forge Review to fit your team's needs.

---

## Table of Contents

- [Severity Threshold](#severity-threshold)
- [Agent Configuration](#agent-configuration)
- [Comment Templates](#comment-templates)
- [Filters and Exclusions](#filters-and-exclusions)
- [Agent Prompts](#agent-prompts)
- [Custom Agents](#custom-agents)
- [Advanced Configuration](#advanced-configuration)

---

## Severity Threshold

Control which findings appear as inline comments in PRs.

### Quick Change

Edit [`azure-pipelines.yml`](../azure-pipelines.yml):

```yaml
variables:
  - group: code-review-secrets
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'medium'  # Change this value
```

### Available Options

| Threshold | Inline Comments Include | Best For |
|-----------|------------------------|----------|
| `critical` | Only critical severity | High-noise repos, mature codebases |
| `high` | Critical + high (default) | Most teams, balanced signal/noise |
| `medium` | Critical + high + medium | New projects, learning teams |
| `all` | All findings (low, info, etc.) | Strict quality requirements |

### Temporary Override (via Makefile)

```bash
# Set threshold for next run only
make set-threshold THRESHOLD=all

# Revert to default
make set-threshold THRESHOLD=high
```

### Dynamic Threshold (Advanced)

Set different thresholds for different branches:

```yaml
# azure-pipelines.yml
variables:
  - ${{ if eq(variables['System.PullRequest.TargetBranch'], 'refs/heads/main') }}:
    - name: INLINE_SEVERITY_THRESHOLD
      value: 'high'
  - ${{ if eq(variables['System.PullRequest.TargetBranch'], 'refs/heads/develop') }}:
    - name: INLINE_SEVERITY_THRESHOLD
      value: 'medium'
```

---

## Agent Configuration

### Disable Specific Agents

Comment out agents in [`azure-pipelines.yml`](../azure-pipelines.yml):

```yaml
# Disable Design Review
# - task: PythonScript@0
#   displayName: '🎨 Design Review'
#   inputs:
#     scriptSource: 'filePath'
#     scriptPath: 'scripts/agents/run_design_review.py'
#     arguments: '--pr-id $(System.PullRequest.PullRequestId) --output $(Build.ArtifactStagingDirectory)/design.json'
```

### Change Agent Models

Edit agent runner scripts to use different models:

**Use Sonnet everywhere (faster, cheaper):**

```python
# scripts/agents/run_code_review.py
MODEL = "claude-sonnet-4-5-20250929"  # Instead of Opus
```

**Use Opus everywhere (slower, more thorough):**

```python
# scripts/agents/run_security_review.py
MODEL = "claude-opus-4-5-20251101"  # Instead of Sonnet
```

### Adjust Agent Timeouts

```yaml
# azure-pipelines.yml
- task: PythonScript@0
  displayName: '🛡️ Security Review'
  timeoutInMinutes: 10  # Default is 5
  inputs:
    scriptPath: 'scripts/agents/run_security_review.py'
```

---

## Comment Templates

Templates are Jinja2 files that control comment formatting.

### Summary Template

Edit [`scripts/templates/summary.md.jinja2`](../scripts/templates/summary.md.jinja2):

```jinja2
🔍 **Code Review Complete**

## 📊 Analysis Summary

{% for agent_name, stats in summary.by_agent.items() %}
• **{{ agent_name }}**: {{ stats.critical }} critical, {{ stats.high }} high, {{ stats.medium }} medium
{% endfor %}

---

💬 **Inline Comments**: {{ inline_count }} (threshold: {{ threshold }})
📝 **Total Findings**: {{ summary.total }}

{% if summary.total == 0 %}
✨ **Great job!** No issues found.
{% endif %}

---

⚙️ **Current threshold**: `{{ threshold }}`
_To see more/fewer inline comments, adjust `INLINE_SEVERITY_THRESHOLD` in azure-pipelines.yml_
```

### Inline Comment Template

Edit [`scripts/templates/finding.md.jinja2`](../scripts/templates/finding.md.jinja2):

**Example: Add emoji for severity:**

```jinja2
{% if severity == 'critical' %}🚨{% elif severity == 'high' %}⚠️{% elif severity == 'medium' %}💡{% else %}ℹ️{% endif %} **{{ severity | upper }}** - {{ title }}

**File:** `{{ file }}:{{ line }}`
**Agent:** {{ agent }}

### Issue
{{ description }}

{% if exploit_scenario %}
### Exploit Scenario
{{ exploit_scenario }}
{% endif %}

### Recommendation
{{ recommendation }}

{% if references %}
### References
{% for ref in references %}
• [{{ ref.title }}]({{ ref.url }})
{% endfor %}
{% endif %}
```

**Example: Simplified format:**

```jinja2
### {{ severity | upper }}: {{ title }}

**Line {{ line }} in {{ file }}**

{{ description }}

**Fix:** {{ recommendation }}
```

### Test Template Changes

```bash
# Render template with test data
python -c "
from jinja2 import Template

template = Template(open('scripts/templates/finding.md.jinja2').read())

print(template.render({
    'severity': 'critical',
    'title': 'SQL Injection',
    'file': 'api/users.py',
    'line': 42,
    'agent': 'Sentinel',
    'description': 'User input directly in SQL query',
    'recommendation': 'Use parameterized queries',
    'exploit_scenario': 'Attacker can execute arbitrary SQL',
    'references': [
        {'title': 'OWASP SQL Injection', 'url': 'https://owasp.org/...'}
    ]
}))
"
```

---

## Filters and Exclusions

### Exclude Files from Analysis

Edit [`azure-pipelines.yml`](../azure-pipelines.yml) PR trigger:

```yaml
pr:
  branches:
    include: ['*']
  paths:
    exclude:
      - 'docs/**'           # Documentation
      - '*.md'              # Markdown files
      - 'tests/**'          # Test files
      - 'vendor/**'         # Third-party code
      - 'node_modules/**'   # Dependencies
      - '*.min.js'          # Minified files
      - '*.generated.*'     # Generated files
```

### Exclude Specific Branches

```yaml
pr:
  branches:
    include:
      - main
      - develop
      - release/*
    exclude:
      - experimental/*
      - personal/*
```

### Custom File Filters (in code)

Edit [`scripts/utils/git_diff_parser.py`](../scripts/utils/git_diff_parser.py):

```python
def should_analyze_file(filepath: str) -> bool:
    """Determine if file should be analyzed."""

    # Exclude patterns
    exclude_patterns = [
        r'\.min\.js$',
        r'\.generated\.',
        r'^vendor/',
        r'^node_modules/',
        r'^public/assets/',
        r'\.(jpg|png|gif|svg|ico)$',  # Images
        r'\.(woff|woff2|ttf|eot)$',   # Fonts
    ]

    for pattern in exclude_patterns:
        if re.search(pattern, filepath):
            return False

    return True
```

---

## Agent Prompts

Agent behavior is controlled by prompt files in [`.claude/agents/`](../.claude/agents/).

### Modify Security Agent

Edit [`.claude/agents/security-review-slash-command.md`](../.claude/agents/security-review-slash-command.md):

**Example: Add custom security rules:**

```markdown
## Custom Security Rules

### Financial System Specific
- **Payment Amount Validation**: Verify all payment amounts are validated server-side
- **Transaction Idempotency**: Check for idempotency keys on financial transactions
- **Audit Logging**: Ensure sensitive operations are logged

### PII Protection
- **CPF/CNPJ Handling**: Never log complete CPF/CNPJ (mask as ***.***.***-**)
- **Credit Card**: Never store full card numbers (use tokens only)
```

### Modify Code Review Agent

Edit [`.claude/agents/pragmatic-code-review-subagent.md`](../.claude/agents/pragmatic-code-review-subagent.md):

**Example: Add team-specific patterns:**

```markdown
## Team Coding Standards

### Required Patterns
- All API endpoints must have OpenAPI documentation
- Database queries must use parameterized statements
- All external API calls must have retry logic
- Error responses must include correlation IDs

### Prohibited Patterns
- No `console.log` in production code
- No hardcoded URLs (use environment variables)
- No `any` type in TypeScript (use proper types)
```

### Test Prompt Changes

```bash
# Run agent locally with modified prompt
python scripts/agents/run_security_review.py \
  --pr-id mock \
  --output findings/security.json \
  --verbose

# Review findings
cat findings/security.json | jq '.findings[].title'
```

---

## Custom Agents

### Create New Agent

**1. Create prompt file:**

```bash
# .claude/agents/performance-review-agent.md
cat > .claude/agents/performance-review-agent.md << 'EOF'
# Performance Review Agent

You are an expert in performance optimization and scalability.

## Focus Areas
- Database query efficiency (N+1 queries, missing indexes)
- Memory leaks and resource management
- Algorithmic complexity (O(n²) → O(n log n))
- Caching opportunities
- Async/await usage

## Output Format
For each finding:
- **Severity**: critical | high | medium | low
- **Title**: Brief description
- **File**: Affected file path
- **Line**: Line number
- **Performance Impact**: Quantify impact (e.g., "10x slower on large datasets")
- **Recommendation**: Specific optimization
EOF
```

**2. Create agent runner:**

```python
# scripts/agents/run_performance_review.py
import os
import json
from anthropic import Anthropic

def run_performance_review(pr_id: str, output_path: str):
    """Run performance review analysis."""

    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Get diff
    from scripts.utils.git_diff_parser import get_pr_diff
    diff = get_pr_diff(pr_id)

    # Load prompt
    with open('.claude/agents/performance-review-agent.md') as f:
        prompt = f.read()

    # Replace placeholders
    prompt = prompt.replace('{{DIFF}}', diff)

    # Call API
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse findings
    from scripts.utils.markdown_parser import parse_markdown_findings
    findings = parse_markdown_findings(response.content[0].text)

    # Save results
    result = {
        'agent': 'Performance',
        'findings': findings,
        'metadata': {
            'pr_id': pr_id,
            'model': 'claude-sonnet-4-5-20250929'
        }
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"✅ Performance review complete: {len(findings)} findings")

if __name__ == '__main__':
    import sys
    run_performance_review(
        pr_id=sys.argv[1],
        output_path=sys.argv[2]
    )
```

**3. Add to pipeline:**

```yaml
# azure-pipelines.yml
- task: PythonScript@0
  displayName: '⚡ Performance Review'
  inputs:
    scriptSource: 'filePath'
    scriptPath: 'scripts/agents/run_performance_review.py'
    arguments: '--pr-id $(System.PullRequest.PullRequestId) --output $(Build.ArtifactStagingDirectory)/performance.json'
```

**4. Update normalizer:**

```python
# scripts/normalize_results.py
# Add performance findings to consolidation
performance_file = args.performance_file
if performance_file and os.path.exists(performance_file):
    with open(performance_file) as f:
        performance_data = json.load(f)
        all_findings.extend(performance_data['findings'])
```

---

## Advanced Configuration

### Environment-Specific Settings

```yaml
# azure-pipelines.yml
variables:
  - ${{ if eq(variables['Build.SourceBranchName'], 'main') }}:
    - name: INLINE_SEVERITY_THRESHOLD
      value: 'high'
    - name: ENABLE_PERFORMANCE_AGENT
      value: 'true'

  - ${{ if ne(variables['Build.SourceBranchName'], 'main') }}:
    - name: INLINE_SEVERITY_THRESHOLD
      value: 'medium'
    - name: ENABLE_PERFORMANCE_AGENT
      value: 'false'
```

### Conditional Agent Execution

```yaml
# Run performance agent only on main branch
- ${{ if eq(variables['ENABLE_PERFORMANCE_AGENT'], 'true') }}:
  - task: PythonScript@0
    displayName: '⚡ Performance Review'
    inputs:
      scriptPath: 'scripts/agents/run_performance_review.py'
```

### Custom Severity Mapping

```python
# scripts/normalize_results.py

def map_custom_severity(finding: dict) -> str:
    """Map findings to custom severity levels."""

    # Example: Escalate all SQL injection to critical
    if 'sql injection' in finding['title'].lower():
        return 'critical'

    # Example: Downgrade TODO comments
    if finding['category'] == 'TODO':
        return 'low'

    return finding.get('severity', 'medium')
```

### Custom Deduplication Logic

```python
# scripts/utils/finding_deduplicator.py

def custom_deduplication_key(finding: dict) -> str:
    """Generate custom key for deduplication."""

    # Group by file + category (ignore line numbers)
    return f"{finding['file']}|{finding['category']}"

# Use in normalize_results.py:
deduplicated = deduplicate_findings(
    findings,
    key_func=custom_deduplication_key,
    similarity_threshold=0.85
)
```

---

## Examples

### Example: Strict Security for Production

```yaml
# azure-pipelines.yml - Production branch
trigger:
  branches:
    include: ['release/*']

variables:
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'critical'  # Only critical issues block
  - name: ENABLE_AGENTS
    value: 'security,code'  # Skip design review

jobs:
  - job: SecurityReview
    displayName: 'Critical Security Review Only'
    steps:
      - task: PythonScript@0
        displayName: '🛡️ Security Review'
        inputs:
          scriptPath: 'scripts/agents/run_security_review.py'
```

### Example: Lenient for Feature Branches

```yaml
# azure-pipelines.yml - Feature branches
pr:
  branches:
    include: ['feature/*']

variables:
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'all'  # Show everything for learning

  - name: COMMENT_MODE
    value: 'summary_only'  # No inline spam
```

### Example: Team-Specific Templates

```jinja2
{# scripts/templates/finding.md.jinja2 #}

{# Add team mention for critical issues #}
{% if severity == 'critical' %}
@security-team Please review this critical finding.
{% endif %}

{{ severity | upper }}: {{ title }}

{# Add JIRA ticket link #}
{% if jira_ticket %}
**Related JIRA**: [{{ jira_ticket }}](https://jira.yourorg.com/browse/{{ jira_ticket }})
{% endif %}

{{ description }}
```

---

## Testing Customizations

### Test Locally

```bash
# Run full pipeline locally
make test-local

# Test specific agent
python scripts/agents/run_security_review.py --pr-id mock --output test.json

# Test template rendering
python scripts/publish_to_pr.py \
  --review-file reviewResult.json \
  --pr-id test \
  --dry-run  # Don't actually post comments
```

### Validate Pipeline YAML

```bash
# Validate syntax
az pipelines validate \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --repository azure-forge-review \
  --yml-path azure-pipelines.yml
```

### Test in Non-Production

1. Create separate Azure DevOps project for testing
2. Deploy customized version
3. Create test PRs with known issues
4. Verify customizations work as expected
5. Promote to production

---

## Best Practices

✅ **Do:**
- Test customizations locally before deploying
- Document why you made custom changes
- Keep custom logic separate from core code
- Version control all customizations
- Share useful customizations with community

❌ **Don't:**
- Modify core agent logic without understanding impact
- Hardcode organization-specific values
- Disable security checks without good reason
- Over-customize (keep it simple)

---

## Support

If you create a useful customization, please share it!

- **Share Examples**: [GitHub Discussions](https://github.com/your-org/azure-forge-review/discussions)
- **Contribute**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Questions**: [GitHub Issues](https://github.com/your-org/azure-forge-review/issues)

---

**Last Updated:** 2026-01-03
