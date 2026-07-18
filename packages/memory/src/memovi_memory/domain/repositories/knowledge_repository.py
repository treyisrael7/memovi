import builtins
from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_memory.domain.entities import KnowledgeItem
from memovi_memory.domain.value_objects import KnowledgeItemId


class KnowledgeRepository(Protocol):
    """Persistence contract for durable knowledge items."""

    def save(self, knowledge_item: KnowledgeItem) -> None:
        raise NotImplementedError

    def get_by_id(
        self,
        knowledge_item_id: KnowledgeItemId,
        *,
        workspace_id: WorkspaceId,
    ) -> KnowledgeItem | None:
        raise NotImplementedError

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> builtins.list[KnowledgeItem]:
        raise NotImplementedError

    def list_by_document(
        self,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
    ) -> builtins.list[KnowledgeItem]:
        raise NotImplementedError

    def list_by_document_version(
        self,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
        document_version_id: str,
    ) -> builtins.list[KnowledgeItem]:
        raise NotImplementedError

    def delete(
        self,
        knowledge_item_id: KnowledgeItemId,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        raise NotImplementedError
