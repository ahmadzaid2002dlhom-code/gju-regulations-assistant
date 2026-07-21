from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from supabase import Client

from src.models import DetectedSection, ExtractedPage, PreparedChunk, SourceDefinition


def _batches(values: Sequence[dict[str, Any]], size: int = 200) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


class SupabaseRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def find_document_by_checksum(self, source_url: str, checksum: str) -> dict[str, Any] | None:
        response = (
            self._client.table("documents")
            .select("*")
            .eq("source_url", source_url)
            .eq("checksum", checksum)
            .eq("status", "current")
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def current_documents_for_url(self, source_url: str) -> list[dict[str, Any]]:
        response = (
            self._client.table("documents")
            .select("*")
            .eq("source_url", source_url)
            .eq("status", "current")
            .order("created_at", desc=True)
            .execute()
        )
        return list(response.data or [])

    def create_document(
        self,
        source: SourceDefinition,
        checksum: str,
        storage_path: str,
        supersedes_document_id: str | None,
    ) -> str:
        record = source.model_dump(mode="json")
        record.update(
            {
                "url": None,
                "source_url": str(source.url),
                "storage_path": storage_path,
                "checksum": checksum,
                "status": "processing",
                "supersedes_document_id": supersedes_document_id,
            }
        )
        record.pop("url", None)
        response = self._client.table("documents").insert(record).execute()
        if not response.data:
            raise RuntimeError("Supabase did not return the inserted document.")
        return str(response.data[0]["id"])

    def update_document_status(self, document_id: str, status: str) -> None:
        (
            self._client.table("documents")
            .update({"status": status})
            .eq("id", document_id)
            .execute()
        )

    def insert_pages(self, document_id: str, pages: list[ExtractedPage]) -> dict[int, str]:
        records = [
            {
                "document_id": document_id,
                "pdf_page_number": page.pdf_page_number,
                "printed_page_number": page.printed_page_number,
                "page_text": page.page_text,
                "section_title": page.section_title,
            }
            for page in pages
        ]
        page_ids: dict[int, str] = {}
        for batch in _batches(records):
            response = self._client.table("pages").insert(batch).execute()
            for row in response.data or []:
                page_ids[int(row["pdf_page_number"])] = str(row["id"])
        if len(page_ids) != len(records):
            raise RuntimeError("Not all PDF pages were inserted.")
        return page_ids

    def insert_sections(
        self,
        document_id: str,
        sections: list[DetectedSection],
    ) -> dict[str, str]:
        section_ids: dict[str, str] = {}
        for section in sorted(sections, key=lambda value: (value.page_start, value.hierarchy_level)):
            response = (
                self._client.table("sections")
                .insert(
                    {
                        "document_id": document_id,
                        "parent_section_id": section_ids.get(section.parent_local_key or ""),
                        "title": section.title,
                        "section_type": section.section_type,
                        "article_number": section.article_number,
                        "hierarchy_level": section.hierarchy_level,
                        "page_start": section.page_start,
                        "page_end": section.page_end,
                    }
                )
                .execute()
            )
            if not response.data:
                raise RuntimeError(f"Section {section.title!r} was not inserted.")
            section_ids[section.local_key] = str(response.data[0]["id"])
        return section_ids

    def insert_chunks(
        self,
        document_id: str,
        chunks: list[PreparedChunk],
        page_ids: dict[int, str],
        section_ids: dict[str, str],
    ) -> None:
        records: list[dict[str, Any]] = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_index} has no embedding.")
            records.append(
                {
                    "document_id": document_id,
                    "page_id": page_ids[chunk.pdf_page_start],
                    "section_id": section_ids.get(chunk.section_local_key or ""),
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                    "embedding_text": chunk.embedding_text,
                    "section_title": chunk.section_title,
                    "article_number": chunk.article_number,
                    "pdf_page_start": chunk.pdf_page_start,
                    "pdf_page_end": chunk.pdf_page_end,
                    "printed_page_start": chunk.printed_page_start,
                    "printed_page_end": chunk.printed_page_end,
                    "language": chunk.language,
                    "academic_year": chunk.academic_year,
                    "document_status": chunk.document_status,
                    "token_count": chunk.token_count,
                    "embedding": chunk.embedding,
                }
            )
        for batch in _batches(records, size=100):
            self._client.table("chunks").insert(batch).execute()

    def clear_document_content(self, document_id: str) -> None:
        self._client.table("chunks").delete().eq("document_id", document_id).execute()
        self._client.table("sections").delete().eq("document_id", document_id).execute()
        self._client.table("pages").delete().eq("document_id", document_id).execute()

    def delete_document(self, document_id: str) -> None:
        self._client.table("documents").delete().eq("id", document_id).execute()

    def search_vector(
        self,
        embedding: list[float],
        *,
        match_count: int,
        document_type: str | None,
        language: str | None,
    ) -> list[dict[str, Any]]:
        response = self._client.rpc(
            "match_chunks",
            {
                "p_query_embedding": embedding,
                "p_match_count": match_count,
                "p_document_type": document_type,
                "p_language": language,
                "p_status": "current",
            },
        ).execute()
        return list(response.data or [])

    def search_keyword(
        self,
        query: str,
        *,
        match_count: int,
        document_type: str | None,
        language: str | None,
    ) -> list[dict[str, Any]]:
        response = self._client.rpc(
            "search_chunks_keyword",
            {
                "p_query_text": query,
                "p_match_count": match_count,
                "p_document_type": document_type,
                "p_language": language,
                "p_status": "current",
            },
        ).execute()
        return list(response.data or [])

    def search_sections(
        self,
        query: str,
        *,
        match_count: int,
        document_type: str | None,
        language: str | None,
    ) -> list[dict[str, Any]]:
        response = self._client.rpc(
            "search_sections",
            {
                "p_query_text": query,
                "p_match_count": match_count,
                "p_document_type": document_type,
                "p_language": language,
                "p_status": "current",
            },
        ).execute()
        return list(response.data or [])
