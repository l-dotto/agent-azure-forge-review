# Git & Commit Rules

## Metadado

- Data de referência: 2025-12-11
- Autor do guia: Luan Dotto
- Objetivo: garantir histórico limpo, rastreabilidade, segurança e governança para projetos críticos de pagamento (PIX, cartão, integrações PSP, infra AWS).

## 1. Estrutura dos Commits

- Cada commit deve representar **uma única mudança lógica**.
- Não misturar responsabilidades (ex.: refactor + feature).
- Commits grandes devem ser quebrados em passos lógicos e intitulados.
- Nunca citar a ClaudeAi
- Não fazer commit na Master, criar branch com nome adequado para que possamos abrir PR na Azure Devops

## 2. Padrão de Mensagens (Conventional Commits) — **OBRIGATÓRIO**

- Formato:
- Tipos permitidos:
- `feat:` → nova funcionalidade
- `fix:` → correção de bug
- `chore:` → manutenção/ops
- `refactor:` → refatoração sem mudança comportamental
- `test:` → adição/alteração de testes
- `docs:` → documentação
- `perf:` → melhoria de performance
- `ci:` → pipeline/CI changes
- `security:` → correção/ajuste de segurança
- `revert:` → reversão de commit
- Regras:
- Linha de título até **72 caracteres**.
- Escopo opcional, porém recomendado (ex.: `payment`, `infra`, `api`).

## 3. Corpo do Commit — quando necessário (regras)

- Explicar **o que**, **por que** e **como** (não repetir o diff).
- Incluir:
- contexto do problema;
- trade-offs e implicações;
- passos de teste manual (se aplicável).
- Obrigatório para mudanças críticas: arquitetura, segurança, infra, pagamentos, bancos de dados.

### Exemplo:

feat(payment): add idempotency middleware for PIX

Add table pix_idempotency and middleware that:
• validates idempotency-key header
• prevents duplicate charges for identical requests
• logs PSP correlation-id for audit

## 4. Regras de Segurança (commits & histórico)

- **Proibido** commitar:
  - chaves, secrets, certificados, .env com valores sensíveis;
  - dumps de banco com dados reais;
  - dados de cartão (PAN, CVV), CPF/CNPJ completos.
- Se um segredo vazar:
  1. Remover imediatamente (commit + PR).
  2. Rotacionar credenciais afetadas (Secrets Manager / PSP).
  3. Abrir incidente e notificar security/SRE.
  4. Reescrever histórico localmente se apropriado (`git rebase -i`) e coordenar equipe — **não reescrever main remoto sem processo**.

## 5. Branching Strategy (convencionado)

- Nomes:
  - `feature/<descricao-curta>`
  - `fix/<descricao-curta>`
  - `hotfix/<descricao-curta>`
  - `refactor/<descricao-curta>`
  - `release/<versao>`
- `main` = sempre estável, deployments aprovados.
- `develop` ou `integration` = integração contínua (se usar GitFlow).
- Hotfix: merge direto em `main` e em seguida merge de volta para `develop`.

## 6. Pull Requests (PR)

- PRs pequenos e focados (ideal < 400 linhas de diff).
- Template mínimo obrigatório no PR:
  - Descrição do que muda e por que;
  - Issue/ticket referenciado;
  - Como testar (passos);
  - Checklist de impacto (DB, infra, contratos, migração);
  - Screenshots / resultado do `terraform plan` quando aplica.
- Revisores obrigatórios:
  - 1 Tech Lead
  - 1 Security reviewer (quando altera pagamentos/infra)
  - 1 QA para features críticas

## 7. Merge / Rebase

- Preferir **rebase** para manter histórico linear em PRs.
- Merge commits permitidos para:
  - releases;
  - hotfixes críticos onde histórico de merge é necessário.
- Ao reescrever histórico (rebase/amend), coordenar equipe e evitar forçar (`git push --force`) em branches compartilhadas sem aviso.

## 8. Qualidade do Histórico

- Evitar mensagens vagas: `"update"`, `"fix"`, `"teste"`.
- Evitar commits com linguagem inapropriada ou irrelevante.
- Manter commits com propósito claro e atomicidade.

## 9. Commits Relacionados a Infra / Terraform / AWS

- Cada mudança infra deve ser isolada em branch própria.
- Commit deve incluir:
  - `terraform plan` output (resumido) ou link para artefato;
  - descrição do impacto (VPC, SG, RDS, IAM).
- Não commitar arquivos gerados (state file, .tfstate).
- Mudanças IAM devem listar permissões adicionadas/removidas e justificativa.

## 10. Automação e Hooks

- Implementar hooks locais / CI:
  - `pre-commit` para lint, formatação e scans básicos;
  - `commit-msg` para validar Conventional Commits;
  - CI gates: lint → tests → security-scan → build → deploy-stage.
- Ferramentas recomendadas:
  - commitlint (conventional commits)
  - husky / pre-commit
  - trivy / snyk / semgrep (dependências e segurança)

## 11. Política de Reversão

- `revert:` deve ser usado para reverter commits problemáticos com justificativa clara.
- Hotfix urgente: criar branch `hotfix/<id>` e seguir processo de aprovação rápida.
- Após revert, investigar causa raiz e abrir issue para correção definitiva.

## 12. Critérios de Rejeição Imediata de Commit/PR

- Contém segredos ou dados sensíveis.
- Mensagem de commit vazia ou vaga.
- PR sem descrição ou sem steps para teste.
- Mudanças grandes sem divisão lógica.
- Alterações em infra/segurança sem `terraform plan` ou justificativa.

## 13. Templates Úteis (rápido)

- Commit curto (título):
