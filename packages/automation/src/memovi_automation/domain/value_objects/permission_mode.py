from enum import StrEnum


class PermissionMode(StrEnum):
    """Capability-specific permission decision for execution requests."""

    ALWAYS_ALLOW = "always_allow"
    ASK_EVERY_TIME = "ask_every_time"
    DENY = "deny"
