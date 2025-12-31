# Azure Code Reviewer

**Automated code review system for Azure DevOps Pull Requests powered by Claude.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure DevOps](https://img.shields.io/badge/Azure%20DevOps-Compatible-blue)](https://azure.microsoft.com/en-us/products/devops/)

## Overview

Azure Code Reviewer is an intelligent, automated code review system that integrates seamlessly with Azure DevOps Pull Requests. It leverages three specialized review agents to provide comprehensive feedback on security, design, and code quality.

### Key Features

- **Three Specialized Agents**
  - **Sentinel**: Security vulnerability detection and exploit analysis
  - **Atlas**: UX, accessibility, and design review
  - **Forge**: Pragmatic code quality and architecture review

- **Seamless Integration**
  - Automatic execution on every PR update
  - Inline comments on specific code lines
  - Configurable severity thresholds
  - Summary reports with actionable insights

- **Professional Output**
  - Structured findings with severity levels
  - Clear exploit scenarios for security issues
  - Actionable recommendations
  - Links to relevant documentation

- **Enterprise Ready**
  - No secrets in logs or commits
  - Sanitized diffs before processing
  - Rate limiting and retry logic
  - Comprehensive error handling

## Quick Start

### Prerequisites

- Azure DevOps organization with repository access
- Python 3.11 or higher
- Anthropic API key (Claude)
- Build Service with "Contribute to Pull Requests" permission

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/azure-code-reviewer.git
   cd azure-code-reviewer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Azure DevOps**

   a. Create a Variable Group named `code-review-secrets`:
   ```bash
   Azure DevOps → Pipelines → Library → + Variable group
   ```

   b. Add the Anthropic API key as a secret:
   ```
   Name: ANTHROPIC_API_KEY
   Value: sk-ant-...
   [x] Keep this value secret
   ```

   c. Grant Build Service permissions:
   ```
   Project Settings → Repositories → [Your Repo] → Security
   → [Project] Build Service
   → Set "Contribute to pull requests" to Allow
   ```

4. **Enable Branch Policy**
   ```
   Repos → Branches → main → Branch Policies
   → Build Validation → +
   → Select "Azure Code Reviewer" pipeline
   ```

### Configuration

Control inline comment behavior with the `INLINE_SEVERITY_THRESHOLD` variable in [azure-pipelines.yml](azure-pipelines.yml):

```yaml
variables:
  - name: INLINE_SEVERITY_THRESHOLD
    value: 'high'  # Options: critical | high | medium | all
```

- `critical`: Only critical severity findings get inline comments
- `high`: Critical and high severity findings (default)
- `medium`: Critical, high, and medium severity findings
- `all`: All findings get inline comments

## How It Works

```
Developer pushes to PR
         ↓
Azure Pipeline triggered
         ↓
┌────────┼────────┬──────────┐
↓        ↓        ↓          ↓
Sentinel Atlas   Forge    Git diff
(Security)(Design)(Code)     ↓
↓        ↓        ↓          ↓
findings/security.json       ↓
findings/design.json         ↓
findings/code.json           ↓
         ↓                   ↓
    Normalizer ← ← ← ← ← ← ← ┘
         ↓
  reviewResult.json
         ↓
   PR Publisher
         ↓
┌────────┴────────┐
↓                 ↓
Summary         Inline
Comment        Comments
```

### Agent Specialization

**Sentinel (Security Review)**
- SQL injection, XSS, authentication bypass
- Exploitable vulnerabilities with proof-of-concept scenarios
- Security best practices validation
- Model: Claude Sonnet 4.5

**Atlas (Design Review)**
- UX patterns and user experience
- Accessibility (WCAG compliance)
- Visual consistency and design systems
- Model: Claude Sonnet 4.5

**Forge (Code Review)**
- Architecture and design patterns
- Code quality and maintainability
- Performance considerations
- Model: Claude Opus 4.5 (deeper analysis)

## Project Structure

```
azure-code-reviewer/
├── .claude/
│   ├── agents/              # Agent prompt templates
│   ├── rules/               # Project coding rules
│   └── settings.json        # Claude configuration
├── .github/
│   ├── ISSUE_TEMPLATE/      # Bug report and feature request templates
│   └── workflows/           # GitHub Actions (if migrating from Azure)
├── docs/
│   ├── guides/              # User guides and tutorials
│   ├── architecture/        # Technical documentation
│   └── examples/            # Usage examples
├── scripts/
│   ├── agents/              # Agent runner scripts
│   ├── utils/               # Utilities (parsers, Azure client)
│   └── templates/           # Jinja2 templates for PR comments
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test data
├── azure-pipelines.yml      # Main pipeline configuration
├── requirements.txt         # Python dependencies
├── pytest.ini               # Test configuration
└── README.md                # This file
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
make test

# Run linters
make lint

# Format code
make format
```

### Running Tests

```bash
# All tests with coverage
pytest tests/ -v --cov=scripts --cov-report=html

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

### Code Quality

This project maintains high code quality standards:
- Black for code formatting
- Flake8 for linting
- MyPy for type checking
- Pytest for testing (>80% coverage required)
- Pre-commit hooks for validation

## Roadmap

### Version 1.0 (Current - MVP)
- Three specialized review agents
- Azure DevOps PR integration
- Configurable inline comment threshold
- JSON output for future extensibility

### Version 2.0 (Planned)
- Web dashboard (React + TypeScript)
- PostgreSQL persistence for analytics
- REST API for querying results
- Slack/Teams notifications
- Historical metrics and trends

### Version 3.0 (Future)
- Fine-tuned agents with project examples
- Auto-fix mode (generates correction PRs)
- SonarQube/Checkmarx integration
- Multi-repository support

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Coding standards
- Commit message format
- Pull request process

## Security

Security is a top priority. Please:
- Never commit secrets, API keys, or sensitive data
- Review [.claude/rules/security.md](.claude/rules/security.md)
- Report security vulnerabilities privately to maintainers

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

## Credits

Built with:
- [Anthropic Claude](https://www.anthropic.com/claude) - Advanced language model
- [Azure DevOps](https://azure.microsoft.com/en-us/products/devops/) - CI/CD platform
- [Python 3.11+](https://www.python.org/) - Core implementation

---

**Status**: MVP in development | See [PLANO_IMPLEMENTACAO.md](PLANO_IMPLEMENTACAO.md) for detailed implementation plan
