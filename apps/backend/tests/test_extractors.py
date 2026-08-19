import pytest
from app.services.extractors.txt import TXTExtractor


def test_txt_extractor_basic():
    extractor = TXTExtractor()
    content = "Page 1 content text.\fPage 2 content text."
    doc = extractor.extract(content.encode("utf-8"))
    
    assert doc.page_count == 2
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert "Page 1 content text." in doc.pages[0].text
    assert doc.pages[1].page_number == 2
    assert "Page 2 content text." in doc.pages[1].text


def test_txt_extractor_empty_file():
    extractor = TXTExtractor()
    with pytest.raises(ValueError, match="File content is empty"):
        extractor.extract(b"")


def test_txt_extractor_whitespace_only():
    extractor = TXTExtractor()
    with pytest.raises(ValueError, match="TXT file contains no readable text"):
        extractor.extract(b"   \n\n\t  ")
