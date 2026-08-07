from enum import StrEnum

from memovi_memory.domain.exceptions import InvalidCollectionMembershipError


class CollectionMemberKind(StrEnum):
    """Kinds of platform resources that may belong to a collection."""

    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"
    CONVERSATION = "conversation"
    WORKFLOW = "workflow"


_ALLOWED = frozenset(kind.value for kind in CollectionMemberKind)


def parse_member_kind(value: str) -> CollectionMemberKind:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED:
        raise InvalidCollectionMembershipError(
            "Member kind must be one of: document, knowledge, conversation, workflow.",
        )
    return CollectionMemberKind(normalized)
