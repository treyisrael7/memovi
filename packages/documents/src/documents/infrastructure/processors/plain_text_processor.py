from documents.application.exceptions import DocumentProcessingError


class PlainTextDocumentProcessor:
    """Extracts text from plain text artifacts."""

    def extract_text(self, content: bytes) -> str:
        try:
            extracted = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentProcessingError("Plain text content is not valid UTF-8.") from exc

        if not extracted.strip():
            raise DocumentProcessingError("Plain text content is empty.")

        return extracted
