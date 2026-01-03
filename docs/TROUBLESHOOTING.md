# Troubleshooting Guide

This guide covers common issues and their solutions. If you don't find your issue here, please [open a GitHub issue](https://github.com/your-org/azure-forge-review/issues).

---

## Table of Contents

- [Setup Issues](#setup-issues)
- [Pipeline Issues](#pipeline-issues)
- [Permission Issues](#permission-issues)
- [API Issues](#api-issues)
- [Comment Issues](#comment-issues)
- [Performance Issues](#performance-issues)
- [Advanced Debugging](#advanced-debugging)

---

## Setup Issues

### ❌ Error: "ANTHROPIC_API_KEY not found"

**Cause:** Variable Group not configured or API key not set as secret.

**Solution:**

```bash
# Method 1: Re-run automated setup
./setup.sh

# Method 2: Manual configuration via Azure CLI
az pipelines variable-group create \
  --organization https://dev.azure.com/your-org \
  --project YourProject \
  --name code-review-secrets \
  --variables ANTHROPIC_API_KEY=sk-ant-your-key-here

# Mark as secret
az pipelines variable-group variable update \
  --group-id <group-id> \
  --name ANTHROPIC_API_KEY \
  --secret true
```

**Verification:**

```bash
# Check if Variable Group exists
az pipelines variable-group list \
  --organization https://dev.azure.com/your-org \
  --project YourProject \
  | grep code-review-secrets

# Validate API key works
make validate-api-key
```

---

### ❌ Error: "Azure CLI not authenticated"

**Cause:** Azure CLI session expired or not logged in.

**Solution:**

```bash
# Login to Azure CLI
az login

# Set default organization and project
az devops configure --defaults \
  organization=https://dev.azure.com/your-org \
  project=YourProject

# Verify authentication
az account show
```

---

### ❌ Error: "Python version mismatch"

**Cause:** Python version < 3.11.

**Solution:**

```bash
# Check current version
python --version

# Install Python 3.11+ (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv

# Create virtual environment with correct version
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Pipeline Issues

### ❌ Pipeline fails with "No such file or directory"

**Cause:** Pipeline running before repository structure is properly set up.

**Solution:**

```bash
# Verify directory structure
ls -la scripts/agents/
ls -la scripts/utils/
ls -la scripts/templates/

# If missing, re-clone repository
git clone https://github.com/your-org/azure-forge-review.git
cd azure-forge-review
./setup.sh
```

---

### ❌ Pipeline succeeds but no findings

**Cause:** Either genuinely no issues, or parsing failed silently.

**Diagnosis:**

```bash
# Test agents locally with verbose logging
python scripts/agents/run_security_review.py \
  --pr-id mock \
  --output findings/security.json \
  --verbose

# Check if findings file was generated
cat findings/security.json | jq .

# Verify git diff has content
git diff --merge-base origin/main
```

**Common reasons:**
1. **Empty diff** - No changes to analyze
2. **Clean code** - No issues found (rare but possible)
3. **Parser failure** - Check logs for markdown parsing errors

**Solution:**

```bash
# Force threshold to 'all' temporarily to see everything
# Edit azure-pipelines.yml:
variables:
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'all'

# Create test PR with intentional issues
echo "SELECT * FROM users WHERE name = '" + user_input + "'" > test.py
git add test.py
git commit -m "test: intentional SQL injection for testing"
git push
```

---

### ❌ Pipeline times out

**Cause:** Large PR (>1000 lines) takes too long to analyze.

**Solution:**

```bash
# Option 1: Increase pipeline timeout (azure-pipelines.yml)
jobs:
  - job: CodeReview
    timeoutInMinutes: 30  # Default is 60, reduce or increase

# Option 2: Split large PRs into smaller chunks
git rebase -i HEAD~5  # Interactive rebase to split commits

# Option 3: Disable slower agents temporarily
# Comment out Forge (Opus 4.5 is slower) in azure-pipelines.yml
# - script: python scripts/agents/run_code_review.py
#   displayName: '🧠 Code Review (DISABLED)'
```

---

## Permission Issues

### ❌ Error: "Access denied" or "TF401027"

**Cause:** Build Service lacks "Contribute to Pull Requests" permission.

**Solution:**

```bash
# Automated fix
make fix-permissions

# Manual fix:
# 1. Go to Azure DevOps → Project Settings
# 2. Repositories → Select your repo → Security
# 3. Find "[ProjectName] Build Service ([OrgName])"
# 4. Set "Contribute to pull requests" to "Allow"
# 5. Set "Create thread" to "Allow"
```

**Verification:**

```bash
# Check permissions via API
az devops security permission show \
  --id <repo-security-namespace-id> \
  --subject <build-service-descriptor>
```

---

### ❌ Error: "Variable group 'code-review-secrets' not found"

**Cause:** Variable Group not created or pipeline doesn't have access.

**Solution:**

```bash
# Create Variable Group
az pipelines variable-group create \
  --name code-review-secrets \
  --variables ANTHROPIC_API_KEY=sk-ant-...

# Grant pipeline access to Variable Group
# Go to: Pipelines → Library → code-review-secrets → Pipeline permissions
# → Add pipeline → Select "Azure Code Reviewer"
```

---

## API Issues

### ❌ Error: "Anthropic API rate limit exceeded"

**Cause:** Too many requests in short time (free tier limit or high PR volume).

**Solution:**

```bash
# Option 1: Upgrade to paid tier
# Visit: https://console.anthropic.com/settings/billing

# Option 2: Reduce review frequency
# Edit azure-pipelines.yml trigger:
pr:
  branches:
    include: ['main', 'develop']  # Only on main branches
  paths:
    exclude: ['docs/**', '*.md', 'tests/**']  # Skip docs/tests

# Option 3: Add retry with longer backoff
# Already implemented in scripts/utils/azure_devops_client.py
# Adjust max_retries if needed
```

---

### ❌ Error: "Invalid API key"

**Cause:** API key incorrect, expired, or not properly set.

**Diagnosis:**

```bash
# Test API key manually
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Hi"}]
  }'

# Expected: JSON response with completion
# Error: 401 Unauthorized = invalid key
```

**Solution:**

```bash
# Generate new API key at: https://console.anthropic.com/settings/keys

# Update Variable Group
az pipelines variable-group variable update \
  --group-id <id> \
  --name ANTHROPIC_API_KEY \
  --value sk-ant-new-key-here \
  --secret true
```

---

## Comment Issues

### ❌ No comments appear in PR

**Quick diagnostic:**

```bash
# 1. Check pipeline ran successfully
# Azure DevOps → Pipelines → Recent runs → Check status

# 2. View detailed logs
make debug-last-run

# 3. Validate configuration
make validate-config

# 4. Test locally
make test-local
```

**Common causes and solutions:**

| Cause | Solution |
|-------|----------|
| **Threshold too restrictive** | Lower threshold in `azure-pipelines.yml` to `medium` or `all` |
| **No findings met severity** | Review `reviewResult.json` in pipeline artifacts |
| **Parser failed** | Check logs for markdown parsing errors, update `scripts/utils/markdown_parser.py` |
| **API failure** | Check Anthropic API status, verify rate limits |
| **Azure DevOps API error** | Check Build Service permissions |

**Detailed investigation:**

```bash
# Download pipeline artifacts
az pipelines runs artifact download \
  --run-id <run-id> \
  --artifact-name findings

# Inspect reviewResult.json
cat reviewResult.json | jq '.findings[] | select(.severity == "critical")'

# Check if threshold filtered everything out
cat reviewResult.json | jq '.summary.by_severity'
```

---

### ❌ Comments appear multiple times (duplicates)

**Cause:** Normalizer deduplication not working or pipeline ran multiple times.

**Solution:**

```bash
# Check deduplication logic
python scripts/normalize_results.py \
  --security-file findings/security.json \
  --code-file findings/code.json \
  --design-file findings/design.json \
  --output reviewResult.json \
  --similarity-threshold 0.80 \
  --stats  # Shows deduplication stats

# Increase similarity threshold to be more aggressive
--similarity-threshold 0.70  # More findings considered duplicates
```

---

### ❌ Comment formatting broken (Markdown not rendering)

**Cause:** Jinja2 template syntax error or Azure DevOps markdown incompatibility.

**Diagnosis:**

```bash
# Test template rendering locally
python -c "
from jinja2 import Template
template = Template(open('scripts/templates/finding.md.jinja2').read())
print(template.render({
  'severity': 'critical',
  'title': 'Test Issue',
  'file': 'test.py',
  'line': 42,
  'description': 'Test description',
  'recommendation': 'Fix it'
}))
"
```

**Solution:**

- Azure DevOps uses GitHub Flavored Markdown (GFM)
- Avoid HTML tags - use pure Markdown
- Test in Azure DevOps comment box before committing template changes

---

## Performance Issues

### ❌ Pipeline takes >5 minutes

**Diagnosis:**

```bash
# Check which agent is slowest (view pipeline logs)
# Typical times:
# - Sentinel: ~30-60s
# - Atlas: ~30-60s
# - Forge: ~60-120s (Opus 4.5 is slower but more thorough)
```

**Solutions:**

```bash
# Option 1: Use Sonnet for all agents (faster, slightly less thorough)
# Edit scripts/agents/run_code_review.py:
model = "claude-sonnet-4-5-20250929"  # Instead of Opus

# Option 2: Run agents in parallel (requires code changes)
# Currently sequential - V2.0 will use asyncio for parallelization

# Option 3: Cache results for unchanged files
# Add to git_diff_parser.py to only analyze changed sections
```

---

## Advanced Debugging

### Collect full diagnostic information

```bash
# Run diagnostic script
make collect-diagnostics

# This creates diagnostics.txt with:
# - Python version
# - Installed packages
# - Azure CLI version
# - Environment variables (sanitized)
# - Recent pipeline logs
# - Configuration validation results
```

### Enable verbose logging

```bash
# Edit agent runners to add --verbose flag
python scripts/agents/run_security_review.py \
  --pr-id $(System.PullRequest.PullRequestId) \
  --output findings/security.json \
  --verbose \
  --log-level DEBUG
```

### Test individual components

```bash
# Test git diff parser
python -c "
from scripts.utils.git_diff_parser import get_pr_diff
diff = get_pr_diff(pr_id=123)
print(f'Diff size: {len(diff)} characters')
print(diff[:500])  # First 500 chars
"

# Test markdown parser
python -c "
from scripts.utils.markdown_parser import parse_security_markdown
findings = parse_security_markdown(open('test.md').read())
print(f'Parsed {len(findings)} findings')
"

# Test Azure DevOps client
python -c "
from scripts.utils.azure_devops_client import AzureDevOpsClient
client = AzureDevOpsClient(org='your-org', project='YourProject')
# Test connection
print('Connection successful')
"
```

### View raw API responses

```bash
# Add debug logging to azure_devops_client.py
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show:
# - Full HTTP requests
# - Response status codes
# - Response bodies
# - Retry attempts
```

---

## Still Having Issues?

If your issue isn't covered here:

1. **Check GitHub Issues**: [github.com/your-org/azure-forge-review/issues](https://github.com/your-org/azure-forge-review/issues)
2. **Search Discussions**: [github.com/your-org/azure-forge-review/discussions](https://github.com/your-org/azure-forge-review/discussions)
3. **Open New Issue** with:
   - Output of `make collect-diagnostics`
   - Pipeline logs (sanitized - remove secrets!)
   - Steps to reproduce
   - Expected vs actual behavior

---

## Prevention Tips

✅ **Always:**
- Run `make validate-config` before deploying
- Test locally with `make test-local` before pushing
- Keep dependencies updated (`pip install -r requirements.txt --upgrade`)
- Monitor pipeline logs for warnings

❌ **Never:**
- Commit secrets or API keys
- Skip setup.sh validation steps
- Force-push to main branch
- Modify core files without testing

---

**Last Updated:** 2026-01-03
