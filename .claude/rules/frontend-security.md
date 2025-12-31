---
paths:
  - web/**/*.tsx
  - web/**/*.ts
  - mobile/**/*.dart
---

# Frontend Security Rules

## 1. Proteção de Token

- Nunca armazenar tokens em localStorage.
- Usar cookies httpOnly + Secure.
- Rotação automática via refresh seguro.

## 2. Manipulação de Dados Sensíveis

- Não exibir dados completos:
  - CPF: **_._**.**\*-**
  - Cartão: \***\* \*\*** \*\*\*\* 1234
- Nunca manter dados no estado global.

## 3. Sanitização

- Sanitizar inputs contra XSS.
- validar CPF/CNPJ/valores apenas no backend.

## 4. UI/UX de Pagamento

- Evitar inputs livres para valores ou datas.
- Sempre usar componentes restritivos:
  - masked input
  - dropdowns e pickers seguros

## 5. Performance

- Lazy loading
- Otimização de imagens
- Redução de re-renders
