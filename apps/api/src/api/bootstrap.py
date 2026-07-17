import logging
from importlib.metadata import PackageNotFoundError, metadata

PROJECT_DISTRIBUTION = "memovi-api"
LOGGER_NAME = "memovi.api"


def initialize_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def validate_configuration() -> None:
    return None


def project_metadata() -> dict[str, str]:
    fallback = {
        "title": "Memovi API",
        "description": "Backend composition root for the Memovi platform.",
        "version": "0.1.0",
    }
    try:
        package_metadata = metadata(PROJECT_DISTRIBUTION)
    except PackageNotFoundError:
        return fallback

    # Prefer Message.get over version(): incomplete editable installs can expose
    # a distribution whose Version key is missing (None), which warns under 3.14+.
    project_version = package_metadata.get("Version") or fallback["version"]
    project_description = package_metadata.get("Summary") or fallback["description"]

    return {
        "title": fallback["title"],
        "description": project_description,
        "version": project_version,
    }
