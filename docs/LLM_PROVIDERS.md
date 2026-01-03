# LLM Provider Configuration

The Azure Code Reviewer supports multiple LLM providers, allowing you to choose the AI service that best fits your needs.

## Supported Providers

| Provider | Model Examples | Best For |
|----------|----------------|----------|
| **Anthropic Claude** (default) | `claude-sonnet-4-5-20250929`, `claude-opus-4-5-20251101` | Security analysis, deep code review |
| **OpenAI GPT** | `gpt-4-turbo-preview`, `gpt-4` | General code review, fast responses |
| **Azure OpenAI** | `gpt-4`, `gpt-35-turbo` | Enterprise deployments, data residency |
| **Google Gemini** | `gemini-pro`, `gemini-ultra` | Cost-effective, multimodal analysis |

---

## Configuration

### 1. Anthropic Claude (Default)

**Environment Variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Local Testing:**
```bash
python scripts/agents/run_security_review.py \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929 \
  --output findings/security.json
```

**Azure Pipelines:**
```yaml
variables:
  - group: code-review-secrets  # Contains ANTHROPIC_API_KEY
  - name: LLM_PROVIDER
    value: 'anthropic'
```

---

### 2. OpenAI GPT

**Installation:**
```bash
pip install openai==1.6.1
```

Or uncomment in `requirements.txt`:
```python
# openai==1.6.1  # Uncomment for OpenAI/Azure OpenAI support
```

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-proj-...
LLM_PROVIDER=openai
```

**Local Testing:**
```bash
python scripts/agents/run_security_review.py \
  --provider openai \
  --model gpt-4-turbo-preview \
  --output findings/security.json
```

**Azure Pipelines:**
```yaml
variables:
  - group: code-review-secrets
    # Add variable: OPENAI_API_KEY
  - name: LLM_PROVIDER
    value: 'openai'
```

---

### 3. Azure OpenAI

**Installation:**
```bash
pip install openai==1.6.1
```

**Environment Variables:**
```bash
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4
LLM_PROVIDER=azure_openai
```

**Local Testing:**
```bash
python scripts/agents/run_security_review.py \
  --provider azure_openai \
  --azure-endpoint https://your-resource.openai.azure.com \
  --deployment gpt-4 \
  --output findings/security.json
```

**Azure Pipelines:**
```yaml
variables:
  - group: code-review-secrets
    # Add variables:
    #   AZURE_OPENAI_API_KEY
    #   AZURE_OPENAI_ENDPOINT
    #   AZURE_OPENAI_DEPLOYMENT
  - name: LLM_PROVIDER
    value: 'azure_openai'
```

---

### 4. Google Gemini

**Installation:**
```bash
pip install google-generativeai==0.3.2
```

Or uncomment in `requirements.txt`:
```python
# google-generativeai==0.3.2  # Uncomment for Gemini support
```

**Environment Variables:**
```bash
GOOGLE_API_KEY=AIza...
LLM_PROVIDER=gemini
```

**Local Testing:**
```bash
python scripts/agents/run_security_review.py \
  --provider gemini \
  --model gemini-pro \
  --output findings/security.json
```

**Azure Pipelines:**
```yaml
variables:
  - group: code-review-secrets
    # Add variable: GOOGLE_API_KEY
  - name: LLM_PROVIDER
    value: 'gemini'
```

---

## Provider Auto-Detection

If you don't specify `--provider`, the system auto-detects based on environment variables:

1. If `LLM_PROVIDER` is set → use that provider
2. Else if `OPENAI_API_KEY` is set → use OpenAI
3. Else if `AZURE_OPENAI_API_KEY` is set → use Azure OpenAI
4. Else if `GOOGLE_API_KEY` is set → use Gemini
5. Else → default to Anthropic

---

## Cost Comparison (Approximate)

| Provider | Model | Input ($/1M tokens) | Output ($/1M tokens) |
|----------|-------|--------------------:|---------------------:|
| Anthropic | Claude Sonnet 4.5 | $3 | $15 |
| Anthropic | Claude Opus 4.5 | $15 | $75 |
| OpenAI | GPT-4 Turbo | $10 | $30 |
| Azure OpenAI | GPT-4 | $30 | $60 |
| Google | Gemini Pro | $0.50 | $1.50 |

*Note: Prices are approximate and subject to change. Check provider documentation for current rates.*

---

## Recommended Configuration

### For Security Reviews (Sentinel)
**Best:** Anthropic Claude Sonnet 4.5
- Superior vulnerability detection
- Detailed exploit scenarios
- Lower false-positive rate

**Budget:** Google Gemini Pro
- 10x cheaper than Claude
- Adequate for common vulnerabilities

### For Code Quality (Forge)
**Best:** Anthropic Claude Opus 4.5
- Deep architectural analysis
- Comprehensive design feedback

**Fast:** OpenAI GPT-4 Turbo
- Faster responses
- Good for high-frequency PRs

### For Design Reviews (Atlas)
**Best:** Anthropic Claude Sonnet 4.5
- Strong UX/accessibility insights
- Visual design understanding

---

## Environment Configuration Examples

### .env Example (Local Development)

```bash
# Choose ONE provider:

# Option 1: Anthropic (default)
ANTHROPIC_API_KEY=sk-ant-api03-...
LLM_PROVIDER=anthropic

# Option 2: OpenAI
# OPENAI_API_KEY=sk-proj-...
# LLM_PROVIDER=openai

# Option 3: Azure OpenAI
# AZURE_OPENAI_API_KEY=your-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT=gpt-4
# LLM_PROVIDER=azure_openai

# Option 4: Google Gemini
# GOOGLE_API_KEY=AIza...
# LLM_PROVIDER=gemini

# Azure DevOps Configuration
AZURE_DEVOPS_ORG=https://dev.azure.com/your-org
AZURE_DEVOPS_PROJECT=your-project
INLINE_SEVERITY_THRESHOLD=high
```

### Azure Variable Group Setup

```bash
# Create Variable Group
az pipelines variable-group create \
  --name code-review-secrets \
  --variables \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --authorize true \
  --secret true

# Or for OpenAI:
az pipelines variable-group create \
  --name code-review-secrets \
  --variables \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    LLM_PROVIDER="openai" \
  --authorize true \
  --secret true
```

---

## Switching Providers

To switch providers, simply update the environment variables:

```bash
# Local (.env file)
LLM_PROVIDER=openai

# Azure Pipelines (Variable Group)
az pipelines variable-group variable update \
  --group-name code-review-secrets \
  --name LLM_PROVIDER \
  --value openai
```

No code changes required!

---

## Troubleshooting

### "Provider not found" Error
- Ensure the provider package is installed (check `requirements.txt`)
- Verify `LLM_PROVIDER` environment variable is set correctly

### "Authentication failed" Error
- Check API key is correct and not expired
- For Azure OpenAI, verify endpoint URL format
- Ensure Variable Group has correct secret names

### "Model not found" Error
- Verify model name matches provider's available models
- For Azure OpenAI, use deployment name (not model name)

### High Costs
- Switch to cheaper provider (Gemini for budget)
- Use lower-tier models (e.g., GPT-3.5 instead of GPT-4)
- Enable caching (future feature)

---

## CLI Examples

### Test All Providers

```bash
# Test Anthropic
python scripts/agents/run_security_review.py --provider anthropic --output test-anthropic.json

# Test OpenAI
python scripts/agents/run_security_review.py --provider openai --output test-openai.json

# Test Azure OpenAI
python scripts/agents/run_security_review.py \
  --provider azure_openai \
  --azure-endpoint https://your.openai.azure.com \
  --deployment gpt-4 \
  --output test-azure.json

# Test Gemini
python scripts/agents/run_security_review.py --provider gemini --output test-gemini.json
```

### Compare Results

```bash
# Run same PR with different providers
for provider in anthropic openai gemini; do
  python scripts/agents/run_security_review.py \
    --provider $provider \
    --output findings/security-$provider.json
done

# Compare findings counts
jq '.metadata.total_findings' findings/security-*.json
```

---

## Future Enhancements

- [ ] Local LLM support (Llama 3, Mistral)
- [ ] Multi-provider ensemble (combine results)
- [ ] Cost tracking and budgets
- [ ] Provider fallback on errors
- [ ] Response caching

---

## Support

For provider-specific issues:
- Anthropic: https://docs.anthropic.com/claude/reference
- OpenAI: https://platform.openai.com/docs
- Azure OpenAI: https://learn.microsoft.com/azure/ai-services/openai
- Google Gemini: https://ai.google.dev/docs

For system integration issues, open an issue on GitHub.