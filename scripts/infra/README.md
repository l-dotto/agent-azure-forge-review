# Infrastructure

This directory contains infrastructure-as-code and containerization files.

## Files

### Docker

- **Dockerfile** - Container image for running the code review system
- **docker-compose.yml** - Orchestration for local testing and development

## Usage

### Build and Run with Docker Compose

```bash
# From project root
cd scripts/infra

# Run validation
docker-compose up code-reviewer

# Run tests
docker-compose up test

# Development shell
docker-compose up dev
```

### Build Docker Image Manually

```bash
# From project root
docker build -f scripts/infra/Dockerfile -t azure-code-reviewer .

# Run validation
docker run --rm -v $(pwd)/.env:/app/.env:ro azure-code-reviewer
```

## Environment Variables

Required environment variables (set in .env file):

- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `INLINE_SEVERITY_THRESHOLD` - Severity threshold (default: high)

## Azure DevOps Configuration

For Azure DevOps deployment, infrastructure files will be added in future phases:

- Terraform/Bicep templates (Phase 6+)
- ARM templates for Azure resources
- Pipeline variable group definitions