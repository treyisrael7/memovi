from collections.abc import Callable, Iterator

from documents.application.ports import ProcessingJobQueue
from fastapi import Request
from memovi_observability import get_request_context
from sqlalchemy.orm import Session

from api.database import database_session


def build_documents_database_session(
    session_dependency: Callable[[], Iterator[Session]] | None = None,
) -> Callable[[Request], Iterator[Session]]:
    resolved_session_dependency = session_dependency or database_session

    def documents_database_session(request: Request) -> Iterator[Session]:
        pending_job_ids: list[str] = []
        pending_domain_events: list[object] = []
        request.state.pending_processing_job_ids = pending_job_ids
        request.state.pending_domain_events = pending_domain_events

        yield from resolved_session_dependency()

        queue: ProcessingJobQueue | None = getattr(
            request.app.state,
            "processing_job_queue",
            None,
        )
        context = getattr(request.state, "request_context", None) or get_request_context()
        request_id = context.request_id if context is not None else None
        workspace_id = (
            context.workspace_id.value
            if context is not None and context.workspace_id is not None
            else None
        )
        if queue is not None:
            for job_id in pending_job_ids:
                queue.enqueue(
                    job_id,
                    request_id=request_id,
                    workspace_id=workspace_id,
                )

        dispatcher = getattr(request.app.state, "event_dispatcher", None)
        if dispatcher is not None:
            for event in pending_domain_events:
                dispatcher.publish(event)

    return documents_database_session


documents_database_session = build_documents_database_session()
