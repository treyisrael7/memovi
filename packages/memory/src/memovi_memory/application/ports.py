from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from memovi_memory.application.dto.processed_document_snapshot import ProcessedDocumentSnapshot


class EventPublisher(Protocol):
    """Publishes memory domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError


class ProcessedDocumentReader(Protocol):
    """Loads processed document content without coupling to the Documents domain."""

    def load_by_processing_job(
        self,
        processing_job_id: str,
    ) -> ProcessedDocumentSnapshot | None:
        raise NotImplementedError
