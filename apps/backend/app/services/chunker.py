from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID
from app.services.extractors.base import ExtractedDocument


@dataclass
class ChunkData:
    chunk_index: int
    page_number: int
    text: str
    token_count: int
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None


class Chunker:
    """Configurable deterministic text chunker retaining page boundaries and metadata."""

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        doc: ExtractedDocument,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[ChunkData]:
        chunks: List[ChunkData] = []
        global_chunk_index = 0

        for page in doc.pages:
            text = page.text.strip()
            if not text:
                continue

            page_chunks = self._chunk_text(text)
            for page_chunk_text in page_chunks:
                # Estimate token count (~4 chars per token rule of thumb)
                estimated_tokens = max(1, len(page_chunk_text) // 4)
                
                chunks.append(
                    ChunkData(
                        chunk_index=global_chunk_index,
                        page_number=page.page_number,
                        text=page_chunk_text,
                        token_count=estimated_tokens,
                        subject=subject,
                        chapter=chapter,
                        topic=topic
                    )
                )
                global_chunk_index += 1

        return chunks

    def _chunk_text(self, text: str) -> List[str]:
        if not text:
            return []
        
        if len(text) <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # If not at the end of text, try to split at paragraph or sentence boundary
            if end < len(text):
                last_newline = chunk.rfind("\n")
                if last_newline > self.chunk_size // 2:
                    end = start + last_newline + 1
                    chunk = text[start:end]
                else:
                    last_space = chunk.rfind(" ")
                    if last_space > self.chunk_size // 2:
                        end = start + last_space + 1
                        chunk = text[start:end]

            chunk_str = chunk.strip()
            if chunk_str:
                chunks.append(chunk_str)

            start += max(1, end - start - self.chunk_overlap)
            if start >= len(text) or (len(chunks) > 1 and chunks[-1] == text[start:].strip()):
                if start < len(text) and text[start:].strip() and text[start:].strip() != chunks[-1]:
                    chunks.append(text[start:].strip())
                break

        return chunks
