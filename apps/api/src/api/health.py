"""Liveness and readiness endpoints for platform dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Request, Response, status
from memovi_config.settings.api import ApiSettings
from memovi_search.domain.providers import EmbeddingProvider
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceRepository
from sqlalchemy import text

from api.database import create_session, engine
from api.document_processing import MEMORY_STORAGE_LABEL, MINIO_STORAGE_LABEL

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


def _check_embedding_provider(provider: EmbeddingProvider | None) -> ComponentCheck:
    try:
        if provider is None:
            return ComponentCheck(
                name="embedding_provider",
                status="down",
                detail="Embedding provider was not configured.",
            )
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
            detail=f"{provider.provider}/{provider.model} dims={vector.dimensions}",
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


_OBJECT_STORAGE_DOWN = (
    "Persistent object storage is unavailable (MinIO). "
    "Start MinIO with `docker compose up -d` or `task docker-up`."
)


def _check_object_storage(
    *,
    storage: object | None = None,
    backend: str | None = None,
    label: str | None = None,
) -> ComponentCheck:
    kind = (backend or "").strip().lower()
    is_memory = kind == "memory" or type(storage).__name__ == "InMemoryObjectStorage"
    if storage is None and not kind:
        return ComponentCheck(
            name="object_storage",
            status="down",
            detail="Object storage was not configured.",
        )
    if is_memory:
        return ComponentCheck(
            name="object_storage",
            status="up",
            detail=label or MEMORY_STORAGE_LABEL,
        )
    try:
        check_available = getattr(storage, "check_available", None)
        if callable(check_available):
            check_available()
        return ComponentCheck(
            name="object_storage",
            status="up",
            detail=label or MINIO_STORAGE_LABEL,
        )
    except Exception:
        return ComponentCheck(
            name="object_storage",
            status="down",
            detail=_OBJECT_STORAGE_DOWN,
        )


def run_readiness_checks(
    *,
    embedding_provider: EmbeddingProvider | None = None,
    object_storage: object | None = None,
    object_storage_backend: str | None = None,
    object_storage_label: str | None = None,
) -> list[ComponentCheck]:
    storage_check = _check_object_storage(
        storage=object_storage,
        backend=object_storage_backend,
        label=object_storage_label,
    )
    database = _check_database()
    if database.status == "down":
        # Avoid stacking multiple long connection attempts when Postgres is down.
        unavailable = "database unavailable"
        return [
            database,
            ComponentCheck(name="vector_search", status="down", detail=unavailable),
            _check_embedding_provider(embedding_provider),
            ComponentCheck(name="migrations", status="down", detail=unavailable),
            ComponentCheck(name="workspace", status="down", detail=unavailable),
            ComponentCheck(name="search_readiness", status="down", detail=unavailable),
            storage_check,
        ]
    return [
        database,
        _check_vector_search(),
        _check_embedding_provider(embedding_provider),
        _check_migrations(),
        _check_workspace(),
        _check_search_readiness(),
        storage_check,
    ]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict[str, Any]:
    embedding_provider = getattr(request.app.state, "embedding_provider", None)
    checks = run_readiness_checks(
        embedding_provider=embedding_provider,
        object_storage=getattr(request.app.state, "object_storage", None),
        object_storage_backend=getattr(request.app.state, "object_storage_backend", None),
        object_storage_label=getattr(request.app.state, "object_storage_label", None),
    )
    all_up = all(check.status == "up" for check in checks)
    if not all_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if all_up else "not_ready",
        "components": [check.as_dict() for check in checks],
        "environment": ApiSettings.from_environ(os.environ).environment,
    }
