"""Run document processing for a pending processing job (local development)."""

import argparse
import sys

from api.database import session_factory
from documents.application.commands.process_document import ProcessDocument, ProcessDocumentCommand
from documents.infrastructure.events.noop_event_publisher import CollectingEventPublisher
from documents.infrastructure.processors import DefaultProcessorRegistry
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)
from documents.infrastructure.storage import MinioObjectStorage


def main() -> int:
    parser = argparse.ArgumentParser(description="Process a pending document ingestion job.")
    parser.add_argument("processing_job_id", help="Processing job ID from POST /documents response")
    args = parser.parse_args()

    session = session_factory()()
    try:
        result = ProcessDocument(
            documents=SqlAlchemyDocumentRepository(session),
            processing_jobs=SqlAlchemyProcessingJobRepository(session),
            object_storage=MinioObjectStorage.from_env(),
            processor_registry=DefaultProcessorRegistry(),
            event_publisher=CollectingEventPublisher(),
        ).execute(ProcessDocumentCommand(processing_job_id=args.processing_job_id))
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()

    event_names = ", ".join(type(event).__name__ for event in result.events)
    print(f"status: {result.processing_status.value}")
    print(f"events: {event_names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
