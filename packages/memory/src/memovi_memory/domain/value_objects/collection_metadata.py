from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidCollectionError

_MAX_NAME_LENGTH = 256
_MAX_DESCRIPTION_LENGTH = 4000


@dataclass(frozen=True, slots=True)
class CollectionMetadata:
    """User-facing organizational metadata for a collection."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not normalized_name:
            raise InvalidCollectionError("Collection name is required.")
        if len(normalized_name) > _MAX_NAME_LENGTH:
            raise InvalidCollectionError(
                f"Collection name must be at most {_MAX_NAME_LENGTH} characters.",
            )
        normalized_description = self.description.strip()
        if len(normalized_description) > _MAX_DESCRIPTION_LENGTH:
            raise InvalidCollectionError(
                f"Collection description must be at most {_MAX_DESCRIPTION_LENGTH} characters.",
            )
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "description", normalized_description)

    def rename(self, name: str) -> CollectionMetadata:
        return CollectionMetadata(name=name, description=self.description)

    def with_description(self, description: str) -> CollectionMetadata:
        return CollectionMetadata(name=self.name, description=description)
