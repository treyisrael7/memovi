"""Durable SQLAlchemy processing job queue tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import (
    DocumentRecord,
    DocumentVersionRecord,
    ProcessingJobRecord,
)
from documents.infrastructure.queue import SqlAlchemyProcessingJobQueue
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def durable_queue() -> tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DocumentsBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    queue = SqlAlchemyProcessingJobQueue(factory, poll_interval_seconds=0.05)
    yield queue, factory
    engine.dispose()


def _seed_pending_job(
    factory: sessionmaker[Session],
    *,
    status: str = ProcessingStatus.PENDING.value,
    claimed_at: datetime | None = None,
) -> str:
    job_id = str(uuid4())
    document_id = str(uuid4())
    version_id = str(uuid4())
    now = datetime.now(UTC)
    with factory() as session:
        session.add(
            DocumentRecord(
                id=document_id,
                workspace_id=str(uuid4()),
                name="notes.md",
                mime_type="text/markdown",
                source_type="upload",
                created_at=now,
            )
        )
        session.add(
            DocumentVersionRecord(
                id=version_id,
                document_id=document_id,
                version_number=1,
                storage_key=f"docs/{document_id}/{version_id}",
                created_at=now,
            )
        )
        session.add(
            ProcessingJobRecord(
                id=job_id,
                document_id=document_id,
                document_version_id=version_id,
                status=status,
                attempt=1,
                available_at=now,
                claimed_at=claimed_at,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return job_id


@pytest.mark.asyncio
async def test_durable_queue_claims_pending_jobs(
    durable_queue: tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]],
) -> None:
    queue, factory = durable_queue
    job_id = _seed_pending_job(factory)

    queue.enqueue(job_id, attempt=1, request_id="req-1", workspace_id="ws-1")
    claimed = await asyncio.wait_for(queue.dequeue(), timeout=2.0)

    assert claimed is not None
    assert claimed.processing_job_id == job_id
    assert claimed.attempt == 1
    assert claimed.request_id == "req-1"
    assert claimed.workspace_id == "ws-1"

    with factory() as session:
        record = session.get(ProcessingJobRecord, job_id)
        assert record is not None
        assert record.claimed_at is not None
        assert record.status == ProcessingStatus.PENDING.value

    await queue.close()
    assert await queue.dequeue() is None


@pytest.mark.asyncio
async def test_durable_queue_survives_without_in_memory_enqueue(
    durable_queue: tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]],
) -> None:
    """Pending DB rows are claimable after restart even if enqueue never ran."""
    queue, factory = durable_queue
    job_id = _seed_pending_job(factory)

    claimed = await asyncio.wait_for(queue.dequeue(), timeout=2.0)
    assert claimed is not None
    assert claimed.processing_job_id == job_id
    await queue.close()


@pytest.mark.asyncio
async def test_durable_queue_recovers_interrupted_jobs(
    durable_queue: tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]],
) -> None:
    queue, factory = durable_queue
    job_id = _seed_pending_job(factory, status=ProcessingStatus.EXTRACTING.value)

    claimed = await asyncio.wait_for(queue.dequeue(), timeout=2.0)
    assert claimed is not None
    assert claimed.processing_job_id == job_id

    with factory() as session:
        record = session.get(ProcessingJobRecord, job_id)
        assert record is not None
        assert record.status == ProcessingStatus.PENDING.value

    await queue.close()


@pytest.mark.asyncio
async def test_durable_queue_prevents_double_claim(
    durable_queue: tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]],
) -> None:
    queue, factory = durable_queue
    job_id = _seed_pending_job(factory)
    queue.enqueue(job_id)

    first = await asyncio.wait_for(queue.dequeue(), timeout=2.0)
    assert first is not None
    assert first.processing_job_id == job_id

    second = queue._claim_next()
    assert second is None
    await queue.close()


@pytest.mark.asyncio
async def test_durable_queue_retry_updates_attempt(
    durable_queue: tuple[SqlAlchemyProcessingJobQueue, sessionmaker[Session]],
) -> None:
    queue, factory = durable_queue
    job_id = _seed_pending_job(factory)
    queue.enqueue(job_id, attempt=1)
    claimed = await asyncio.wait_for(queue.dequeue(), timeout=2.0)
    assert claimed is not None

    with factory() as session:
        record = session.get(ProcessingJobRecord, job_id)
        assert record is not None
        record.status = ProcessingStatus.EXTRACTING.value
        session.commit()

    queue.enqueue(job_id, attempt=2, request_id="retry")
    retried = await asyncio.wait_for(queue.dequeue(), timeout=2.0)
    assert retried is not None
    assert retried.attempt == 2
    assert retried.request_id == "retry"
    await queue.close()
