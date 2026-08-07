from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from memovi_connectors.domain.exceptions import InvalidConnectorError

# Well-known connector identifiers for future adapters.
CONNECTOR_FAKE = "fake"
CONNECTOR_FILESYSTEM = "filesystem"
CONNECTOR_GITHUB = "github"
CONNECTOR_GOOGLE_DRIVE = "google_drive"
CONNECTOR_SLACK = "slack"
CONNECTOR_GMAIL = "gmail"
CONNECTOR_NOTION = "notion"
CONNECTOR_OBSIDIAN = "obsidian"
CONNECTOR_CLOUD_STORAGE = "cloud_storage"

_AUTH_METHODS = frozenset(
    {
        "none",
        "oauth",
        "api_key",
        "personal_access_token",
        "service_account",
    },
)

_SOURCE_CATEGORIES = frozenset(
    {
        "filesystem",
        "cloud_storage",
        "collaboration",
        "email",
        "code",
        "notes",
        "api",
        "other",
    },
)


@dataclass(frozen=True, slots=True)
class ConnectorMetadata:
    """Immutable discovery metadata for a registered connector type."""

    connector_id: str
    display_name: str
    description: str
    source_category: str
    auth_methods: Sequence[str] = ()
    supports_incremental_sync: bool = True
    supports_delete_detection: bool = True

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        display_name = self.display_name.strip()
        description = self.description.strip()
        source_category = self.source_category.strip().lower()

        if not connector_id:
            raise InvalidConnectorError("Connector metadata connector_id is required.")
        if not display_name:
            raise InvalidConnectorError("Connector metadata display_name is required.")
        if source_category not in _SOURCE_CATEGORIES:
            raise InvalidConnectorError(
                "Connector metadata source_category must be one of: "
                f"{', '.join(sorted(_SOURCE_CATEGORIES))}.",
            )

        methods = tuple(method.strip().lower() for method in self.auth_methods)
        if not methods:
            methods = ("none",)
        invalid = [method for method in methods if method not in _AUTH_METHODS]
        if invalid:
            raise InvalidConnectorError(
                "Connector metadata auth_methods contains unsupported values: "
                f"{', '.join(invalid)}.",
            )

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "source_category", source_category)
        object.__setattr__(self, "auth_methods", methods)
