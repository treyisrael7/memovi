# Memovi Auth

Authentication and authorization domain boundary. This package owns the identity-related
domain, application, infrastructure, API, and event contracts for Memovi.

This package implements Memovi's local authentication foundation. Authentication exists
to establish ownership of knowledge in a self-hosted instance; it is not a generic SaaS
identity system.

The package uses secure HTTP-only session cookies, Argon2id password hashes, SQLAlchemy
repositories, and Alembic-managed PostgreSQL tables. It intentionally does not implement
JWT, OAuth, RBAC, or API keys.

## Layers

- `domain` contains auth business concepts, value objects, repository interfaces,
  domain events, domain exceptions, and domain services.
- `application` contains future use-case commands, queries, DTOs, and services.
- `api` contains transport-specific FastAPI routers, schemas, and dependencies.
- `infrastructure` contains future persistence, repository, security, and provider adapters.

The import package is `auth` because the package boundary is already clear from
`packages/auth`.
