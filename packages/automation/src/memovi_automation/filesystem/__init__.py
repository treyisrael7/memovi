"""Production Filesystem Capability — reference capability implementation."""

from memovi_automation.filesystem.capability import (
    CAPABILITY_ID,
    READ_OPERATIONS,
    WRITE_OPERATIONS,
    FilesystemCapability,
    register_filesystem_capability,
)
from memovi_automation.filesystem.config import FilesystemCapabilityConfig
from memovi_automation.filesystem.errors import (
    FILE_NOT_FOUND,
    FILE_TOO_LARGE,
    INVALID_PATH,
    NOT_A_DIRECTORY,
    NOT_A_FILE,
    NOT_TEXT_FILE,
    PERMISSION_DENIED,
    UNSUPPORTED_OPERATION,
)

__all__ = [
    "CAPABILITY_ID",
    "FILE_NOT_FOUND",
    "FILE_TOO_LARGE",
    "INVALID_PATH",
    "NOT_A_DIRECTORY",
    "NOT_A_FILE",
    "NOT_TEXT_FILE",
    "PERMISSION_DENIED",
    "READ_OPERATIONS",
    "UNSUPPORTED_OPERATION",
    "WRITE_OPERATIONS",
    "FilesystemCapability",
    "FilesystemCapabilityConfig",
    "register_filesystem_capability",
]
