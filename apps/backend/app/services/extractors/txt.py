from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument, ExtractedPage


class TXTExtractor(BaseDocumentExtractor):
    """Plain Text Document Extractor."""

    def extract(self, file_bytes: bytes) -> ExtractedDocument:
        if not file_bytes:
            raise ValueError("File content is empty")

        try:
            # Try UTF-8 decoding, fallback to latin-1
            try:
                text_content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text_content = file_bytes.decode("latin-1")

            text_content = text_content.strip()
            if not text_content:
                raise ValueError("TXT file contains no readable text")

            # Split on form feed character \f if present for pagination
            page_blocks = text_content.split("\f")
            pages: list[ExtractedPage] = []
            
            for idx, block in enumerate(page_blocks):
                cleaned_block = block.strip()
                if cleaned_block:
                    pages.append(ExtractedPage(page_number=idx + 1, text=cleaned_block))

            if not pages:
                pages = [ExtractedPage(page_number=1, text=text_content)]

            return ExtractedDocument(page_count=len(pages), pages=pages)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse TXT document: {str(e)}")
