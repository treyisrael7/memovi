# Local Infrastructure

Memovi uses Docker Compose for local infrastructure. The Compose stack provides only shared platform services; it does not build or run backend API or client application containers.

## Usage

Create a local environment file from the template when you want to override ports or credentials:

```bash
cp .env.example .env
```

Start the services:

```bash
docker compose up -d
```

Stop the services without deleting data:

```bash
docker compose down
```

Delete local service data:

```bash
docker compose down -v
```

The default credentials are intentionally stronger than common local examples, but they are still development credentials. Replace them in `.env` for any shared environment.

## Network

All services join the `memovi_internal` Docker network. The network is marked `internal: true` so containers on it are isolated from external Docker networks by default.

For local developer access, service ports are published only on `127.0.0.1`. This makes the services reachable from the host machine while avoiding broad LAN exposure.

## PostgreSQL

PostgreSQL is the authoritative relational database for durable Memovi data.

- Service name: `postgres`
- Image: `pgvector/pgvector:pg18`
- Container port: `5432`
- Host binding: `127.0.0.1:${POSTGRES_PORT:-5432}`
- Database: `${POSTGRES_DB:-memovi}`
- User: `${POSTGRES_USER:-memovi_app}`
- Password: `${POSTGRES_PASSWORD:-memovi_local_pg_9f4c8e2d7a6b41c3}`
- Volume: `memovi_postgres_data`
- Health check: `pg_isready` against the configured database and user

The `pgvector/pgvector:pg18` image keeps local PostgreSQL 18 ready for future vector extension usage. The Compose stack does not create schemas, migrations, tables, or application data. Apply Alembic migrations with `task db:migrate` to create Auth, Documents, Memory, and Search tables.

Redis is not used in V1. Document processing uses a PostgreSQL-backed job table
and an in-process worker; domain events use an in-process dispatcher. Distributed
queues or Redis Streams remain future architectural options, not local Compose
services.

## MinIO

MinIO provides local S3-compatible object storage for uploaded files and generated artifacts.

- Service name: `minio`
- Image: `minio/minio:latest`
- API container port: `9000`
- Console container port: `9001`
- API host binding: `127.0.0.1:${MINIO_API_PORT:-9000}`
- Console host binding: `127.0.0.1:${MINIO_CONSOLE_PORT:-9001}`
- Root user: `${MINIO_ROOT_USER:-memovi_minio_admin}`
- Root password: `${MINIO_ROOT_PASSWORD:-memovi_local_minio_5c7f1e9a3b6d4a82}`
- Region: `${MINIO_REGION_NAME:-us-east-1}`
- Volume: `memovi_minio_data`
- Health check: MinIO live health endpoint

The Compose stack does not create buckets or policies. Those should be added later through infrastructure initialization code or explicit setup scripts when application storage contracts exist.

The API defaults to MinIO (`MEMOVI_OBJECT_STORAGE=minio`). If MinIO is not running, startup fails instead of silently storing uploads in process memory. For ephemeral local work only, set `MEMOVI_OBJECT_STORAGE=memory` with `MEMOVI_ENV=local`.
