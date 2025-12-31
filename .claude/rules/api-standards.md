---
paths:
  - src/api/**/*.ts
  - src/modules/**/*.ts
  - src/controllers/**/*.ts
---

# API Standards (Finanças + Pagamentos)

## 1. Estrutura da API

- Seguir Clean Architecture ou Hexagonal.
- Separar controllers, use-cases, domain e infra.
- Uso obrigatório de DTOs validados.

## 2. Boas Práticas de Rotas

- Todas as rotas protegidas por autenticação.
- Respostas com estrutura padronizada:
  - success
  - code
  - timestamp
  - correlation_id

## 3. Comunicação com PSP (MercadoPago, Cielo, Pix)

- Retry com backoff exponencial.
- Timeout de 3–5s.
- Circuit breaker obrigatório.
- Validar assinatura e integridade de webhooks.

## 4. Idempotência

- Cada requisição de pagamento deve ter chave idempotente única.
- Evitar duplicidade por CPF / valor / débito / timestamp.

## 5. Documentação

- OpenAPI/Swagger atualizado.
- Versionamento obrigatório (v1, v2…).

## 6. Observabilidade

- Logging estruturado.
- Trace distribuído com trace_id.
- Métricas customizadas (latência, TPS, falhas de pagamento).
