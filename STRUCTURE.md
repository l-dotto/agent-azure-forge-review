# Project Structure

## Root Directory

```
azure-code-reviewer/
├── .env.example                    # Environment configuration template
├── setup.sh                        # Automated setup script (executable)
├── Makefile                        # Development commands
├── azure-pipelines.yml             # Azure Pipeline definition
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Test configuration
│
├── .claude/                        # Claude Code configuration
│   ├── agents/                     # Review agent definitions
│   │   ├── security-review-slash-command.md     (Sentinel)
│   │   ├── design-review-slash-command.md       (Atlas)
│   │   └── pragmatic-code-review-subagent.md    (Forge)
│   └── rules/                      # Development rules
│       ├── git-commit.md
│       ├── security.md
│       ├── api-standards.md
│       ├── frontend-security.md
│       ├── performance.md
│       ├── pipeline.md
│       └── aws-infrastructure.md
│
├── scripts/                        # Python implementation
│   ├── agents/                     # Agent runners (Phase 2-3)
│   ├── utils/                      # Utility modules (Phase 2-5)
│   ├── templates/                  # Jinja2 templates (Phase 5)
│   │   ├── summary.md.jinja2
│   │   └── finding.md.jinja2
│   ├── config/                     # Configuration files
│   │   └── config.example.yaml
│   ├── infra/                      # Infrastructure files
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── README.md
│   └── validate_setup.py           # Setup validation CLI
│
├── tests/                          # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── findings/                       # Generated findings (gitignored)
│   ├── .gitkeep
│   └── README.md
│
└── docs/                           # Documentation
    ├── guides/
    ├── architecture/
    └── examples/
```

## Key Files

### Phase 1 (Setup Básico) - COMPLETED

- [x] **setup.sh** - Interactive setup script with validation
- [x] **Makefile** - Simplified development commands
- [x] **requirements.txt** - Python dependencies including CLI/UX libraries
- [x] **scripts/validate_setup.py** - Configuration validation tool
- [x] **azure-pipelines.yml** - Pipeline with placeholder stages
- [x] **scripts/infra/Dockerfile** - Container for local testing
- [x] **scripts/infra/docker-compose.yml** - Docker orchestration
- [x] **scripts/templates/*.jinja2** - Comment templates
- [x] **.env.example** - Configuration template

### Next Phases

**Phase 2** (Security Review Agent):
- scripts/utils/git_diff_parser.py
- scripts/utils/markdown_parser.py
- scripts/agents/run_security_review.py

**Phase 3** (Design + Code Agents):
- scripts/agents/run_design_review.py
- scripts/agents/run_code_review.py

**Phase 4** (Normalizer):
- scripts/normalize_results.py
- scripts/utils/finding_deduplicator.py

**Phase 5** (PR Publisher):
- scripts/utils/azure_devops_client.py
- scripts/publish_to_pr.py

## Usage

### Quick Start

```bash
# Run automated setup
./setup.sh

# Validate configuration
make validate-config

# Test locally
make test-local

# Deploy to Azure DevOps
make deploy-azure
```

### Docker Usage

```bash
# Build image
make docker-build

# Run validation
make docker-run

# Run tests
make docker-test
```

### Development

```bash
# Install dependencies
make install

# Run tests
make test

# Lint code
make lint

# Format code
make format

# Clean generated files
make clean
```
