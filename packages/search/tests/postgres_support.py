import os

import pytest
from memovi_search.infrastructure.persistence.models import Base
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def postgres_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url and explicit_url.startswith("postgresql"):
        return explicit_url

    user = os.getenv("POSTGRES_USER", "memovi_app")
    password = os.getenv("POSTGRES_PASSWORD", "memovi_local_pg_9f4c8e2d7a6b41c3")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "memovi")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def postgres_available() -> bool:
    try:
        engine = create_engine(
            postgres_database_url(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is required for full-text and vector search tests.",
)


def ensure_pgvector_extension(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def build_postgres_session_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine
