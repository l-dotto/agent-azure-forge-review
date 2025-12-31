# Contributing to Azure Code Reviewer

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Be respectful, professional, and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, Azure DevOps version)
   - Logs or screenshots if applicable

### Suggesting Features

1. Check existing [Issues](../../issues) and [Discussions](../../discussions)
2. Create a new issue with:
   - Clear use case description
   - Expected behavior
   - Why this would be valuable
   - Possible implementation approach (optional)

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Follow our coding standards (see below)
4. Write tests for new functionality
5. Update documentation as needed
6. Commit with clear, conventional commit messages
7. Push and create a PR with:
   - Description of changes
   - Related issue(s)
   - Test results
   - Screenshots/examples (if applicable)

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/azure-code-reviewer.git
cd azure-code-reviewer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## Coding Standards

### Python Style

- Follow PEP 8
- Use `black` for formatting: `black scripts/`
- Use `flake8` for linting: `flake8 scripts/`
- Use type hints where appropriate
- Maximum line length: 100 characters

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agents): add retry logic for Claude API
fix(parser): handle edge case in markdown parsing
docs(readme): update installation instructions
test(utils): add tests for git diff parser
```

**IMPORTANT:** Never mention AI/LLM/Claude in commit messages or PR descriptions intended for production use.

### Testing

- Write unit tests for all new functions
- Maintain test coverage above 80%
- Use meaningful test names: `test_parse_security_finding_with_missing_severity`
- Mock external dependencies (Claude API, Azure DevOps API)

### Documentation

- Update README.md for user-facing changes
- Update docs/ for architectural changes
- Add docstrings to all public functions
- Include code examples where helpful

## Security

- Never commit secrets, API keys, or sensitive data
- Review [.claude/rules/security.md](.claude/rules/security.md) before contributing
- Report security vulnerabilities privately to maintainers

## Project Structure

```
scripts/
  agents/       - Agent runners (Security, Design, Code)
  utils/        - Utilities (parsers, Azure client, git)
  templates/    - Jinja2 templates for PR comments

tests/
  unit/         - Unit tests
  integration/  - Integration tests
  fixtures/     - Test data

docs/
  guides/       - User guides
  architecture/ - Technical architecture
  examples/     - Usage examples
```

## Getting Help

- Check [docs/](docs/) for documentation
- Ask questions in [Discussions](../../discussions)
- Join our community chat (link TBD)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
