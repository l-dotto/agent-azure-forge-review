# 🚀 Setup Guide - Azure Code Reviewer

## Our Differentiator: **3-Step Setup. That's It.**

Most code review tools require hours of configuration, complex YAML files, and infrastructure setup. **Not this one.**

---

## 📋 Prerequisites

- Azure DevOps repository with Pull Requests enabled
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Python 3.11+ (if running locally)

---

## ⚡ Quick Start (3 Steps)

### Step 1: Add Your API Key (30 seconds)

1. Go to your Azure DevOps project
2. Navigate to **Pipelines** → **Library**
3. Create a new Variable Group named `code-review-secrets`
4. Add a secret variable:
   - Name: `ANTHROPIC_API_KEY`
   - Value: `your-api-key-here`
   - ✅ Check "Keep this value secret"

**That's it for secrets!** Everything else is automatic.

---

### Step 2: Copy the Pipeline File (10 seconds)

Copy [`azure-pipelines.yml`](../azure-pipelines.yml) to the root of your repository.

**No changes needed!** The pipeline auto-detects everything:
- ✅ Repository URL
- ✅ Branch name
- ✅ PR ID
- ✅ Project name
- ✅ Access tokens

---

### Step 3: Enable Build Validation (1 minute)

1. Go to **Repos** → **Branches**
2. Click `...` on your main branch → **Branch policies**
3. Under **Build Validation**, click `+` to add a new policy
4. Select your pipeline (the one you created in Step 2)
5. Configure:
   - **Trigger:** Automatic
   - **Policy requirement:** Required
   - **Build expiration:** Immediately
6. Save

**Done!** 🎉

---

## ✅ Verification

Create a test PR and watch the magic happen:

1. Create a new branch: `git checkout -b test/code-review`
2. Make a small change to any file
3. Push and create a PR
4. Within 2-3 minutes, you'll see:
   - ✅ Pipeline running
   - ✅ Summary comment posted
   - ✅ Inline comments on issues found

---

## 🎛️ Optional Configuration

### Customize Inline Comment Threshold

By default, only **High** and **Critical** issues are posted as inline comments.

To change this, edit your pipeline YAML and add under `variables`:

```yaml
variables:
  - group: code-review-secrets
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'medium'  # Options: critical | high | medium | low | all
```

**Recommendations:**
- `critical` - Only show-stoppers (good for large teams)
- `high` - Security + architecture issues (default, recommended)
- `medium` - Include code quality issues
- `all` - Every single finding (can be noisy)

---

## 🔒 Permissions

The pipeline needs permission to comment on PRs. This is **automatically granted** when you use `$(System.AccessToken)`, but verify:

1. Go to **Project Settings** → **Repositories**
2. Select your repository
3. Go to **Security** tab
4. Find **Build Service** (`[Project Name] Build Service`)
5. Ensure it has:
   - ✅ **Contribute to pull requests** - Allow

If not, grant this permission.

---

## 🎨 Customizing Review Behavior

### Agent Focus Areas

The system uses 3 specialized agents:

| Agent | Focus | Model | Can Disable? |
|-------|-------|-------|--------------|
| **Sentinel** 🛡️ | Security vulnerabilities | Sonnet 4.5 | ⚠️ Not recommended |
| **Atlas** 🎨 | Design & UX | Sonnet 4.5 | ✅ Yes (see below) |
| **Forge** 🔨 | Code quality | Opus 4.5 | ⚠️ Not recommended |

### Disabling Agents

If you don't need design reviews (e.g., backend-only project), comment out in [`azure-pipelines.yml`](../azure-pipelines.yml):

```yaml
# - script: python scripts/agents/run_design_review.py
#   displayName: '🎨 Atlas - Design Review'
#   continueOnError: true
```

---

## 📊 What Gets Reviewed?

The agents analyze:

- ✅ **Security:** SQL injection, XSS, auth bypass, secrets exposure, insecure crypto
- ✅ **Design:** WCAG compliance, visual consistency, UX patterns, accessibility
- ✅ **Code Quality:** Architecture, SOLID principles, performance, maintainability
- ✅ **Best Practices:** Error handling, logging, testing, documentation

---

## 🐛 Troubleshooting

### "Missing required Azure DevOps configuration"

**Solution:** Make sure you're running in Azure Pipelines with PR trigger. The pipeline auto-injects all required variables.

### "Failed to create thread: 401 Unauthorized"

**Solution:** Grant **Contribute to pull requests** permission to Build Service (see Permissions section above).

### "Review results not found"

**Solution:** One of the agents failed. Check pipeline logs to see which agent crashed and why.

### Pipeline succeeds but no comments appear

**Solutions:**
1. Check if `reviewResult.json` was created in the `findings/` folder
2. Verify Build Service has PR comment permissions
3. Check pipeline logs for the "Publish to PR" step

---

## 🚀 Advanced: Running Locally

For testing agent behavior before pushing:

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Run agents individually
python scripts/agents/run_security_review.py
python scripts/agents/run_design_review.py
python scripts/agents/run_code_review.py

# Normalize results
python scripts/normalize_results.py

# View results
cat findings/reviewResult.json | jq
```

**Note:** Publishing to PR only works in Azure Pipelines (requires PR context).

---

## 📈 Performance

Typical PR review time: **2-3 minutes**

- Sentinel (Security): ~30-45s
- Atlas (Design): ~30-45s
- Forge (Code Quality): ~60-90s (Opus is more thorough)
- Normalization + Publishing: ~10-15s

For large PRs (500+ lines), add ~30-60s per agent.

---

## 🎯 Next Steps

1. ✅ Setup complete? Create a test PR!
2. 📚 Read agent documentation: [`.claude/agents/`](../.claude/agents/)
3. 🔧 Customize thresholds based on team feedback
4. 📊 Track review quality improvements over time

---

## 💡 Pro Tips

### Reduce Noise

Start with `INLINE_SEVERITY_THRESHOLD: critical` for the first week. Once your team trusts the system, move to `high`.

### Focus on Security

If you only care about security, disable Atlas and Forge in the pipeline. Sentinel alone is incredibly valuable.

### Custom Rules

Each agent has a detailed prompt in `.claude/agents/`. You can customize what they look for by editing these files.

### Performance Optimization

Running all 3 agents takes time. For faster feedback:
- Run agents in parallel (requires pipeline modification)
- Use Sonnet instead of Opus for Forge (faster, slightly less thorough)

---

## 🆘 Need Help?

- 📖 Check [CLAUDE.md](../CLAUDE.md) for project overview
- 🐛 Found a bug? Open an issue in your repo
- 💬 Questions? Review pipeline logs first

---

**Remember:** The goal is **net positive over perfection**. Start simple, gather feedback, iterate.

Happy reviewing! 🚀
