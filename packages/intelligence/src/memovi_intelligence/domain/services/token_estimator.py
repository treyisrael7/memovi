def estimate_token_count(text: str) -> int:
    """Estimate token count with a deterministic character heuristic.

    Uses roughly four characters per token so assembly limits remain provider-agnostic.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
