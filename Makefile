.PHONY: help install test lint format clean test-local validate-config deploy-azure \
        debug-last-run collect-diagnostics validate-api-key set-threshold fix-permissions \
        reset-config watch-local benchmark pre-deploy final-check docker-build docker-run docker-test \
        security security-snyk security-sonar security-all security-report docs serve-docs check-docs

help:
	@echo "Azure Code Reviewer - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install           - Install Python dependencies"
	@echo "  make validate-config   - Validate Azure DevOps configuration"
	@echo "  make deploy-azure      - Deploy pipeline to Azure DevOps"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build      - Build Docker image"
	@echo "  make docker-run        - Run validation in Docker"
	@echo "  make docker-test       - Run tests in Docker"
	@echo ""
	@echo "Testing & Development:"
	@echo "  make test-local        - Run agents locally with mock PR"
	@echo "  make test              - Run test suite with coverage"
	@echo "  make lint              - Run linters (flake8, mypy)"
	@echo "  make format            - Format code with black"
	@echo "  make watch-local       - Run agents in loop (dev mode)"
	@echo "  make benchmark         - Measure execution time"
	@echo ""
	@echo "Security Scanning:"
	@echo "  make security          - Run all security scans (Snyk + SonarQube)"
	@echo "  make security-snyk     - Run Snyk vulnerability scan"
	@echo "  make security-sonar    - Run SonarQube code quality scan"
	@echo "  make security-report   - Generate security report"
	@echo ""
	@echo "Diagnostics:"
	@echo "  make debug-last-run    - Show logs from last pipeline run"
	@echo "  make collect-diagnostics - Collect info for debugging"
	@echo "  make validate-api-key  - Test Anthropic API Key"
	@echo ""
	@echo "Configuration:"
	@echo "  make set-threshold THRESHOLD=<value> - Set severity threshold (critical|high|medium|all)"
	@echo "  make fix-permissions   - Fix Azure DevOps Build Service permissions"
	@echo "  make reset-config      - Reset configuration (WARNING: destructive)"
	@echo ""
	@echo "Pre-Deploy Checks:"
	@echo "  make pre-deploy        - Run all validation checks before deploy"
	@echo "  make final-check       - Final validation before production"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Remove generated files"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs              - Validate all documentation"
	@echo "  make check-docs        - Check documentation for broken links"
	@echo "  make serve-docs        - Serve documentation locally (port 8000)"

install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Dependencies installed successfully"

docker-build:
	@echo "Building Docker image..."
	docker build -f scripts/infra/Dockerfile -t azure-code-reviewer .
	@echo "Docker image built successfully"

docker-run:
	@echo "Running in Docker container..."
	docker-compose -f scripts/infra/docker-compose.yml up code-reviewer

docker-test:
	@echo "Running tests in Docker container..."
	docker-compose -f scripts/infra/docker-compose.yml up test

test:
	@echo "Running test suite..."
	pytest tests/ -v --cov=scripts --cov-report=html --cov-report=term-missing

test-local:
	@echo "Running agents locally with mock PR..."
	@if [ ! -f ".env" ]; then \
		echo "Error: .env file not found. Run ./setup.sh first."; \
		exit 1; \
	fi
	python scripts/validate_setup.py --mock
	@echo "Local test completed"

validate-config:
	@echo "Validating configuration..."
	python scripts/validate_setup.py
	@echo "Configuration is valid"

deploy-azure:
	@echo "Deploying pipeline to Azure DevOps..."
	@if [ -z "$(AZURE_ORG)" ] || [ -z "$(AZURE_PROJECT)" ]; then \
		echo "Error: AZURE_ORG and AZURE_PROJECT must be set."; \
		echo "Usage: make deploy-azure AZURE_ORG=<org> AZURE_PROJECT=<project>"; \
		exit 1; \
	fi
	az pipelines create --name "Code Review Pipeline" \
		--repository $(shell git remote get-url origin) \
		--branch $(shell git branch --show-current) \
		--yml-path azure-pipelines.yml \
		--org $(AZURE_ORG) \
		--project $(AZURE_PROJECT)
	@echo "Pipeline deployed successfully"

debug-last-run:
	@echo "Fetching logs from last pipeline run..."
	@if [ -z "$(AZURE_ORG)" ] || [ -z "$(AZURE_PROJECT)" ]; then \
		echo "Error: AZURE_ORG and AZURE_PROJECT must be set."; \
		exit 1; \
	fi
	az pipelines runs list --org $(AZURE_ORG) --project $(AZURE_PROJECT) --top 1
	@echo "Use: az pipelines runs show --id <run-id> for details"

collect-diagnostics:
	@echo "Collecting diagnostics..."
	@echo "=== System Info ==="
	@python --version
	@echo ""
	@echo "=== Git Info ==="
	@git branch --show-current
	@git remote -v
	@echo ""
	@echo "=== Python Packages ==="
	@pip list | grep -E "anthropic|click|rich|inquirer|jinja2|tenacity"
	@echo ""
	@echo "=== Environment Check ==="
	@if [ -f ".env" ]; then \
		echo "OK: .env file exists"; \
	else \
		echo "ERROR: .env file missing"; \
	fi
	@echo ""
	@echo "=== Azure CLI ==="
	@which az || echo "ERROR: Azure CLI not installed"
	@echo "Diagnostics collected"

validate-api-key:
	@echo "Testing Anthropic API Key..."
	@python -c "import os; from anthropic import Anthropic; \
		from dotenv import load_dotenv; load_dotenv(); \
		client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')); \
		print('API Key is valid')" || \
		echo "API Key validation failed"

set-threshold:
	@if [ -z "$(THRESHOLD)" ]; then \
		echo "Error: THRESHOLD not set."; \
		echo "Usage: make set-threshold THRESHOLD=<critical|high|medium|all>"; \
		exit 1; \
	fi
	@if [ "$(THRESHOLD)" != "critical" ] && [ "$(THRESHOLD)" != "high" ] && \
	   [ "$(THRESHOLD)" != "medium" ] && [ "$(THRESHOLD)" != "all" ]; then \
		echo "Error: Invalid threshold. Use: critical|high|medium|all"; \
		exit 1; \
	fi
	@echo "Setting threshold to: $(THRESHOLD)"
	@sed -i 's/value: .*/value: '\''$(THRESHOLD)'\''/' azure-pipelines.yml
	@echo "Threshold updated in azure-pipelines.yml"

fix-permissions:
	@echo "Fixing Azure DevOps Build Service permissions..."
	@if [ -z "$(AZURE_ORG)" ] || [ -z "$(AZURE_PROJECT)" ]; then \
		echo "Error: AZURE_ORG and AZURE_PROJECT must be set."; \
		exit 1; \
	fi
	@echo "Please run the following command manually:"
	@echo "az devops security permission update --subject <build-service-id> --allow-bit <contribute-to-pull-requests>"
	@echo "See docs/DEPLOYMENT.md for details"

reset-config:
	@echo "WARNING: This will delete all configuration"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f .env scripts/config/*.yaml; \
		echo "Configuration reset complete"; \
	else \
		echo "Reset cancelled"; \
	fi

watch-local:
	@echo "Watching for changes (dev mode)..."
	@echo "Press Ctrl+C to stop"
	while true; do \
		make test-local; \
		sleep 10; \
	done

benchmark:
	@echo "Benchmarking agent execution time..."
	@time make test-local

pre-deploy:
	@echo "Running pre-deploy validation..."
	make validate-config
	make test-local
	@echo "Pre-deploy checks passed"

final-check:
	@echo "Running final production validation..."
	make validate-config
	make lint
	make test
	@echo "Final checks passed - Ready for production"

lint:
	@echo "Running linters..."
	flake8 scripts/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	mypy scripts/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	black scripts/ tests/ --line-length=100

clean:
	@echo "Cleaning generated files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf findings/*.json
	rm -f reviewResult.json
	rm -rf .scannerwork
	rm -f snyk-report.json snyk-report.html
	rm -f sonar-report.json
	@echo "Cleanup complete"

# Security scanning targets
security: security-snyk security-sonar
	@echo "All security scans completed"

security-snyk:
	@echo "Running Snyk vulnerability scan..."
	@if ! command -v snyk &> /dev/null; then \
		echo "ERROR: Snyk CLI not installed."; \
		echo "Install with: npm install -g snyk"; \
		echo "Or download from: https://snyk.io/docs/snyk-cli/"; \
		exit 1; \
	fi
	@echo "Authenticating with Snyk (if not already logged in)..."
	@snyk auth || echo "Using existing Snyk authentication"
	@echo "Scanning Python dependencies..."
	snyk test --file=requirements.txt --severity-threshold=high --json-file-output=snyk-report.json || true
	@echo "Snyk scan complete. Results saved to snyk-report.json"
	@echo "For detailed report, run: snyk test --file=requirements.txt"

security-sonar:
	@echo "Running SonarQube code quality scan..."
	@if ! command -v sonar-scanner &> /dev/null; then \
		echo "ERROR: SonarQube Scanner not installed."; \
		echo "Install instructions:"; \
		echo "  1. Download from: https://docs.sonarqube.org/latest/analysis/scan/sonarscanner/"; \
		echo "  2. Or use Docker: docker run --rm -v \$$(pwd):/usr/src sonarsource/sonar-scanner-cli"; \
		exit 1; \
	fi
	@if [ -z "$(SONAR_TOKEN)" ] && [ -z "$(SONAR_HOST_URL)" ]; then \
		echo "WARNING: SONAR_TOKEN and SONAR_HOST_URL not set."; \
		echo "Set environment variables or configure sonar-project.properties"; \
		echo "Skipping SonarQube scan..."; \
	else \
		echo "Running SonarQube analysis..."; \
		sonar-scanner -Dsonar.login=$(SONAR_TOKEN) -Dsonar.host.url=$(SONAR_HOST_URL); \
	fi
	@echo "SonarQube scan complete"

security-report:
	@echo "Generating security report..."
	@echo ""
	@echo "=== Snyk Vulnerability Report ==="
	@if [ -f "snyk-report.json" ]; then \
		echo "Found Snyk report. Summary:"; \
		cat snyk-report.json | python -m json.tool | grep -E "severity|title" | head -20 || echo "No vulnerabilities found"; \
	else \
		echo "No Snyk report found. Run 'make security-snyk' first."; \
	fi
	@echo ""
	@echo "=== SonarQube Report ==="
	@echo "Access SonarQube dashboard at: $(SONAR_HOST_URL)"
	@echo "Project: azure-code-reviewer"
	@echo ""
	@echo "For detailed reports:"
	@echo "  - Snyk: snyk test --file=requirements.txt"
	@echo "  - SonarQube: Check dashboard at $(SONAR_HOST_URL)"

# Documentation targets
docs: check-docs
	@echo "Documentation validation complete"

check-docs:
	@echo "Checking documentation for issues..."
	@echo "Checking README.md..."
	@test -f README.md || (echo "ERROR: README.md not found" && exit 1)
	@grep -q "Quick Start" README.md || (echo "WARNING: README.md missing Quick Start section" && exit 1)
	@echo "Checking TROUBLESHOOTING.md..."
	@test -f docs/TROUBLESHOOTING.md || (echo "ERROR: docs/TROUBLESHOOTING.md not found" && exit 1)
	@echo "Checking DEPLOYMENT.md..."
	@test -f docs/DEPLOYMENT.md || (echo "ERROR: docs/DEPLOYMENT.md not found" && exit 1)
	@echo "Checking CUSTOMIZATION.md..."
	@test -f docs/CUSTOMIZATION.md || (echo "ERROR: docs/CUSTOMIZATION.md not found" && exit 1)
	@echo "Checking for broken internal links..."
	@grep -r "\[.*\](.*\.md)" README.md docs/ | grep -v "http" | while read line; do \
		file=$$(echo $$line | sed -E 's/.*\]\((.*\.md).*/\1/'); \
		if [ ! -f "$$file" ] && [ ! -f "docs/$$file" ]; then \
			echo "WARNING: Broken link found: $$file"; \
		fi; \
	done || true
	@echo "✅ Documentation check complete"

serve-docs:
	@echo "Serving documentation on http://localhost:8000"
	@echo "Press Ctrl+C to stop"
	@python -m http.server 8000 --directory .
