from dataclasses import replace

from src.models import RetrievalHit
from src.retrieval.query_classifier import classify_query, detect_language
from src.retrieval.reranker import merge_and_rerank


def hit(chunk_id: str, **scores: float) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        document_id="document-1",
        document_title="GJU Regulations",
        source_url="https://example.edu/regulations.pdf",
        chunk_text="Evidence text",
        section_title="Registration",
        article_number="18",
        pdf_page_start=5,
        pdf_page_end=5,
        document_status="current",
        **scores,
    )


def test_scores_from_multiple_retrievers_are_merged() -> None:
    vector = hit("shared", vector_score=0.8)
    keyword = replace(vector, vector_score=0.0, keyword_score=0.7)
    vector_only = hit("vector-only", vector_score=0.9)

    results = merge_and_rerank([vector, vector_only], [keyword], [])

    shared = next(result for result in results if result.chunk_id == "shared")
    assert shared.vector_score > 0
    assert shared.keyword_score == 1.0
    assert shared.final_score > 0.1


def test_language_and_topic_classification() -> None:
    assert detect_language("ما هو course load المسموح؟") == "mixed"
    assert classify_query("What happens after too many absences?").topic == "attendance"
    assert classify_query("What are the German Year rules?").suggested_document_type == "german_year"
