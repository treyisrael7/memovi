from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidConversationError
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects.conversation_turn import ConversationTurn


@dataclass(frozen=True, slots=True)
class ConversationHistory:
    """Immutable ordered sequence of conversation turns."""

    turns: tuple[ConversationTurn, ...] = ()

    def __post_init__(self) -> None:
        if any(not isinstance(turn, ConversationTurn) for turn in self.turns):
            raise InvalidConversationError(
                "turns must contain ConversationTurn instances.",
            )
        object.__setattr__(self, "turns", tuple(self.turns))

    @classmethod
    def empty(cls) -> ConversationHistory:
        return cls(turns=())

    @property
    def is_empty(self) -> bool:
        return len(self.turns) == 0

    @property
    def estimated_token_count(self) -> int:
        return sum(_estimate_turn_tokens(turn) for turn in self.turns)

    def append(self, turn: ConversationTurn) -> ConversationHistory:
        return ConversationHistory(turns=(*self.turns, turn))

    def trim(self, *, max_turns: int, max_tokens: int) -> ConversationHistory:
        """Return the most recent contiguous turns within turn and token limits.

        Older turns are dropped first. If the newest retained window would exceed
        ``max_tokens``, trimming stops so token limits are never bypassed.
        """
        if max_turns < 0:
            raise InvalidConversationError("max_turns cannot be negative.")
        if max_tokens < 0:
            raise InvalidConversationError("max_tokens cannot be negative.")
        if max_turns == 0 or max_tokens == 0 or not self.turns:
            return ConversationHistory.empty()

        candidates = self.turns[-max_turns:]
        retained: list[ConversationTurn] = []
        used_tokens = 0

        for turn in reversed(candidates):
            turn_tokens = _estimate_turn_tokens(turn)
            if used_tokens + turn_tokens > max_tokens:
                break
            retained.append(turn)
            used_tokens += turn_tokens

        retained.reverse()
        return ConversationHistory(turns=tuple(retained))


def _estimate_turn_tokens(turn: ConversationTurn) -> int:
    return estimate_token_count(f"{turn.role.value}: {turn.content}")
