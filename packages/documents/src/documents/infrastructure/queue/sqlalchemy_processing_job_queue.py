"""Durable processing job queue backed by ``documents_processing_jobs``."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from memovi_observability import get_metrics_recorder
from sqlalchemy import or_
from sqlalchemy.orm import Session as OrmSession

from documents.application.ports import QueuedProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence.models import ProcessingJobRecord

LOGGER = logging.getLogger(__name__)

_INTERRUPTED_STATUSES = (
    ProcessingStatus.EXTRACTING.value,
    ProcessingStatus.NORMALIZING.value,
)


class SqlAlchemyProcessingJobQueue:
    """Postgres/SQLite-backed queue that survives process restarts.

    Pending rows in ``documents_processing_jobs`` are the source of truth.
    ``enqueue`` updates durable metadata and wakes the poller. ``dequeue``
    atomically claims the next pending job (``FOR UPDATE SKIP LOCKED`` on
    PostgreSQL) so future multi-worker deployments cannot double-process.
    """

    def __init__(
        self,
        session_factory: Callable[[], OrmSession],
        *,
        poll_interval_seconds: float = 0.25,
        claim_lease_seconds: float = 300.0,
    ) -> None:
        self._session_factory = session_factory
        self._poll_interval_seconds = poll_interval_seconds
        self._claim_lease = timedelta(seconds=claim_lease_seconds)
        self._closed = False
        self._wakeup = asyncio.Event()
        self._recovered = False

    def enqueue(
        self,
        processing_job_id: str,
        *,
        attempt: int = 1,
        request_id: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("Processing job queue is closed.")

        now = datetime.now(UTC)
        session = self._session_factory()
        try:
            record = session.get(ProcessingJobRecord, processing_job_id)
            if record is None:
                LOGGER.warning(
                    "Ignoring enqueue for missing processing job %s",
                    processing_job_id,
                )
                return

            if record.status == ProcessingStatus.CANCELLED.value:
                LOGGER.info(
                    "Ignoring enqueue for cancelled processing job %s",
                    processing_job_id,
                )
                return

            record.attempt = attempt
            record.request_id = request_id
            record.workspace_id = workspace_id
            record.available_at = now
            record.claimed_at = None
            # Retries reset via domain before enqueue; tolerate pending-only.
            if (
                record.status != ProcessingStatus.PENDING.value
                and record.status in _INTERRUPTED_STATUSES
            ):
                record.status = ProcessingStatus.PENDING.value
                record.started_at = None
                record.completed_at = None
                record.failure_reason = None
            record.updated_at = now
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        self._record_queue_depth()
        self._wakeup.set()

    async def dequeue(self) -> QueuedProcessingJob | None:
        while not self._closed:
            if not self._recovered:
                self._recover_interrupted_jobs()
                self._recovered = True

            claimed = self._claim_next()
            if claimed is not None:
                return claimed

            self._wakeup.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._wakeup.wait(),
                    timeout=self._poll_interval_seconds,
                )

        return None

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._wakeup.set()

    def pending_count(self) -> int:
        session = self._session_factory()
        try:
            return (
                session.query(ProcessingJobRecord)
                .filter(ProcessingJobRecord.status == ProcessingStatus.PENDING.value)
                .count()
            )
        finally:
            session.close()

    def _claim_next(self) -> QueuedProcessingJob | None:
        now = datetime.now(UTC)
        stale_before = now - self._claim_lease
        session = self._session_factory()
        try:
            query = (
                session.query(ProcessingJobRecord)
                .filter(ProcessingJobRecord.status == ProcessingStatus.PENDING.value)
                .filter(
                    or_(
                        ProcessingJobRecord.available_at.is_(None),
                        ProcessingJobRecord.available_at <= now,
                    )
                )
                .filter(
                    or_(
                        ProcessingJobRecord.claimed_at.is_(None),
                        ProcessingJobRecord.claimed_at < stale_before,
                    )
                )
                .order_by(ProcessingJobRecord.created_at.asc())
            )
            bind = session.get_bind()
            dialect_name = bind.dialect.name if bind is not None else ""
            if dialect_name == "postgresql":
                record = query.with_for_update(skip_locked=True).first()
            else:
                record = query.with_for_update().first()

            if record is None:
                session.commit()
                return None

            record.claimed_at = now
            record.updated_at = now
            session.commit()
            get_metrics_recorder().increment("memovi.documents.processing.claimed")
            self._record_queue_depth()
            return QueuedProcessingJob(
                processing_job_id=record.id,
                attempt=record.attempt,
                request_id=record.request_id,
                workspace_id=record.workspace_id,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _recover_interrupted_jobs(self) -> None:
        """Return mid-flight jobs to pending after an unclean shutdown."""
        now = datetime.now(UTC)
        session = self._session_factory()
        try:
            interrupted = (
                session.query(ProcessingJobRecord)
                .filter(ProcessingJobRecord.status.in_(_INTERRUPTED_STATUSES))
                .all()
            )
            for record in interrupted:
                record.status = ProcessingStatus.PENDING.value
                record.claimed_at = None
                record.available_at = now
                record.started_at = None
                record.completed_at = None
                record.updated_at = now
                LOGGER.warning(
                    "Recovered interrupted processing job %s to pending after restart",
                    record.id,
                )

            stale_claims = (
                session.query(ProcessingJobRecord)
                .filter(ProcessingJobRecord.status == ProcessingStatus.PENDING.value)
                .filter(ProcessingJobRecord.claimed_at.is_not(None))
                .all()
            )
            for record in stale_claims:
                record.claimed_at = None
                record.available_at = now
                record.updated_at = now

            if interrupted or stale_claims:
                session.commit()
                get_metrics_recorder().increment(
                    "memovi.documents.processing.recovered",
                    value=float(len(interrupted) + len(stale_claims)),
                )
            else:
                session.commit()
        except Exception:
            session.rollback()
            LOGGER.exception("Failed to recover interrupted processing jobs")
            raise
        finally:
            session.close()

    def _record_queue_depth(self) -> None:
        try:
            depth = self.pending_count()
        except Exception:
            LOGGER.exception("Failed to read processing queue depth")
            return
        get_metrics_recorder().histogram(
            "memovi.documents.processing.queue_depth",
            float(depth),
        )
