from __future__ import annotations

from src.database.repositories import SupabaseRepository
from src.models import RetrievalHit


def keyword_search(
    repository: SupabaseRepository,
    query: str,
    *,
    match_count: int,
    document_type: str | None,
    language: str | None,
) -> list[RetrievalHit]:
    rows = repository.search_keyword(
        query,
        match_count=match_count,
        document_type=document_type,
        language=language,
    )
    return [RetrievalHit.from_mapping(row, "keyword") for row in rows]
