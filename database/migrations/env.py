import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "packages" / "auth" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "documents" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "intelligence" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "memory" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "search" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "workspace" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "shared" / "src"))

from auth.infrastructure.persistence import Base as AuthBase  # noqa: E402
from documents.infrastructure.persistence import Base as DocumentsBase  # noqa: E402
from memovi_intelligence.infrastructure.persistence import Base as IntelligenceBase  # noqa: E402
from memovi_memory.infrastructure.persistence import Base as MemoryBase  # noqa: E402
from memovi_search.infrastructure.persistence import Base as SearchBase  # noqa: E402
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [
    AuthBase.metadata,
    DocumentsBase.metadata,
    IntelligenceBase.metadata,
    MemoryBase.metadata,
    SearchBase.metadata,
    WorkspaceBase.metadata,
]


def database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("POSTGRES_USER", "memovi_app")
    password = os.getenv("POSTGRES_PASSWORD", "memovi_local_pg_9f4c8e2d7a6b41c3")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "memovi")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
