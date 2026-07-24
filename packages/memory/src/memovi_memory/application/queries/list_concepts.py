from collections import defaultdict

from memovi_shared import WorkspaceId

from memovi_memory.application.dto import ConceptDto
from memovi_memory.application.queries.list_knowledge import ListKnowledge


class ListConcepts:
    """Projects structural concepts from workspace knowledge metadata."""

    def __init__(self, *, list_knowledge: ListKnowledge) -> None:
        self._list_knowledge = list_knowledge

    def execute(self, *, workspace_id: WorkspaceId) -> list[ConceptDto]:
        knowledge_items = self._list_knowledge.execute(workspace_id=workspace_id)
        buckets: dict[tuple[str, str], list[str]] = defaultdict(list)

        for item in knowledge_items:
            buckets[("source_type", item.source_type)].append(item.id)
            buckets[("mime_type", item.mime_type)].append(item.id)

        concepts: list[ConceptDto] = []
        for (kind, label), knowledge_ids in sorted(
            buckets.items(),
            key=lambda entry: (entry[0][0], entry[0][1]),
        ):
            unique_ids = tuple(dict.fromkeys(knowledge_ids))
            concepts.append(
                ConceptDto(
                    id=f"{kind}:{label}",
                    kind=kind,
                    label=label,
                    knowledge_item_count=len(unique_ids),
                    knowledge_item_ids=unique_ids,
                )
            )
        return concepts
