import logging
from importlib.metadata import PackageNotFoundError, metadata, version

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
    try:
        package_metadata = metadata(PROJECT_DISTRIBUTION)
        project_version = version(PROJECT_DISTRIBUTION)
    except PackageNotFoundError:
        return {
            "title": "Memovi API",
            "description": "Backend composition root for the Memovi platform.",
            "version": "0.1.0",
        }

    project_description = (
        package_metadata.get("Summary") or "Backend composition root for the Memovi platform."
    )

    return {
        "title": "Memovi API",
        "description": project_description,
        "version": project_version,
    }
