---
paths:
  - infrastructure/**/*.tf
  - deployment/**/*.yaml
  - .aws/*.json
---

# AWS Infrastructure & Security Rules

## 1. Rede (VPC)

- Subnets privadas para backend e banco.
- Subnets públicas apenas para ALB/API Gateway.
- Bloquear tráfego lateral via NACLs.
- Security Groups com mínimo privilégio.

## 2. Compute

- ECS Fargate ou Lambda (nunca EC2 sem necessidade).
- Autoscaling por CPU, memória e TPS.
- Containers sempre não privilegiados.
- Imagens no ECR com scanning ativado.

## 3. Banco de Dados (RDS PostgreSQL)

- TLS obrigatório.
- Criptografar com KMS.
- Rotação automática de senhas via Secrets Manager.
- Acesso apenas via SG específico do backend.

## 4. S3

- Public Access Block ON.
- Versionamento ON.
- Criptografia SSE-KMS.
- Object Lock para documentos críticos.

## 5. Segurança

- AWS WAF ativado com regras:
  - SQLi
  - XSS
  - Bots maliciosos
  - String match customizada (3A, 3B, 3C)
- IAM com zero trust e MFA.
- Shield Standard habilitado.

## 6. Observabilidade

- CloudWatch Logs + métricas customizadas.
- X-Ray para tracing distribuído.
- Alarmes:
  - 5xx > 1%
  - Latência alta
  - Falhas de pagamento
