# Azure Forge Review

**Intelligent Code Review for Azure DevOps Pull Requests**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure DevOps](https://img.shields.io/badge/Azure%20DevOps-Compatible-0078D7)](https://azure.microsoft.com/en-us/products/devops/)

Automated code review that finds security vulnerabilities, design issues, and code quality problems **before** they reach production. Simple setup, powerful results.

---

## ✨ Why Azure Forge Review?

- **⚡ Setup in Minutes** - One command deploys everything
- **🎯 Finds Real Issues** - Security, design, and code quality analysis
- **💬 Clear Feedback** - Actionable comments, not noise
- **🔧 Easy to Customize** - Control what gets flagged
- **📊 Works Your Way** - Integrates seamlessly with Azure DevOps

---

## 🚀 Quick Start

### Prerequisites

- Azure DevOps account with repository access
- Python 3.11 or higher
- [Anthropic API Key](https://console.anthropic.com/) (free tier available)
- Azure CLI installed and authenticated

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/azure-forge-review.git
cd azure-forge-review

# 2. Run automated setup
./setup.sh

# 3. Test locally (optional)
make test-local

# 4. Deploy to Azure DevOps
make deploy-azure
```

**That's it!** Your next PR will automatically get reviewed. ✅

---

## 🎬 How It Works

When you create or update a Pull Request:

1. **Azure Pipeline Triggers** automatically
2. **Three Specialized Agents** analyze your code in parallel:
   - **🛡️ Sentinel** - Security vulnerabilities (SQL injection, XSS, auth bypass)
   - **🎨 Atlas** - Design quality (UX, accessibility, visual consistency)
   - **🧠 Forge** - Code quality (architecture, performance, maintainability)
3. **Results Posted** - Summary + inline comments appear in your PR

### Example: What You'll See

**Summary Comment:**
```markdown
🔍 Code Review Complete

📊 Analysis Summary:
• 🛡️ Sentinel: 2 critical, 1 high
• 🎨 Atlas: 0 critical, 2 medium
• 🧠 Forge: 1 high, 3 medium

💬 Inline Comments: 3 (threshold: high)
📝 Total Findings: 9

⚙️ Current threshold: high
Change in azure-pipelines.yml to show more/fewer inline comments
```

**Inline Comment Example:**
```markdown
🛡️ CRITICAL - SQL Injection Vulnerability

**File:** src/api/users.py:42
**Agent:** Sentinel (Security Review)

**Issue:**
User input is directly interpolated into SQL query without sanitization.

**Exploit Scenario:**
An attacker could execute arbitrary SQL commands by injecting malicious
input in the 'username' parameter:
  username = "admin' OR '1'='1"

**Recommendation:**
Use parameterized queries with prepared statements:
```python
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
```

**References:**
• [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
```

---

## ⚙️ Configuration

### Adjust Inline Comment Threshold

Control which findings appear as inline comments. Edit [`azure-pipelines.yml`](azure-pipelines.yml):

```yaml
variables:
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'high'  # Options: critical | high | medium | all
```

| Threshold | What Gets Posted as Inline Comments |
|-----------|-------------------------------------|
| `critical` | Only critical severity findings |
| `high` | Critical + high severity (default) |
| `medium` | Critical + high + medium |
| `all` | All findings (can be noisy) |

### Customize Templates

Want to change how comments look? Edit the Jinja2 templates:
- [`scripts/templates/summary.md.jinja2`](scripts/templates/summary.md.jinja2) - Summary format
- [`scripts/templates/finding.md.jinja2`](scripts/templates/finding.md.jinja2) - Inline comment format

See [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for detailed customization options.

---

## 🏗️ Architecture

```
PR Created/Updated
       ↓
Azure Pipeline (azure-pipelines.yml)
       ↓
┌──────┼──────┬─────────┐
↓      ↓      ↓         ↓
🛡️      🎨      🧠       git diff
Sentinel Atlas Forge     ↓
↓      ↓      ↓         ↓
security design code → Normalizer
.json  .json  .json     ↓
                 reviewResult.json
                        ↓
                  PR Publisher
                        ↓
        ┌───────────────┼──────────────┐
        ↓                              ↓
  Summary Comment              Inline Comments
  (top-level)                  (file-specific)
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Agent Runners** | Execute specialized review agents | [`scripts/agents/`](scripts/agents/) |
| **Normalizer** | Consolidate & deduplicate findings | [`scripts/normalize_results.py`](scripts/normalize_results.py) |
| **PR Publisher** | Post results to Azure DevOps | [`scripts/publish_to_pr.py`](scripts/publish_to_pr.py) |
| **Templates** | Format comments beautifully | [`scripts/templates/`](scripts/templates/) |
| **Azure Client** | Communicate with Azure DevOps API | [`scripts/utils/azure_devops_client.py`](scripts/utils/azure_devops_client.py) |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**DEPLOYMENT.md**](docs/DEPLOYMENT.md) | Detailed setup and deployment guide |
| [**TROUBLESHOOTING.md**](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [**CUSTOMIZATION.md**](docs/CUSTOMIZATION.md) | How to customize agents and templates |
| [**CONTRIBUTING.md**](CONTRIBUTING.md) | Development and contribution guidelines |

---

## 🐛 Troubleshooting

### No comments appear in my PR

**Quick fixes:**

```bash
# Check if configuration is correct
make validate-config

# View detailed logs from last run
make debug-last-run

# Test agents locally
make test-local
```

**Common causes:**
1. Threshold too restrictive (no findings met severity level)
2. Variable Group not configured correctly
3. Build Service lacks permissions

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

### Permission errors

Build Service needs `Contribute to Pull Requests` permission:

```bash
# Automated fix
make fix-permissions

# Or manually:
# Project Settings → Repos → Security
# → [Project] Build Service → "Contribute to pull requests" → Allow
```

---

## ❓ FAQ

<details>
<summary><strong>Does this replace human code review?</strong></summary>

No. This tool finds common issues automatically so humans can focus on business logic, architecture decisions, and design tradeoffs. Think of it as an extra team member who never gets tired.
</details>

<details>
<summary><strong>What if the API is down or rate-limited?</strong></summary>

The pipeline retries with exponential backoff. If all retries fail, the PR isn't blocked (fail-safe design). You'll see a warning in the pipeline logs.
</details>

<details>
<summary><strong>Can I disable specific agents?</strong></summary>

Yes. Comment out the corresponding step in [`azure-pipelines.yml`](azure-pipelines.yml):

```yaml
# - script: python scripts/agents/run_design_review.py
#   displayName: '🎨 Design Review (DISABLED)'
```

See [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for details.
</details>

<details>
<summary><strong>How much does it cost?</strong></summary>

Costs depend on PR size and Anthropic API pricing:
- Small PR (< 200 lines): ~$0.05-0.15
- Medium PR (200-500 lines): ~$0.15-0.30
- Large PR (500+ lines): ~$0.30-0.60

Anthropic's free tier may cover personal projects. Enterprise teams should use the paid tier for reliability.
</details>

<details>
<summary><strong>Is my code secure? Does it leave my infrastructure?</strong></summary>

The git diff is sent to Anthropic's API via HTTPS. Key security measures:
- Diffs are sanitized (secrets removed) before sending
- Only the changed code is analyzed, not your entire codebase
- No code is stored by this tool (stateless)
- Follow best practices: never commit secrets, API keys, or sensitive data

Review [.claude/rules/security.md](.claude/rules/security.md) for our security guidelines.
</details>

<details>
<summary><strong>Can I run this on GitHub instead of Azure DevOps?</strong></summary>

Currently Azure DevOps only. GitHub Actions support is planned for V2.0. The core agents work anywhere—only the PR publisher needs adaptation.
</details>

---

## 🗺️ Roadmap

### V1.0 - MVP (Current)
- ✅ Three specialized agents (Sentinel, Atlas, Forge)
- ✅ Azure DevOps PR integration
- ✅ Configurable inline comment threshold
- ✅ Automated setup and deployment
- ✅ Finding deduplication and normalization

### V2.0 - Analytics & Dashboard (Q2 2025)
- 📊 Web dashboard (React + TypeScript)
- 📈 Historical metrics and trends
- 💾 PostgreSQL persistence
- 🔔 Slack/Teams notifications
- 🔌 REST API for findings
- 🐙 GitHub Actions support

### V3.0 - Advanced Features (Q3 2025)
- 🤖 Auto-fix mode (generates fix PRs)
- 🎓 Fine-tuning with project-specific examples
- 🔗 SonarQube/Checkmarx integration
- 📦 Multi-repository support
- 🧪 Test generation suggestions

---

## 🤝 Contributing

We welcome contributions! Areas where you can help:

- **🔍 Agent Improvements** - Enhance detection accuracy
- **🎨 Templates** - Better comment formatting
- **📖 Documentation** - Tutorials, examples, translations
- **🐛 Bug Fixes** - Issues, edge cases, performance
- **✨ New Features** - Dashboard, integrations, analytics

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 💬 Support & Community

- **📖 Documentation**: [docs/](docs/)
- **🐛 Report Issues**: [GitHub Issues](https://github.com/your-org/azure-forge-review/issues)
- **💡 Discussions**: [GitHub Discussions](https://github.com/your-org/azure-forge-review/discussions)
- **📧 Email**: support@yourorg.com

---

## 🙏 Credits

Built with:
- [**Anthropic Claude**](https://www.anthropic.com/) - Advanced code analysis
- [**Azure DevOps REST API**](https://learn.microsoft.com/en-us/rest/api/azure/devops/) - PR integration
- [**Jinja2**](https://jinja.palletsprojects.com/) - Template rendering
- [**Python 3.11+**](https://www.python.org/) - Core implementation
- [**Rich**](https://rich.readthedocs.io/) - Beautiful terminal output

---

<div align="center">

**Made with precision, not hype. 🎯**

[Get Started](#-quick-start) • [Documentation](docs/) • [Contributing](CONTRIBUTING.md)

</div>
