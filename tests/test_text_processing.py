"""LegalLens AI — Tests for text processing utilities."""

from app.utils.text_processing import (
    chunk_text,
    detect_sections,
    get_section_for_position,
    normalize_text,
)


def test_normalize_text():
    """Test text normalization."""
    # Handle carriage returns
    assert normalize_text("Line 1\r\nLine 2") == "Line 1\nLine 2"

    # Collapse multiple blank lines
    assert normalize_text("A\n\n\n\nB") == "A\n\nB"

    # Preserve necessary newlines but strip space
    assert normalize_text("  Start  \n  End  ") == "Start\nEnd"


def test_detect_sections():
    """Test section detection logic."""
    text = """
Some intro text.

1. DEFINITIONS
Here are definitions.

ARTICLE II: PAYMENT
Payment terms here.

SECTION 3 - TERMINATION
Termination terms.
    """

    sections = detect_sections(text)
    assert len(sections) == 3
    assert sections[0]["heading"] == "1. DEFINITIONS"
    assert sections[1]["heading"] == "ARTICLE II: PAYMENT"
    assert sections[2]["heading"] == "SECTION 3 - TERMINATION"


def test_get_section_for_position():
    """Test mapping position to section."""
    sections = [
        {"heading": "Sec 1", "start_pos": 10},
        {"heading": "Sec 2", "start_pos": 50},
    ]

    assert get_section_for_position(sections, 5) is None
    assert get_section_for_position(sections, 15) == "Sec 1"
    assert get_section_for_position(sections, 60) == "Sec 2"


def test_chunk_text():
    """Test document chunking."""
    text = "A" * 1000 + "\n\n" + "B" * 1000

    # Small chunk size to force multiple chunks
    chunks = chunk_text(text, chunk_size=800, chunk_overlap=100)

    assert len(chunks) > 1
    assert chunks[0].chunk_id == 0
    assert chunks[1].chunk_id == 1

    # Verify overlap exists (second chunk starts before first ends)
    assert chunks[1].start_char < chunks[0].end_char

    # Verify page assignment
    page_breaks = [1500]
    chunks = chunk_text(text, chunk_size=800, chunk_overlap=0, page_breaks=page_breaks)

    # First chunks before 1500 are page 1, after are page 2
    assert chunks[0].page == 1
    assert chunks[-1].page == 2
