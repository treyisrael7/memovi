from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class BrowserCapabilityConfig:
    """Configuration for the Browser Capability.

    Download destinations are restricted to ``download_roots`` (typically the
    same roots as the Filesystem Capability). Timeouts and size caps bound
    network work so callers cannot request unbounded fetches.
    """

    download_roots: tuple[Path, ...]
    default_timeout_seconds: float = 30.0
    max_timeout_seconds: float = 300.0
    max_response_bytes: int = 5_242_880  # 5 MiB page/body cap
    max_download_bytes: int = 52_428_800  # 50 MiB download cap
    default_search_limit: int = 5
    max_search_limit: int = 20
    user_agent: str = "MemoviBrowser/0.1 (+https://memovi.local)"
    follow_redirects: bool = True
    max_redirects: int = 10

    def __post_init__(self) -> None:
        if not self.download_roots:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.download_roots must contain at least one root.",
            )
        if self.default_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.default_timeout_seconds must be positive.",
            )
        if self.max_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.max_timeout_seconds must be positive.",
            )
        if self.default_timeout_seconds > self.max_timeout_seconds:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.default_timeout_seconds cannot exceed "
                "max_timeout_seconds.",
            )
        if self.max_response_bytes <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.max_response_bytes must be positive.",
            )
        if self.max_download_bytes <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.max_download_bytes must be positive.",
            )
        if self.default_search_limit <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.default_search_limit must be positive.",
            )
        if self.max_search_limit <= 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.max_search_limit must be positive.",
            )
        if self.max_redirects < 0:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.max_redirects cannot be negative.",
            )
        agent = self.user_agent.strip()
        if not agent:
            raise InvalidCapabilityError(
                "BrowserCapabilityConfig.user_agent is required.",
            )

        normalized_roots: list[Path] = []
        for root in self.download_roots:
            if not isinstance(root, Path):
                raise InvalidCapabilityError(
                    "BrowserCapabilityConfig.download_roots must contain Path instances.",
                )
            resolved = root.expanduser().resolve(strict=False)
            if not resolved.exists():
                raise InvalidCapabilityError(
                    f"Browser download root does not exist: {resolved}",
                )
            if not resolved.is_dir():
                raise InvalidCapabilityError(
                    f"Browser download root must be a directory: {resolved}",
                )
            normalized_roots.append(resolved)

        object.__setattr__(self, "download_roots", tuple(normalized_roots))
        object.__setattr__(self, "user_agent", agent)

    @classmethod
    def from_roots(
        cls,
        roots: Iterable[Path | str],
        *,
        default_timeout_seconds: float = 30.0,
        max_timeout_seconds: float = 300.0,
        max_response_bytes: int = 5_242_880,
        max_download_bytes: int = 52_428_800,
        default_search_limit: int = 5,
        max_search_limit: int = 20,
        user_agent: str = "MemoviBrowser/0.1 (+https://memovi.local)",
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ) -> BrowserCapabilityConfig:
        return cls(
            download_roots=tuple(Path(root) for root in roots),
            default_timeout_seconds=default_timeout_seconds,
            max_timeout_seconds=max_timeout_seconds,
            max_response_bytes=max_response_bytes,
            max_download_bytes=max_download_bytes,
            default_search_limit=default_search_limit,
            max_search_limit=max_search_limit,
            user_agent=user_agent,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
        )
