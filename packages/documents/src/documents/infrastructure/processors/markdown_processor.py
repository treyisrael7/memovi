from documents.application.exceptions import DocumentProcessingError


class MarkdownDocumentProcessor:
    """Extracts text from Markdown artifacts."""

    def extract_text(self, content: bytes) -> str:
        try:
            extracted = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentProcessingError("Markdown content is not valid UTF-8.") from exc

        if not extracted.strip():
            raise DocumentProcessingError("Markdown content is empty.")

        return extracted
