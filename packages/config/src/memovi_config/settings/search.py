"""Search domain process settings (non-embedding)."""

from __future__ import annotations

from dataclasses import dataclass

from memovi_config.env import Environ


@dataclass(frozen=True, slots=True)
class SearchSettings:
    """Search process settings outside embedding provider selection.

    Embedding provider configuration lives in ``EmbeddingsSettings``. This
    object is reserved for future search ranking / retrieval process knobs.
    """

    @classmethod
    def from_environ(cls, environ: Environ) -> SearchSettings:
        del environ
        return cls()
