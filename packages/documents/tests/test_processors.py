import pytest
from documents.application.exceptions import DocumentProcessingError
from documents.domain.services.text_normalizer import normalize_text
from documents.infrastructure.processors.markdown_processor import MarkdownDocumentProcessor
from documents.infrastructure.processors.pdf_processor import PdfDocumentProcessor
from documents.infrastructure.processors.plain_text_processor import PlainTextDocumentProcessor
from documents.infrastructure.processors.registry import DefaultProcessorRegistry
from pdf_fixtures import build_pdf_with_text


def test_plain_text_processor_extracts_utf8_content() -> None:
    processor = PlainTextDocumentProcessor()

    extracted = processor.extract_text(b"Hello\r\nworld")

    assert extracted == "Hello\r\nworld"


def test_plain_text_processor_rejects_invalid_utf8() -> None:
    processor = PlainTextDocumentProcessor()

    with pytest.raises(DocumentProcessingError, match="valid UTF-8"):
        processor.extract_text(b"\xff\xfe")


def test_markdown_processor_extracts_content() -> None:
    processor = MarkdownDocumentProcessor()

    extracted = processor.extract_text(b"# Title\r\n\r\nBody")

    assert extracted == "# Title\r\n\r\nBody"


def test_pdf_processor_extracts_text() -> None:
    processor = PdfDocumentProcessor()
    pdf_bytes = build_pdf_with_text("Hello PDF")

    extracted = processor.extract_text(pdf_bytes)

    assert "Hello PDF" in extracted


def test_pdf_processor_rejects_invalid_pdf() -> None:
    processor = PdfDocumentProcessor()

    with pytest.raises(DocumentProcessingError, match="could not be extracted"):
        processor.extract_text(b"not-a-pdf")


def test_processor_registry_resolves_supported_mime_types() -> None:
    registry = DefaultProcessorRegistry()

    assert isinstance(registry.processor_for("application/pdf"), PdfDocumentProcessor)
    assert isinstance(registry.processor_for("text/markdown"), MarkdownDocumentProcessor)
    assert isinstance(registry.processor_for("text/plain"), PlainTextDocumentProcessor)


def test_normalize_text_collapses_line_endings_and_whitespace() -> None:
    normalized = normalize_text("Hello \r\n\r\nworld\t\t!")

    assert normalized == "Hello\n\nworld !"
