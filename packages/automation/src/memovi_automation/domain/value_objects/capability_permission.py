from dataclasses import dataclass

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class CapabilityPermission:
    """Immutable permission identifier declared by a capability.

    Permissions are metadata for discovery and future approval flows.
    This milestone does not enforce user consent.
    """

    name: str

    def __post_init__(self) -> None:
        name = self.name.strip().lower()
        if not name:
            raise InvalidCapabilityError("Capability permission name is required.")
        if any(part == "" for part in name.split(".")):
            raise InvalidCapabilityError(
                f"Capability permission '{self.name}' must use dotted segments.",
            )
        if not all(part.replace("_", "").isalnum() for part in name.split(".")):
            raise InvalidCapabilityError(
                f"Capability permission '{self.name}' contains invalid characters.",
            )
        object.__setattr__(self, "name", name)

    def __str__(self) -> str:
        return self.name


# Well-known permission names for future concrete capabilities.
FILESYSTEM_READ = CapabilityPermission("filesystem.read")
FILESYSTEM_WRITE = CapabilityPermission("filesystem.write")
TERMINAL_EXECUTE = CapabilityPermission("terminal.execute")
GIT_READ = CapabilityPermission("git.read")
GIT_WRITE = CapabilityPermission("git.write")
BROWSER_READ = CapabilityPermission("browser.read")
CLIPBOARD_READ = CapabilityPermission("clipboard.read")
CLIPBOARD_WRITE = CapabilityPermission("clipboard.write")
NOTIFICATIONS_SEND = CapabilityPermission("notifications.send")
