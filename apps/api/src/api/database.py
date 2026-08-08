import os
from collections.abc import Iterator
from functools import lru_cache

from memovi_config.settings.database import DatabaseSettings
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    return DatabaseSettings.from_environ(os.environ).url


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
