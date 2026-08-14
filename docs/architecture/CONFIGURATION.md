# Configuration

Memovi loads process configuration through `packages/config` (`memovi_config`).
That package is the single source of truth for typed settings, environment parsing,
defaults, secret handling, and startup validation.

Domain packages may still expose package-level config objects (for example
`SearchEmbeddingConfig` and `IntelligenceConfig`) for domain-specific validation
and DI. Those objects read environment values through `memovi_config` rather than
calling `os.getenv` directly.

---

## Loading and startup validation

At API startup, `apps/api` calls `memovi_config.validate_configuration()` from
`api.bootstrap.validate_configuration()` before workers and providers start.

Validation:

- Loads every configuration domain into a single `Settings` aggregate
- Applies defaults for optional variables
- Rejects missing required values, invalid enums, invalid URLs, and invalid
  numeric values
- Fails fast on the first invalid domain (no partially valid startup)

```python
from memovi_config import load_settings, validate_configuration

settings = validate_configuration()  # raises ConfigurationError on failure
database_url = settings.database.url
```

Partial loaders (database URL only, storage only, embeddings only) exist for
call sites that must not enforce unrelated provider secrets. Full startup always
uses `validate_configuration()`.

---

## Secret handling

Secrets are wrapped in `SecretValue`:

- `str(secret)` and `repr(secret)` always redact to `***`
- Exception messages name the environment variable; they never include the value
- Database diagnostics use `DatabaseSettings.safe_url` (password redacted)
- Storage and provider settings redact credentials in `repr`

Supported secret sources: **environment variables only** for V1.

The desktop client does **not** collect, store, or transmit provider API keys.
Users configure `OPENAI_API_KEY` and `INTELLIGENCE_PROVIDER` on the API process
(typically `.env`), restart the API, then verify from **Settings → Diagnostics**.
Changing provider selection is process-start configuration; it is not applied at
runtime.

---

## Configuration domains

| Domain | Type | Purpose |
| --- | --- | --- |
| API | `ApiSettings` | Process environment label (`MEMOVI_ENV`) |
| Database | `DatabaseSettings` | Postgres / `DATABASE_URL` |
| Auth | `AuthSettings` | Session defaults (cookie name / TTL mirrors) |
| Search | `SearchSettings` | Reserved search process knobs |
| Embeddings | `EmbeddingsSettings` | Embedding provider selection |
| Models | `ModelsSettings` | Intelligence / reasoning provider selection |
| Storage | `StorageSettings` | MinIO / object storage |
| Capabilities | `CapabilitiesSettings` | Filesystem / terminal / git / browser roots + terminal policy |
| Connectors | `ConnectorsSettings` | Process-level connector settings (credentials stay env refs) |
| Observability | `ObservabilitySettings` | Environment label + log level |
| Desktop | `DesktopSettings` | API base URL for desktop / local tooling |

---

## Environment variables

### Required (effective)

None are strictly required for local development because historical local defaults
are preserved. Startup still validates that whatever is configured is well-formed.

In production, treat the following as required in practice:

| Variable | Domain | Notes |
| --- | --- | --- |
| `DATABASE_URL` or `POSTGRES_*` | Database | Reachable Postgres |
| `MINIO_*` | Storage | Reachable object storage (startup fails if MinIO is down unless `MEMOVI_OBJECT_STORAGE=memory` is set in a development `MEMOVI_ENV`) |
| `OPENAI_API_KEY` | Embeddings / Models | Required when provider is `openai` |
| `MEMOVI_FILESYSTEM_ROOTS` (etc.) | Capabilities | Required when locking capability roots; unset keeps temp/fallback behavior |

### Database

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | optional | composed from `POSTGRES_*` | Full SQLAlchemy URL (`postgresql+psycopg://…` or `sqlite…`) |
| `POSTGRES_USER` | optional | `memovi_app` | Used when `DATABASE_URL` unset |
| `POSTGRES_PASSWORD` | optional | local default | Secret |
| `POSTGRES_HOST` | optional | `127.0.0.1` | |
| `POSTGRES_PORT` | optional | `5432` | Integer 1–65535 |
| `POSTGRES_DB` | optional | `memovi` | |

### Storage (MinIO)

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `MINIO_SERVER_URL` | optional | `http://127.0.0.1:9000` | Absolute `http(s)` URL |
| `MINIO_ROOT_USER` | optional | local default | Secret access key |
| `MINIO_ROOT_PASSWORD` | optional | local default | Secret |
| `MINIO_BUCKET` | optional | `memovi-documents` | |
| `MINIO_REGION_NAME` | optional | `us-east-1` | |
| `MEMOVI_OBJECT_STORAGE` | optional | `minio` | `minio` \| `memory`. `memory` is allowed only when `MEMOVI_ENV` is `local`, `development`, `dev`, or `test`. |

Connectivity is checked at API startup. Invalid URL / blank credentials fail
configuration validation even if MinIO is down. If the backend is `minio` and
MinIO cannot be reached, startup fails with instructions to start Compose /
check `MINIO_SERVER_URL`, or to opt in to ephemeral in-memory storage for local
development only. There is no silent fallback. `/ready` includes an
`object_storage` component (`Persistent object storage: MinIO` or
`Development object storage: In-memory`).

### Embeddings

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SEARCH_EMBEDDING_PROVIDER` | optional | `fake` | `fake` \| `openai` \| `ollama` \| `sentence_transformer` |
| `SEARCH_EMBEDDING_MODEL` | optional | provider default | |
| `SEARCH_EMBEDDING_DIMENSIONS` | optional | `384` | Must match pgvector schema |
| `SEARCH_EMBEDDING_ENDPOINT` | optional | Ollama default when needed | Absolute `http(s)` URL |
| `SEARCH_EMBEDDING_API_KEY` | conditional | — | Secret; preferred for embeddings |
| `OPENAI_API_KEY` | conditional | — | Secret; used when embedding provider is `openai` and dedicated key unset |
| `SEARCH_EMBEDDING_TIMEOUT_SECONDS` | optional | `60` | Positive number |

### Models (Intelligence)

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `INTELLIGENCE_PROVIDER` | optional | `fake` | `fake` \| `openai` \| reserved providers |
| `INTELLIGENCE_MODEL` | optional | provider default | |
| `OPENAI_MODEL` | optional | `gpt-4o-mini` | Used when provider is `openai` and `INTELLIGENCE_MODEL` unset |
| `OPENAI_API_KEY` | conditional | — | Secret; required at startup when `INTELLIGENCE_PROVIDER=openai`. Never entered in the desktop client. |

### Capabilities

Roots are `os.pathsep`-separated absolute or relative paths. When a variable is
**set**, every entry must exist and be a directory (fail fast). When **unset**,
the API composition root keeps historical fallbacks (temp filesystem root, shared
roots for terminal/git/browser).

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `MEMOVI_FILESYSTEM_ROOTS` | optional | temp dir | Filesystem capability roots |
| `MEMOVI_TERMINAL_ROOTS` | optional | filesystem roots | Terminal cwd roots |
| `MEMOVI_GIT_ROOTS` | optional | filesystem roots | Git repo roots |
| `MEMOVI_BROWSER_DOWNLOAD_ROOTS` | optional | filesystem roots | Browser download roots |
| `MEMOVI_TERMINAL_ALLOWED_EXECUTABLES` | optional | unrestricted | Comma-separated allow list |
| `MEMOVI_TERMINAL_DENIED_EXECUTABLES` | optional | built-in deny defaults | Comma-separated deny list |
| `MEMOVI_TERMINAL_CONFIRM_EXECUTABLES` | optional | built-in confirm defaults | Comma-separated confirmation list |
| `MEMOVI_TERMINAL_DENIED_ARGUMENT_PATTERNS` | optional | built-in patterns | Semicolon-separated regexes |
| `MEMOVI_TERMINAL_DEFAULT_TIMEOUT_SECONDS` | optional | `30` | Default terminal timeout |
| `MEMOVI_TERMINAL_MAX_TIMEOUT_SECONDS` | optional | `300` | Terminal timeout ceiling |
| `MEMOVI_TERMINAL_MAX_STDOUT_BYTES` | optional | `1048576` | Stdout capture cap |
| `MEMOVI_TERMINAL_MAX_STDERR_BYTES` | optional | `1048576` | Stderr capture cap |
| `MEMOVI_TERMINAL_PREFER_ARGV` | optional | `true` | Prefer `shell=False` when practical |
| `MEMOVI_TERMINAL_ALLOW_SHELL` | optional | `true` | Allow `shell=True` fallback |

See [`TERMINAL_CAPABILITY.md`](TERMINAL_CAPABILITY.md) for policy semantics.

### API / observability / desktop

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `MEMOVI_ENV` | optional | `local` | Reported on `/ready` |
| `MEMOVI_LOG_LEVEL` | optional | `info` | `critical` \| `error` \| `warning` \| `info` \| `debug` |
| `MEMOVI_API_BASE` | optional | `http://127.0.0.1:8000` | Tooling / desktop alignment |

Desktop Vite builds also read `VITE_MEMOVI_API_BASE` (client-only; not validated by
`memovi_config`).

### Compose-only (not read by the API Python process)

`MINIO_API_PORT`, `MINIO_CONSOLE_PORT`, and `MINIO_BROWSER_REDIRECT_URL` are used
by Docker Compose / infra substitution. Redis is not used in V1 and has no
Compose or application environment variables.

---

## Package layout

```
packages/config/src/memovi_config/
  exceptions.py          ConfigurationError
  secrets.py             SecretValue
  env.py                 typed env helpers
  settings/
    __init__.py          Settings, load_settings, validate_configuration
    api.py
    database.py
    auth.py
    search.py
    embeddings.py
    models.py
    storage.py
    capabilities.py
    connectors.py
    observability.py
    desktop.py
```

---

## Related documents

- [`.env.example`](../../.env.example) — local development template
- [`SEARCH.md`](SEARCH.md) — embedding provider behavior and probes
- [`storage-architecture.md`](storage-architecture.md) — Postgres / MinIO ownership
- [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md) — desktop API base URL conventions
