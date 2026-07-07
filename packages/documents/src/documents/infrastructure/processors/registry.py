from documents.application.exceptions import UnsupportedProcessorError
from documents.application.ports import DocumentProcessor
from documents.infrastructure.processors.markdown_processor import MarkdownDocumentProcessor
from documents.infrastructure.processors.pdf_processor import PdfDocumentProcessor
from documents.infrastructure.processors.plain_text_processor import PlainTextDocumentProcessor


class DefaultProcessorRegistry:
    """Maps supported MIME types to document processors."""

    def __init__(
        self,
        *,
        processors: dict[str, DocumentProcessor] | None = None,
    ) -> None:
        self._processors = processors or {
            "application/pdf": PdfDocumentProcessor(),
            "text/markdown": MarkdownDocumentProcessor(),
            "text/x-markdown": MarkdownDocumentProcessor(),
            "text/plain": PlainTextDocumentProcessor(),
        }

    def processor_for(self, mime_type: str) -> DocumentProcessor:
        processor = self._processors.get(mime_type.strip().lower())
        if processor is None:
            raise UnsupportedProcessorError(
                f"No processor is registered for MIME type '{mime_type}'.",
            )
        return processor
