"""Unit coverage for API-boundary workspace resolution."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from api.database import database_session as api_database_session
from api.workspace_context import WORKSPACE_HEADER, get_active_workspace_id
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def test_workspace_header_resolution() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    explicit = WorkspaceId.new()

    with Session(engine) as session:
        session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.add(
            WorkspaceRecord(
                id=explicit.value,
                name="Explicit",
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        session.commit()

    def database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = FastAPI()
    app.dependency_overrides[api_database_session] = database_session

    @app.get("/active-workspace")
    def active_workspace(
        workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    ) -> dict[str, str]:
        return {"workspace_id": workspace_id.value}

    with TestClient(app) as client:
        omitted = client.get("/active-workspace")
        assert omitted.status_code == 200
        assert omitted.json()["workspace_id"] == DEFAULT_WORKSPACE_ID.value

        explicit_response = client.get(
            "/active-workspace",
            headers={WORKSPACE_HEADER: explicit.value},
        )
        assert explicit_response.status_code == 200
        assert explicit_response.json()["workspace_id"] == explicit.value

        missing = client.get(
            "/active-workspace",
            headers={WORKSPACE_HEADER: WorkspaceId.new().value},
        )
        assert missing.status_code == 404

        invalid = client.get(
            "/active-workspace",
            headers={WORKSPACE_HEADER: "not-a-uuid"},
        )
        assert invalid.status_code == 422

    engine.dispose()
