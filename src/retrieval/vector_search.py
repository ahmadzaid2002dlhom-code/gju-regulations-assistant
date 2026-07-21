from __future__ import annotations

from src.database.repositories import SupabaseRepository
from src.models import RetrievalHit


def vector_search(
    repository: SupabaseRepository,
    embedding: list[float],
    *,
    match_count: int,
    document_type: str | None,
    language: str | None,
) -> list[RetrievalHit]:
    rows = repository.search_vector(
        embedding,
        match_count=match_count,
        document_type=document_type,
        language=language,
    )
    return [RetrievalHit.from_mapping(row, "vector") for row in rows]
