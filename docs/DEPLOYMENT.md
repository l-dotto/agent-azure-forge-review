# Deployment Guide

Complete guide for deploying Azure Forge Review to your Azure DevOps organization.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup (Automated)](#quick-setup-automated)
- [Manual Setup (Step-by-Step)](#manual-setup-step-by-step)
- [Configuration](#configuration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Rollback Procedure](#rollback-procedure)

---

## Prerequisites

### Required

- **Azure DevOps Organization** with at least one project
- **Azure CLI** installed and authenticated
  ```bash
  az --version  # Should be >= 2.50.0
  az login
  ```
- **Python 3.11+** installed
  ```bash
  python --version  # Should be >= 3.11
  ```
- **Anthropic API Key** - Get one at [console.anthropic.com](https://console.anthropic.com/)
- **Git** installed and configured

### Permissions Required

You need the following permissions in Azure DevOps:

- **Project Administrator** or:
  - Create/edit pipelines
  - Manage variable groups
  - Configure branch policies
  - Grant Build Service permissions

---

## Quick Setup (Automated)

The fastest way to deploy - automated script handles everything.

### 1. Clone Repository

```bash
git clone https://github.com/your-org/azure-forge-review.git
cd azure-forge-review
```

### 2. Run Setup Script

```bash
./setup.sh
```

The script will:
1. ✅ Verify prerequisites (Python, Azure CLI, Git)
2. ✅ Prompt for configuration (org, project, API key)
3. ✅ Create Virtual Environment and install dependencies
4. ✅ Create Variable Group in Azure DevOps
5. ✅ Configure Build Service permissions
6. ✅ Validate configuration
7. ✅ Display next steps

### 3. Test Locally (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run agents with mock data
make test-local

# Expected output:
# ✓ Security agent completed: 3 findings
# ✓ Design agent completed: 2 findings
# ✓ Code agent completed: 4 findings
# ✓ Normalizer completed: 7 unique findings (2 duplicates removed)
```

### 4. Deploy Pipeline

```bash
make deploy-azure
```

### 5. Create Test PR

```bash
git checkout -b test/code-review-setup
echo "# Test PR for code review" > test.md
git add test.md
git commit -m "test: verify code review pipeline"
git push -u origin test/code-review-setup

# Open PR in Azure DevOps UI
```

**Done!** Within ~2 minutes, you should see review comments in your PR.

---

## Manual Setup (Step-by-Step)

If automated setup fails or you need more control, follow these steps.

### Step 1: Verify Prerequisites

```bash
# Check Python version
python --version  # Must be 3.11+

# Check Azure CLI
az --version  # Must be 2.50.0+

# Check Git
git --version

# Authenticate Azure CLI
az login

# Set defaults
az devops configure --defaults \
  organization=https://dev.azure.com/YOUR_ORG \
  project=YOUR_PROJECT
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep anthropic  # Should show anthropic==0.39.0
```

### Step 3: Create Variable Group

```bash
# Create variable group
az pipelines variable-group create \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --name code-review-secrets \
  --variables ANTHROPIC_API_KEY=sk-ant-your-key-here

# Get the group ID (needed for next steps)
GROUP_ID=$(az pipelines variable-group list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --query "[?name=='code-review-secrets'].id | [0]" -o tsv)

echo "Variable Group ID: $GROUP_ID"

# Mark API key as secret
az pipelines variable-group variable update \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --group-id $GROUP_ID \
  --name ANTHROPIC_API_KEY \
  --secret true
```

**Verify in UI:**
1. Go to Azure DevOps → Pipelines → Library
2. Find `code-review-secrets`
3. Verify `ANTHROPIC_API_KEY` shows as `*****`

### Step 4: Create Pipeline

```bash
# Push code to Azure DevOps repository
git remote add azure https://dev.azure.com/YOUR_ORG/YOUR_PROJECT/_git/azure-forge-review
git push azure main

# Create pipeline via Azure CLI
az pipelines create \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --name "Azure Forge Review" \
  --repository azure-forge-review \
  --branch main \
  --yml-path azure-pipelines.yml \
  --skip-first-run
```

**Or via UI:**
1. Azure DevOps → Pipelines → New Pipeline
2. Select your repository
3. Choose "Existing Azure Pipelines YAML file"
4. Select `/azure-pipelines.yml`
5. Click "Run"

### Step 5: Configure Build Service Permissions

The Build Service account needs permission to post comments to PRs.

**Method A: Via UI (Easier)**

1. Go to **Project Settings** → **Repositories**
2. Select your repository
3. Click **Security** tab
4. Find `[YOUR_PROJECT] Build Service (YOUR_ORG)`
5. Set these permissions to **Allow**:
   - **Contribute to pull requests**
   - **Create thread**

**Method B: Via Azure CLI**

```bash
# Get Build Service identity
BUILD_SERVICE_ID=$(az devops security group list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --scope project \
  --query "graphGroups[?contains(principalName, 'Build Service')].descriptor | [0]" -o tsv)

# Grant permissions (requires repo security namespace ID)
# This is complex - UI method recommended
```

**Verify:**
```bash
# Create a test PR
# Pipeline should run without permission errors
```

### Step 6: Configure Branch Policy

Enable automatic review on all PRs.

**Via UI:**

1. Go to **Repos** → **Branches**
2. Click **...** on `main` branch → **Branch policies**
3. Under **Build Validation**, click **+**
4. Configure:
   - **Build pipeline**: Azure Forge Review
   - **Trigger**: Automatic
   - **Policy requirement**: Optional (recommended) or Required
   - **Build expiration**: 12 hours
   - **Display name**: Code Review
5. Click **Save**

**Via Azure CLI:**

```bash
az repos policy build create \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --branch main \
  --repository-id $(az repos show --repository azure-forge-review --query id -o tsv) \
  --build-definition-id $(az pipelines show --name "Azure Forge Review" --query id -o tsv) \
  --enabled true \
  --blocking false \
  --display-name "Code Review" \
  --valid-duration 720  # 12 hours
```

### Step 7: Grant Pipeline Access to Variable Group

```bash
# Get pipeline ID
PIPELINE_ID=$(az pipelines show \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --name "Azure Forge Review" \
  --query id -o tsv)

# Grant access (currently no direct CLI command - use UI)
```

**Via UI:**
1. Pipelines → Library → code-review-secrets
2. Click **Pipeline permissions**
3. Click **+** → Select "Azure Forge Review"
4. Click **Save**

---

## Configuration

### Adjust Severity Threshold

Edit [`azure-pipelines.yml`](../azure-pipelines.yml):

```yaml
variables:
  - group: code-review-secrets
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'high'  # Options: critical | high | medium | all
```

| Value | Inline Comments Shown |
|-------|-----------------------|
| `critical` | Only critical findings |
| `high` | Critical + high (default) |
| `medium` | Critical + high + medium |
| `all` | All findings (verbose) |

### Customize Agents

To disable an agent, comment out its step in `azure-pipelines.yml`:

```yaml
# Disable Design Review
# - task: PythonScript@0
#   displayName: '🎨 Design Review'
#   inputs:
#     scriptSource: 'filePath'
#     scriptPath: 'scripts/agents/run_design_review.py'
```

### Modify Comment Templates

Edit Jinja2 templates:
- **Summary**: [`scripts/templates/summary.md.jinja2`](../scripts/templates/summary.md.jinja2)
- **Inline**: [`scripts/templates/finding.md.jinja2`](../scripts/templates/finding.md.jinja2)

See [CUSTOMIZATION.md](CUSTOMIZATION.md) for template syntax.

---

## Testing

### Local Testing

```bash
# Test with mock PR data
make test-local

# Test specific agent
python scripts/agents/run_security_review.py \
  --pr-id mock \
  --output findings/security.json

# Verify output
cat findings/security.json | jq .
```

### Pipeline Testing

```bash
# Create test branch
git checkout -b test/pipeline-verification

# Add intentional security issue
cat > vulnerable.py << 'EOF'
def get_user(user_id):
    # Intentional SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)
EOF

git add vulnerable.py
git commit -m "test: add vulnerable code for testing"
git push -u origin test/pipeline-verification

# Create PR via UI or CLI
az repos pr create \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --repository azure-forge-review \
  --source-branch test/pipeline-verification \
  --target-branch main \
  --title "Test: Pipeline Verification" \
  --description "Testing code review pipeline"
```

**Expected Results:**
- Pipeline runs automatically
- Security agent detects SQL injection
- Summary + inline comments appear in PR
- Comments reference line numbers correctly

### Validation Checklist

- [ ] Pipeline runs on every PR update
- [ ] Variable Group accessible by pipeline
- [ ] Build Service can post comments
- [ ] Comments appear within 2-3 minutes
- [ ] Inline comments link to correct line numbers
- [ ] Summary shows all three agents
- [ ] Threshold filtering works correctly
- [ ] No secrets appear in logs

---

## Production Deployment

### Pre-Deployment Checklist

```bash
# Run full validation
make validate-config

# Check for secrets in code
git grep -E '(sk-ant-|password|secret|api[_-]?key)' --ignore-case

# Run linters
make lint

# Run tests
make test
```

### Deployment Steps

1. **Merge to main branch**
   ```bash
   git checkout main
   git pull origin main
   git merge --no-ff feature/setup
   git push origin main
   ```

2. **Tag release**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0 - MVP"
   git push origin v1.0.0
   ```

3. **Monitor first production PR**
   - Create small test PR
   - Monitor pipeline logs
   - Verify comments appear
   - Check performance (should be < 3 minutes)

4. **Communicate to team**
   ```
   Subject: New Automated Code Review System Live

   Hi Team,

   We've deployed Azure Forge Review - an automated code review system
   that will now analyze all Pull Requests.

   What to expect:
   • Automatic security, design, and code quality analysis
   • Summary + inline comments on your PRs
   • Findings categorized by severity
   • No action required from you - it's automatic!

   Learn more: [link to README]
   Questions: [link to discussions]
   ```

### Post-Deployment Monitoring

```bash
# Monitor pipeline success rate
az pipelines runs list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --pipeline-ids $(az pipelines show --name "Azure Forge Review" --query id -o tsv) \
  --top 20

# Check for failures
az pipelines runs list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --pipeline-ids $(az pipelines show --name "Azure Forge Review" --query id -o tsv) \
  --status failed
```

**Success Metrics (First 30 days):**
- ✅ Pipeline success rate > 95%
- ✅ Average run time < 3 minutes
- ✅ < 5% false positive rate
- ✅ Team adoption > 80%

---

## Rollback Procedure

If issues occur, follow this rollback procedure.

### Quick Disable (Temporary)

```bash
# Disable branch policy
az repos policy update \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --id $(az repos policy list --branch main --query "[?type=='Build'].id | [0]" -o tsv) \
  --enabled false

# Or via UI:
# Repos → Branches → main → Branch Policies → Build Validation → Disable
```

### Full Rollback

```bash
# 1. Disable branch policy (see above)

# 2. Delete pipeline
az pipelines delete \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --id $(az pipelines show --name "Azure Forge Review" --query id -o tsv) \
  --yes

# 3. Delete variable group (optional - keeps API key for retry)
az pipelines variable-group delete \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --id $(az pipelines variable-group list --query "[?name=='code-review-secrets'].id | [0]" -o tsv) \
  --yes

# 4. Remove repository (if needed)
az repos delete \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --id $(az repos show --repository azure-forge-review --query id -o tsv) \
  --yes
```

### Gradual Rollback

If you want to keep some functionality:

```bash
# Option 1: Keep pipeline, disable auto-trigger
# Edit azure-pipelines.yml:
trigger: none  # Manual trigger only
pr: none       # Disable PR trigger

# Option 2: Reduce agents (keep only security)
# Comment out Atlas and Forge in azure-pipelines.yml

# Option 3: Increase threshold (reduce noise)
# Set INLINE_SEVERITY_THRESHOLD to 'critical'
```

---

## Troubleshooting Deployment

### Setup script fails

```bash
# Run with debug output
bash -x ./setup.sh

# Check logs
cat setup.log  # If script generates logs

# Common issues:
# - Azure CLI not authenticated → az login
# - Insufficient permissions → Verify you're Project Admin
# - Python version mismatch → Install Python 3.11+
```

### Variable Group not found

```bash
# List all variable groups
az pipelines variable-group list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT

# If missing, create manually (see Step 3)
```

### Pipeline fails immediately

```bash
# Check pipeline logs
az pipelines runs show \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --id <run-id>

# Common causes:
# - Variable group not linked → Grant pipeline access (Step 7)
# - Missing files → Ensure all scripts/ committed
# - Python version on agent → Use ubuntu-latest pool
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

---

## Next Steps

After successful deployment:

1. **Customize** - See [CUSTOMIZATION.md](CUSTOMIZATION.md)
2. **Monitor** - Watch first few PRs for issues
3. **Iterate** - Adjust threshold based on team feedback
4. **Scale** - Apply to more repositories
5. **Contribute** - Share improvements with community

---

## Support

- **Documentation**: [README.md](../README.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues**: [github.com/your-org/azure-forge-review/issues](https://github.com/your-org/azure-forge-review/issues)

---

**Deployed by**: [Your Name]
**Date**: 2026-01-03
**Version**: 1.0.0
