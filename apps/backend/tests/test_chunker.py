import pytest
from app.services.chunker import Chunker
from app.services.extractors.base import ExtractedDocument, ExtractedPage


def test_chunker_empty_document():
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    doc = ExtractedDocument(page_count=0, pages=[])
    chunks = chunker.chunk_document(doc)
    assert chunks == []


def test_chunker_short_text():
    chunker = Chunker(chunk_size=500, chunk_overlap=50)
    doc = ExtractedDocument(
        page_count=1,
        pages=[ExtractedPage(page_number=1, text="Short academic text paragraph.")]
    )
    chunks = chunker.chunk_document(doc, subject="Physics", chapter="Ch1", topic="Kinematics")
    
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "Short academic text paragraph."
    assert chunks[0].subject == "Physics"
    assert chunks[0].chapter == "Ch1"
    assert chunks[0].topic == "Kinematics"


def test_chunker_long_text_and_overlap():
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    long_text = "Word " * 100  # 500 chars text
    doc = ExtractedDocument(
        page_count=1,
        pages=[ExtractedPage(page_number=1, text=long_text)]
    )
    chunks = chunker.chunk_document(doc)
    
    assert len(chunks) > 1
    # Verify deterministic chunk indices
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.page_number == 1


def test_chunker_invalid_overlap():
    with pytest.raises(ValueError, match="chunk_overlap must be strictly smaller than chunk_size"):
        Chunker(chunk_size=100, chunk_overlap=100)
