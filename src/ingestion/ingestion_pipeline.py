from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import TypeAdapter

from src.database.repositories import SupabaseRepository
from src.ingestion.chunker import create_chunks
from src.ingestion.downloader import calculate_checksum, download_pdf, safe_pdf_filename
from src.ingestion.embedding_service import EmbeddingProvider
from src.ingestion.heading_detector import detect_sections
from src.ingestion.pdf_extractor import OCRProvider, extract_pdf_pages
from src.models import DetectedSection, ExtractedPage, PreparedChunk, SourceDefinition


@dataclass(slots=True)
class IngestionResult:
    title: str
    status: str
    document_id: str | None
    pages: int = 0
    sections: int = 0
    chunks: int = 0


def load_source_manifest(path: str | Path) -> list[SourceDefinition]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return TypeAdapter(list[SourceDefinition]).validate_python(payload)


def _apply_section_titles(
    pages: list[ExtractedPage], sections: list[DetectedSection]
) -> None:
    for page in pages:
        matches = [
            section
            for section in sections
            if section.page_start <= page.pdf_page_number <= section.page_end
        ]
        if matches:
            page.section_title = max(matches, key=lambda item: item.hierarchy_level).title


def _write_processed_snapshot(
    processed_dir: Path,
    filename: str,
    pages: list[ExtractedPage],
    sections: list[DetectedSection],
    chunks: list[PreparedChunk],
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "pages": [asdict(page) for page in pages],
        "sections": [asdict(section) for section in sections],
        "chunks": [
            {key: value for key, value in asdict(chunk).items() if key != "embedding"}
            for chunk in chunks
        ],
    }
    (processed_dir / f"{Path(filename).stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class IngestionPipeline:
    def __init__(
        self,
        repository: SupabaseRepository,
        embedding_provider: EmbeddingProvider,
        *,
        raw_dir: Path = Path("data/raw"),
        processed_dir: Path = Path("data/processed"),
        embedding_batch_size: int = 32,
        ocr_provider: OCRProvider | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._raw_dir = raw_dir
        self._processed_dir = processed_dir
        self._embedding_batch_size = embedding_batch_size
        self._ocr_provider = ocr_provider

    def ingest(self, source: SourceDefinition, *, force: bool = False) -> IngestionResult:
        filename = safe_pdf_filename(source.title, str(source.url))
        pdf_path = self._raw_dir / filename
        content = download_pdf(str(source.url), pdf_path)
        checksum = calculate_checksum(content)
        existing = self._repository.find_document_by_checksum(str(source.url), checksum)

        if existing and not force:
            return IngestionResult(
                title=source.title,
                status="unchanged",
                document_id=str(existing["id"]),
            )

        old_current = self._repository.current_documents_for_url(str(source.url))
        supersedes = str(old_current[0]["id"]) if old_current else None
        document_id = self._repository.create_document(
            source,
            checksum,
            pdf_path.as_posix(),
            supersedes,
        )

        try:
            pages = extract_pdf_pages(
                pdf_path,
                ocr_provider=self._ocr_provider,
                language=source.language,
            )
            sections = detect_sections(pages)
            _apply_section_titles(pages, sections)
            chunks = create_chunks(
                pages=pages,
                sections=sections,
                document_title=source.title,
                document_type=source.document_type,
                language=source.language,
                academic_year=source.academic_year,
            )
            if not chunks:
                raise ValueError("No searchable text chunks were extracted from the PDF.")

            for start in range(0, len(chunks), self._embedding_batch_size):
                batch = chunks[start : start + self._embedding_batch_size]
                vectors = self._embedding_provider.embed_documents(
                    [chunk.embedding_text for chunk in batch]
                )
                for chunk, vector in zip(batch, vectors, strict=True):
                    chunk.embedding = vector

            page_ids = self._repository.insert_pages(document_id, pages)
            section_ids = self._repository.insert_sections(document_id, sections)
            self._repository.insert_chunks(document_id, chunks, page_ids, section_ids)
            self._repository.update_document_status(document_id, "current")
            for previous in old_current:
                previous_id = str(previous["id"])
                if previous_id != document_id:
                    self._repository.update_document_status(previous_id, "superseded")

            _write_processed_snapshot(
                self._processed_dir, filename, pages, sections, chunks
            )
            return IngestionResult(
                title=source.title,
                status="indexed",
                document_id=document_id,
                pages=len(pages),
                sections=len(sections),
                chunks=len(chunks),
            )
        except Exception:
            self._repository.delete_document(document_id)
            raise
