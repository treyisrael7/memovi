"""Liveness and readiness endpoints for platform dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response, status
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceRepository
from sqlalchemy import text

from api.database import create_session, engine

router = APIRouter(tags=["health"])


@dataclass(frozen=True, slots=True)
class ComponentCheck:
    name: str
    status: str
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "status": self.status}
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


def _check_database() -> ComponentCheck:
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return ComponentCheck(name="database", status="up")
    except Exception as exc:
        return ComponentCheck(name="database", status="down", detail=str(exc))


def _check_vector_search() -> ComponentCheck:
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM search_embeddings LIMIT 1"))
            if connection.dialect.name == "postgresql":
                connection.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                )
        return ComponentCheck(name="vector_search", status="up")
    except Exception as exc:
        return ComponentCheck(name="vector_search", status="down", detail=str(exc))


def _check_embedding_provider() -> ComponentCheck:
    try:
        provider = FakeEmbeddingProvider()
        vector = provider.embed("readiness-probe")
        if vector.dimensions <= 0:
            return ComponentCheck(
                name="embedding_provider",
                status="down",
                detail="Embedding provider returned empty dimensions.",
            )
        return ComponentCheck(
            name="embedding_provider",
            status="up",
            detail=f"{provider.provider}/{provider.model}",
        )
    except Exception as exc:
        return ComponentCheck(name="embedding_provider", status="down", detail=str(exc))


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[4]
    ini_path = root / "alembic.ini"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(root / "database" / "migrations"))
    return config


def _check_migrations() -> ComponentCheck:
    try:
        script = ScriptDirectory.from_config(_alembic_config())
        heads = set(script.get_heads())
        with engine().connect() as connection:
            context = MigrationContext.configure(connection)
            current = context.get_current_revision()
        if current is None:
            return ComponentCheck(
                name="migrations",
                status="down",
                detail="No alembic revision applied.",
            )
        if current not in heads:
            return ComponentCheck(
                name="migrations",
                status="down",
                detail=f"Current revision '{current}' is not at head {sorted(heads)}.",
            )
        return ComponentCheck(
            name="migrations",
            status="up",
            detail=current,
        )
    except Exception as exc:
        return ComponentCheck(name="migrations", status="down", detail=str(exc))


def _check_workspace() -> ComponentCheck:
    session = create_session()
    try:
        workspace = SqlAlchemyWorkspaceRepository(session).get_by_id(DEFAULT_WORKSPACE_ID)
        if workspace is None:
            return ComponentCheck(
                name="workspace",
                status="down",
                detail="Default workspace was not found.",
            )
        return ComponentCheck(name="workspace", status="up", detail=workspace.id.value)
    except Exception as exc:
        return ComponentCheck(name="workspace", status="down", detail=str(exc))
    finally:
        session.close()


def _check_search_readiness() -> ComponentCheck:
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM search_documents LIMIT 1"))
            if connection.dialect.name == "postgresql":
                connection.execute(
                    text(
                        "SELECT to_tsvector('english', 'readiness') @@ "
                        "plainto_tsquery('english', 'readiness')"
                    )
                )
        return ComponentCheck(name="search_readiness", status="up")
    except Exception as exc:
        return ComponentCheck(name="search_readiness", status="down", detail=str(exc))


def run_readiness_checks() -> list[ComponentCheck]:
    database = _check_database()
    if database.status == "down":
        # Avoid stacking multiple long connection attempts when Postgres is down.
        unavailable = "database unavailable"
        return [
            database,
            ComponentCheck(name="vector_search", status="down", detail=unavailable),
            _check_embedding_provider(),
            ComponentCheck(name="migrations", status="down", detail=unavailable),
            ComponentCheck(name="workspace", status="down", detail=unavailable),
            ComponentCheck(name="search_readiness", status="down", detail=unavailable),
        ]
    return [
        database,
        _check_vector_search(),
        _check_embedding_provider(),
        _check_migrations(),
        _check_workspace(),
        _check_search_readiness(),
    ]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    checks = run_readiness_checks()
    all_up = all(check.status == "up" for check in checks)
    if not all_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if all_up else "not_ready",
        "components": [check.as_dict() for check in checks],
        "environment": os.getenv("MEMOVI_ENV", "local"),
    }
