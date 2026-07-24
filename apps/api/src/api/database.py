import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


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


@lru_cache(maxsize=1)
def engine() -> Engine:
    url = database_url()
    if url.startswith("sqlite"):
        connect_args: dict[str, object] = {"check_same_thread": False}
    else:
        # Fail fast when local Postgres is down so /ready and tests do not hang
        # on OS-level TCP timeouts (often 20-60s+ per attempt).
        connect_args = {"connect_timeout": 2}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=engine(), expire_on_commit=False)


def create_session() -> Session:
    """Create a new database session for background workers and scripts."""
    return session_factory()()


def database_session() -> Iterator[Session]:
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
