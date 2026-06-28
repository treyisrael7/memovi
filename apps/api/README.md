# Memovi API

The API application package is the backend composition root for Memovi.

It is responsible for assembling the FastAPI platform, registering routers, configuring application lifecycle behavior, and exposing operational endpoints such as health checks.

This package intentionally contains no authentication, repositories, database models, application services, domain logic, or business workflows.

Run the local API development server from the repository root:

```bash
task backend:dev
```

The health endpoint is available at `http://localhost:8000/health`.
