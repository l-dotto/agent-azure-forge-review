# Performance & Optimization Rules

## 1. Database Queries

- Usar paginação (`Pageable`) para listas grandes
- Evitar N+1 queries com `@EntityGraph` ou JOIN FETCH
- Indexar colunas usadas em WHERE, JOIN e ORDER BY
- Usar queries nativas para operações complexas
- Evitar `SELECT *`, buscar apenas campos necessários

## 2. Caching

- Cache com Redis para dados frequentes
- Usar `@Cacheable`, `@CacheEvict`, `@CachePut`
- Definir TTL apropriado
- Cache de queries pesadas

## 3. API Response

- Comprimir respostas (gzip)
- Usar DTOs leves (não retornar entidades JPA)
- Implementar paginação em todas as listagens
- ETags para cache HTTP

## 4. Async Processing

- Operações longas em threads separadas (`@Async`)
- Usar `CompletableFuture` para paralelismo
- Filas (SQS) para processamento desacoplado

## 5. JVM & Spring

- Configurar heap adequado (-Xmx, -Xms)
- Pool de conexões otimizado (HikariCP)
- Thread pool configurado
- Lazy initialization quando apropriado