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

    def add(self, job: ProcessingJob) -> None:
        self._session.add(
            ProcessingJobRecord(
                id=job.id,
                document_id=job.document_id.value,
                document_version_id=job.document_version_id,
                status=job.status,
                failure_reason=job.failure_reason,
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
        record.updated_at = job.updated_at

    def _to_domain(self, record: ProcessingJobRecord) -> ProcessingJob:
        return ProcessingJob(
            id=record.id,
            document_id=DocumentId(record.document_id),
            document_version_id=record.document_version_id,
            status=ProcessingStatus(record.status),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
            failure_reason=record.failure_reason,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
