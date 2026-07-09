import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from documents.domain.enums import ProcessingStatus
from documents.domain.exceptions import InvalidProcessingJobError, InvalidProcessingTransitionError
from documents.domain.value_objects import DocumentId

_TERMINAL_STATUSES = frozenset({ProcessingStatus.COMPLETED, ProcessingStatus.FAILED})


@dataclass(frozen=True, slots=True)
class ProcessingJob:
    """Tracks ingestion processing for a document version."""

    id: str
    document_id: DocumentId
    document_version_id: str
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidProcessingJobError("Processing job ID is required.")
        if not self.document_version_id:
            raise InvalidProcessingJobError("Document version ID is required.")

    @classmethod
    def create_pending(
        cls,
        *,
        document_id: DocumentId,
        document_version_id: str,
        now: datetime | None = None,
    ) -> ProcessingJob:
        timestamp = now or datetime.now(UTC)
        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            document_version_id=document_version_id,
            status=ProcessingStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def start(self, now: datetime | None = None) -> ProcessingJob:
        return self._transition(
            expected=ProcessingStatus.PENDING,
            next_status=ProcessingStatus.EXTRACTING,
            now=now,
        )

    def advance_to_normalizing(self, now: datetime | None = None) -> ProcessingJob:
        return self._transition(
            expected=ProcessingStatus.EXTRACTING,
            next_status=ProcessingStatus.NORMALIZING,
            now=now,
        )

    def complete(self, now: datetime | None = None) -> ProcessingJob:
        return self._transition(
            expected=ProcessingStatus.NORMALIZING,
            next_status=ProcessingStatus.COMPLETED,
            now=now,
        )

    def fail(self, *, reason: str | None = None, now: datetime | None = None) -> ProcessingJob:
        if self.status in _TERMINAL_STATUSES:
            raise InvalidProcessingTransitionError(
                f"Processing job in status '{self.status}' cannot fail.",
            )

        timestamp = now or datetime.now(UTC)
        return replace(
            self,
            status=ProcessingStatus.FAILED,
            updated_at=timestamp,
            failure_reason=reason,
        )

    def reset_to_pending(self, now: datetime | None = None) -> ProcessingJob:
        if self.status == ProcessingStatus.COMPLETED:
            raise InvalidProcessingTransitionError(
                "Completed processing jobs cannot be reset to pending.",
            )
        if self.status == ProcessingStatus.PENDING:
            return self

        timestamp = now or datetime.now(UTC)
        return replace(
            self,
            status=ProcessingStatus.PENDING,
            updated_at=timestamp,
            failure_reason=None,
        )

    def _transition(
        self,
        *,
        expected: ProcessingStatus,
        next_status: ProcessingStatus,
        now: datetime | None,
    ) -> ProcessingJob:
        if self.status != expected:
            raise InvalidProcessingTransitionError(
                f"Processing job in status '{self.status}' cannot transition to "
                f"'{next_status}'.",
            )

        return replace(self, status=next_status, updated_at=now or datetime.now(UTC))
