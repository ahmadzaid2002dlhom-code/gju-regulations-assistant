from src.ingestion.chunker import article_blocks, create_chunks
from src.ingestion.heading_detector import detect_sections
from src.models import ExtractedPage


def test_article_detection_keeps_continuation_with_article() -> None:
    pages = [
        ExtractedPage(1, "Article 18\nA student may register an additional course."),
        ExtractedPage(2, "This exception applies during the final semester."),
        ExtractedPage(3, "Article (19)\nThe dean must approve the request."),
    ]
    sections = detect_sections(pages)
    blocks = article_blocks(pages, sections)

    article_18 = next(block for block in blocks if block.article_number == "18")
    assert [piece.page_number for piece in article_18.pieces] == [1, 2]
    assert "final semester" in article_18.pieces[-1].text


def test_short_article_is_not_split() -> None:
    pages = [ExtractedPage(1, "Article 18\nA student may register an additional course.")]
    sections = detect_sections(pages)
    chunks = create_chunks(
        pages=pages,
        sections=sections,
        document_title="Test Regulations",
        document_type="regulation",
        language="en",
        academic_year="2026",
        target_tokens=50,
        max_tokens=100,
        overlap_tokens=10,
    )

    assert len(chunks) == 1
    assert chunks[0].article_number == "18"
    assert chunks[0].pdf_page_start == 1


def test_long_article_uses_overlapping_windows() -> None:
    long_text = "Article 20\n" + " ".join(f"requirement{i}" for i in range(180))
    pages = [ExtractedPage(4, long_text)]
    sections = detect_sections(pages)
    chunks = create_chunks(
        pages=pages,
        sections=sections,
        document_title="Test Regulations",
        document_type="regulation",
        language="en",
        academic_year=None,
        target_tokens=40,
        max_tokens=50,
        overlap_tokens=5,
    )

    assert len(chunks) > 1
    assert all(chunk.token_count <= 40 for chunk in chunks)
    assert all(chunk.article_number == "20" for chunk in chunks)


def test_arabic_article_digits_are_normalized() -> None:
    pages = [ExtractedPage(1, "المادة (١٨)\nيجوز للطالب التسجيل وفق التعليمات.")]
    sections = detect_sections(pages)

    assert len(sections) == 1
    assert sections[0].section_type == "article"
    assert sections[0].article_number == "18"


def test_arabic_reversed_parentheses_are_detected() -> None:
    pages = [ExtractedPage(373, "المادة )١٣(\nيجوز أن يزيد الحد الأعلى للنصاب الدراسي.")]

    sections = detect_sections(pages)

    assert len(sections) == 1
    assert sections[0].article_number == "13"
