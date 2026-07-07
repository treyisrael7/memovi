import re

_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")
_MULTI_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalize line endings and whitespace for durable document content."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_MULTI_SPACE_PATTERN.sub(" ", line.rstrip()) for line in normalized.split("\n")]
    collapsed = _MULTI_BLANK_LINES_PATTERN.sub("\n\n", "\n".join(lines))
    return collapsed.strip()
