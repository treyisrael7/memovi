from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from documents.application.exceptions import DocumentProcessingError


class PdfDocumentProcessor:
    """Extracts text from PDF artifacts."""

    def extract_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
        except PdfReadError as exc:
            raise DocumentProcessingError("PDF content could not be extracted.") from exc

        extracted = "\n".join(pages).strip()
        if not extracted:
            raise DocumentProcessingError("PDF content did not contain extractable text.")

        return extracted
