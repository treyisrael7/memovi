from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from documents.domain.entities import ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.value_objects import DocumentId
from documents.infrastructure.persistence.models import ProcessingJobRecord


class SqlAlchemyProcessingJobRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(self, job_id: str) -> ProcessingJob | None:
        record = self._session.get(ProcessingJobRecord, job_id)
        if record is None:
            return None
        return self._to_domain(record)

    def get_by_document_id(self, document_id: DocumentId) -> ProcessingJob | None:
        record = (
            self._session.query(ProcessingJobRecord)
            .filter(ProcessingJobRecord.document_id == document_id.value)
            .order_by(ProcessingJobRecord.created_at.desc())
            .first()
        )
        if record is None:
            return None
        return self._to_domain(record)

    def get_latest_by_document_ids(
        self,
        document_ids: Sequence[DocumentId],
    ) -> dict[str, ProcessingJob]:
        if not document_ids:
            return {}
        ids = [document_id.value for document_id in document_ids]
        records = (
            self._session.query(ProcessingJobRecord)
            .filter(ProcessingJobRecord.document_id.in_(ids))
            .order_by(ProcessingJobRecord.created_at.desc())
            .all()
        )
        latest_by_document: dict[str, ProcessingJobRecord] = {}
        for record in records:
            latest_by_document.setdefault(record.document_id, record)
        return {
            document_id: self._to_domain(record)
            for document_id, record in latest_by_document.items()
        }

    def add(self, job: ProcessingJob) -> None:
        self._session.add(
            ProcessingJobRecord(
                id=job.id,
                document_id=job.document_id.value,
                document_version_id=job.document_version_id,
                status=job.status,
                failure_reason=job.failure_reason,
                attempt=job.attempt,
                request_id=job.request_id,
                workspace_id=job.workspace_id,
                started_at=job.started_at,
                completed_at=job.completed_at,
                available_at=job.created_at,
                claimed_at=None,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
        )

    def save(self, job: ProcessingJob) -> None:
        record = self._session.get(ProcessingJobRecord, job.id)
        if record is None:
            raise ValueError(f"Processing job '{job.id}' was not found.")

        record.status = job.status
        record.failure_reason = job.failure_reason
        record.attempt = job.attempt
        record.request_id = job.request_id
        record.workspace_id = job.workspace_id
        record.started_at = job.started_at
        record.completed_at = job.completed_at
        record.updated_at = job.updated_at
        # Pending jobs must be reclaimable after retry or restart recovery.
        if job.status is ProcessingStatus.PENDING:
            record.claimed_at = None
            if record.available_at is None:
                record.available_at = job.updated_at

    def _to_domain(self, record: ProcessingJobRecord) -> ProcessingJob:
        return ProcessingJob(
            id=record.id,
            document_id=DocumentId(record.document_id),
            document_version_id=record.document_version_id,
            status=ProcessingStatus(record.status),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
            failure_reason=record.failure_reason,
            attempt=record.attempt,
            request_id=record.request_id,
            workspace_id=record.workspace_id,
            started_at=_as_utc_optional(record.started_at),
            completed_at=_as_utc_optional(record.completed_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _as_utc_optional(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _as_utc(value)
