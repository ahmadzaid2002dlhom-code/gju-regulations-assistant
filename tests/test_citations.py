from src.generation.citation_builder import (
    ensure_source_references,
    source_page_url,
    source_summary,
)
from src.models import EvidenceSource, RetrievalHit


def evidence() -> EvidenceSource:
    return EvidenceSource(
        "S1",
        RetrievalHit(
            chunk_id="chunk-1",
            document_id="document-1",
            document_title="Bachelor Degree Instructions",
            source_url="https://example.edu/rules.pdf",
            chunk_text="Official evidence",
            section_title="Course Registration",
            article_number="18",
            pdf_page_start=14,
            pdf_page_end=14,
        ),
    )


def test_source_summary_contains_verifiable_location() -> None:
    summary = source_summary(evidence())
    assert "S1" in summary
    assert "Article 18" in summary
    assert "PDF page 14" in summary


def test_source_page_url_opens_the_first_cited_pdf_page() -> None:
    assert source_page_url(evidence()) == "https://example.edu/rules.pdf#page=14"


def test_source_page_url_preserves_query_parameters() -> None:
    source = evidence()
    source.hit.source_url = "https://example.edu/rules.pdf?download=1#old"
    assert source_page_url(source) == "https://example.edu/rules.pdf?download=1#page=14"


def test_missing_inline_references_get_a_source_footer() -> None:
    answer = ensure_source_references("The rule applies.", [evidence()])
    assert "[S1]" in answer


def test_existing_reference_is_not_duplicated() -> None:
    answer = ensure_source_references("The rule applies [S1].", [evidence()])
    assert answer.count("[S1]") == 1
