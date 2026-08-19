import io
from pypdf import PdfReader
from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument, ExtractedPage


class PDFExtractor(BaseDocumentExtractor):
    """PDF Document Extractor preserving page numbers."""

    def extract(self, file_bytes: bytes) -> ExtractedDocument:
        if not file_bytes:
            raise ValueError("File content is empty")

        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages: list[ExtractedPage] = []
            
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages.append(ExtractedPage(page_number=idx + 1, text=page_text.strip()))
            
            if not pages:
                raise ValueError("PDF contains no readable pages")

            return ExtractedDocument(page_count=len(pages), pages=pages)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF document: {str(e)}")
