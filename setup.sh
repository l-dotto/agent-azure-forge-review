#!/bin/bash

# Azure Code Reviewer - Automated Setup Script
# This script configures everything needed to run the code review system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
trap 'log_error "Setup failed at line $LINENO. Rolling back..."; rollback; exit 1' ERR

rollback() {
    log_warn "Rolling back changes..."
    if [ -f ".env.backup" ]; then
        mv .env.backup .env
        log_info "Restored .env from backup"
    fi
}

# Banner
echo "=========================================="
echo "  Azure Code Reviewer - Setup"
echo "=========================================="
echo ""

# Step 1: Check prerequisites
log_info "Step 1/7: Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    log_error "Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi
log_info "Python version: $PYTHON_VERSION - OK"

if ! command -v git &> /dev/null; then
    log_error "Git is not installed"
    exit 1
fi
log_info "Git - OK"

if ! command -v az &> /dev/null; then
    log_warn "Azure CLI not installed. Install from: https://learn.microsoft.com/cli/azure/install-azure-cli"
    read -p "Continue without Azure CLI? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    log_info "Azure CLI - OK"
fi

# Step 2: Create directory structure
log_info "Step 2/7: Creating directory structure..."

mkdir -p scripts/{agents,utils,templates,config}
mkdir -p findings
mkdir -p tests/{unit,integration,fixtures}
mkdir -p docs/{guides,architecture,examples}

# Create __init__.py files
touch scripts/__init__.py
touch scripts/agents/__init__.py
touch scripts/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

log_info "Directory structure created"

# Step 3: Install Python dependencies
log_info "Step 3/7: Installing Python dependencies..."

if [ -f "requirements.txt" ]; then
    python3 -m pip install --upgrade pip
    pip install -r requirements.txt
    log_info "Dependencies installed successfully"
else
    log_error "requirements.txt not found"
    exit 1
fi

# Step 4: Configure environment variables
log_info "Step 4/7: Configuring environment variables..."

if [ -f ".env" ]; then
    log_warn ".env file already exists"
    read -p "Backup and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env .env.backup
        log_info "Backup created: .env.backup"
    else
        log_info "Keeping existing .env file"
        ENV_EXISTS=true
    fi
fi

if [ -z "$ENV_EXISTS" ]; then
    echo "# Azure Code Reviewer Configuration" > .env
    echo "" >> .env

    read -s -p "Enter your Anthropic API Key: " ANTHROPIC_KEY
    echo  # Add newline after silent input
    echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY" >> .env

    echo "" >> .env
    echo "# Azure DevOps Configuration" >> .env
    read -p "Enter Azure DevOps Organization URL (optional): " AZURE_ORG
    if [ ! -z "$AZURE_ORG" ]; then
        echo "AZURE_DEVOPS_ORG=$AZURE_ORG" >> .env
    fi

    read -p "Enter Azure DevOps Project (optional): " AZURE_PROJECT
    if [ ! -z "$AZURE_PROJECT" ]; then
        echo "AZURE_DEVOPS_PROJECT=$AZURE_PROJECT" >> .env
    fi

    echo "" >> .env
    echo "# Configuration" >> .env
    echo "INLINE_SEVERITY_THRESHOLD=high" >> .env

    log_info ".env file created"
fi

# Add python-dotenv if not in requirements
if ! grep -q "python-dotenv" requirements.txt; then
    echo "python-dotenv==1.0.0" >> requirements.txt
    pip install python-dotenv
fi

# Step 5: Validate API Key
log_info "Step 5/7: Validating Anthropic API Key..."

python3 -c "
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    print('ERROR: ANTHROPIC_API_KEY not found in .env')
    exit(1)

try:
    client = Anthropic(api_key=api_key)
    print('API Key validation: OK')
except Exception as e:
    print(f'ERROR: API Key validation failed: {e}')
    exit(1)
" || {
    log_error "API Key validation failed. Please check your key and try again."
    exit 1
}

# Step 6: Configure Azure DevOps (if Azure CLI is available)
if command -v az &> /dev/null; then
    log_info "Step 6/7: Configuring Azure DevOps..."

    # Check if logged in
    if ! az account show &> /dev/null; then
        log_warn "Not logged into Azure CLI"
        read -p "Login now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            az login
        else
            log_warn "Skipping Azure DevOps configuration"
        fi
    fi

    if az account show &> /dev/null; then
        read -p "Create Variable Group 'code-review-secrets'? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            source .env
            if [ ! -z "$AZURE_DEVOPS_ORG" ] && [ ! -z "$AZURE_DEVOPS_PROJECT" ]; then
                az devops configure --defaults organization="$AZURE_DEVOPS_ORG" project="$AZURE_DEVOPS_PROJECT"

                # Create variable group with secret flag
                az pipelines variable-group create \
                    --name code-review-secrets \
                    --variables ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
                    --authorize true \
                    --secret true || log_warn "Variable group creation failed (may already exist)"

                log_info "Azure DevOps configured"
            else
                log_warn "Azure DevOps org/project not set. Run manually: az devops configure"
            fi
        fi
    fi
else
    log_info "Step 6/7: Skipping Azure DevOps configuration (Azure CLI not available)"
fi

# Step 7: Create example config files
log_info "Step 7/7: Creating configuration templates..."

cat > scripts/config/config.example.yaml <<EOF
# Azure Code Reviewer Configuration
# Copy this file to config.yaml and customize

severity_thresholds:
  inline_comments: high  # critical | high | medium | all
  summary: all

agent_settings:
  timeout_seconds: 120
  retry_attempts: 3

filters:
  ignore_patterns:
    - "vendor/**"
    - "node_modules/**"
    - "*.generated.*"
    - "__pycache__/**"

  file_extensions:
    - ".py"
    - ".js"
    - ".ts"
    - ".tsx"
    - ".java"
    - ".go"
    - ".rs"

azure_devops:
  api_version: "7.1"
  max_comment_length: 5000
EOF

log_info "Configuration template created: scripts/config/config.example.yaml"

# Final validation
log_info "Running final validation..."
if [ -f "scripts/validate_setup.py" ]; then
    python3 scripts/validate_setup.py || log_warn "Validation script not yet implemented"
fi

echo ""
echo "=========================================="
log_info "Setup completed successfully"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review .env file and adjust settings if needed"
echo "  2. Run 'make test-local' to test agents locally"
echo "  3. Run 'make validate-config' to validate configuration"
echo "  4. Run 'make deploy-azure' to deploy the pipeline"
echo ""
echo "For help: make help"
echo ""
