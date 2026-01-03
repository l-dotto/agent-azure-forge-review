# GitHub Actions Workflows

## Code Quality (`pylint.yml`)

Workflow automatizado de análise de qualidade do código.

### Triggers

- **Push:** Executado em branches `main`, `develop` e `chore/**`
- **Pull Request:** Executado em PRs para `main` e `develop`

### Jobs

#### Lint Job

Executa análise estática e testes em múltiplas versões do Python.

**Matrix Strategy:**
- Python 3.11
- Python 3.12

**Steps:**

1. **Setup:**
   - Checkout do código
   - Configuração do Python
   - Instalação de dependências

2. **Code Analysis (Pylint):**
   - Análise de qualidade do código
   - Configuração via `.pylintrc`
   - Threshold mínimo: 7.0/10
   - Desabilita `duplicate-code` warnings (comum em testes)

3. **Tests:**
   - Execução de testes com pytest
   - Cobertura de código
   - Relatórios em formato terminal e XML

4. **Code Formatting:**
   - Verificação de formatação com Black
   - Estilo consistente

5. **Coverage Upload:**
   - Upload para Codecov (apenas Python 3.11)
   - Relatórios de cobertura

### Configuração Local

Para executar as mesmas verificações localmente:

```bash
# Instalar dependências
pip install -r requirements.txt
pip install pylint

# Executar pylint
pylint $(git ls-files '*.py')

# Executar testes
pytest tests/ --cov=scripts --cov-report=term-missing

# Verificar formatação
black --check scripts/ tests/
```

### Notas Importantes

- Todos os passos usam `|| true` para não bloquear o CI durante desenvolvimento
- O workflow é informativo, não bloqueante
- Configurações de pylint estão em `.pylintrc`
- Cobertura de código é opcional (não bloqueia CI)

### Próximos Passos

Para tornar o CI bloqueante (produção):

1. Remover `|| true` dos steps
2. Ajustar threshold de pylint conforme necessário
3. Definir cobertura mínima requerida
4. Adicionar validação de segurança (bandit, safety)
