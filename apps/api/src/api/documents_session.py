from collections.abc import Callable, Iterator

from documents.application.ports import ProcessingJobQueue
from fastapi import Request
from sqlalchemy.orm import Session

from api.database import database_session


def build_documents_database_session(
    session_dependency: Callable[[], Iterator[Session]] | None = None,
) -> Callable[[Request], Iterator[Session]]:
    resolved_session_dependency = session_dependency or database_session

    def documents_database_session(request: Request) -> Iterator[Session]:
        pending_job_ids: list[str] = []
        request.state.pending_processing_job_ids = pending_job_ids

        yield from resolved_session_dependency()

        queue: ProcessingJobQueue | None = getattr(
            request.app.state,
            "processing_job_queue",
            None,
        )
        if queue is None:
            return

        for job_id in pending_job_ids:
            queue.enqueue(job_id)

    return documents_database_session


documents_database_session = build_documents_database_session()
