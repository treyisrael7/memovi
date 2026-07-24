class InMemoryObjectStorage:
    """Process-local object storage for tests and offline API startup fallbacks."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_object(self, key: str) -> bytes:
        try:
            return self.objects[key][0]
        except KeyError as exc:
            raise FileNotFoundError(key) from exc
