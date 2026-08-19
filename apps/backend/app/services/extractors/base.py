from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    page_count: int
    pages: List[ExtractedPage]


class BaseDocumentExtractor(ABC):
    """Abstract interface for extracting text and page boundaries from documents."""

    @abstractmethod
    def extract(self, file_bytes: bytes) -> ExtractedDocument:
        """Extract text and return ExtractedDocument structure."""
        pass
