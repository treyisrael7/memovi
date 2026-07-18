from dataclasses import dataclass
from datetime import datetime

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Optional metadata constraints applied after retrieval and fusion."""

    workspace_id: WorkspaceId | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    source_type: str | None = None
    mime_type: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
