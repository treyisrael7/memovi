# Memovi Auth

Authentication and authorization domain boundary. This package owns the identity-related
domain, application, infrastructure, API, and event contracts for Memovi.

This package currently defines the architectural foundation only. It intentionally contains
no authentication flow, login behavior, JWT handling, OAuth integration, password hashing,
persistence models, repository implementations, or auth endpoints.

## Layers

- `domain` contains auth business concepts, value objects, repository interfaces,
  domain events, domain exceptions, and domain services.
- `application` contains future use-case commands, queries, DTOs, and services.
- `api` contains transport-specific FastAPI routers, schemas, and dependencies.
- `infrastructure` contains future persistence, repository, security, and provider adapters.

The import package is `auth` because the package boundary is already clear from
`packages/auth`.
