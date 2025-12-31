---
paths:
  - src/**/*.ts
  - src/**/*.js
  - src/**/*.java
  - src/**/*.dart
  - infrastructure/**/*.tf
---

# Security Rules

## 1. Input Validation & Sanitization

- Validar absolutamente todas entradas do usuário.
- Proteger contra SQL Injection, XSS, HTML Injection e Header Injection.
- Nunca confiar no valor vindo do client (valor do pagamento, IDs, descontos).
- Usar schemas (Zod, class-validator, Joi).

## 2. Authentication & Authorization

- JWT assinado com RS256/ES256.
- Expiração curta + Refresh Token seguro (httpOnly + Secure).
- Aplicar RBAC e princípio do mínimo privilégio.
- Não expor dados sensíveis no token.

## 3. Cryptography

- AES-256 para dados sensíveis em repouso.
- Argon2id para hashes.
- Rotação automática de chaves via AWS KMS.
- Nunca criar algoritmos próprios.

## 4. Secure Logging

- Nunca logar: número de cartão, CVV, CPF completo, token, chave PIX.
- Logs devem conter request_id e trace_id.
- Uso obrigatório de mascaramento (\*\*\*\*).

## 5. Payments Security (Cartão e PIX)

- Cartões nunca armazenados, apenas tokenizados.
- PIX QR Dinâmico com expiração curta.
- Webhooks assinados com HMAC.
- Idempotência obrigatória para evitar pagamentos duplicados.

## 6. Protection Against Attacks

- Rate limiting (IP, device e fingerprint).
- Anti-fraude básico (score por comportamento).
- Proteção contra replay attack (nonce + expiração).
- WAF obrigatório (SQLi, XSS, bots).

## 7. Secrets Management

- Nada de segredos no código.
- Uso obrigatório de AWS Secrets Manager.
- Rotação periódica automatizada.
