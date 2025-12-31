# Templates

This directory contains Jinja2 templates for generating PR comments.

## Available Templates

### `summary.md.jinja2`
Top-level summary comment posted to the PR with:
- Overview of all three agents (Sentinel, Atlas, Forge)
- Total finding counts by severity
- Inline comment threshold configuration
- Quick statistics

### `finding.md.jinja2`
Individual inline comment template for specific findings:
- Agent emoji (🛡️ Sentinel / 🎨 Atlas / 🧠 Forge)
- Severity badge
- File and line reference
- Description
- Exploit scenario (for security findings)
- Recommendation
- Links to relevant documentation

## Template Variables

Templates receive a context dictionary with:
- `findings`: List of finding dictionaries
- `threshold`: Current inline severity threshold
- `agent`: Agent name (security, design, code)
- `severity`: Finding severity level
- `file_path`: Path to file
- `line_number`: Line number
- `title`: Finding title
- `description`: Detailed description
- `recommendation`: Remediation guidance
- `links`: Related documentation links

## Usage

Templates are rendered by `scripts/publish_to_pr.py` using Jinja2.

Example:
```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('scripts/templates'))
template = env.get_template('summary.md.jinja2')
rendered = template.render(findings=findings, threshold='high')
```
