from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database.repositories import SupabaseRepository
from src.database.supabase_client import create_supabase_client
from src.ingestion.embedding_service import OpenAIEmbeddingProvider
from src.ingestion.ingestion_pipeline import IngestionPipeline, load_source_manifest
from src.ingestion.ocr_service import OpenAIOCRProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Reindex one configured GJU document.")
    parser.add_argument("title", help="Exact title from data/sources.json")
    parser.add_argument("--manifest", default="data/sources.json")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm replacement of the document's current index records.",
    )
    args = parser.parse_args()
    if not args.confirm:
        parser.error("--confirm is required because reindexing replaces existing index rows")

    source = next(
        (item for item in load_source_manifest(args.manifest) if item.title == args.title),
        None,
    )
    if source is None:
        parser.error(f"No source named {args.title!r} exists in the manifest")

    settings = get_settings()
    errors = settings.ingestion_configuration_errors()
    if errors:
        parser.error("; ".join(errors))
    repository = SupabaseRepository(create_supabase_client(settings, privileged=True))
    pipeline = IngestionPipeline(
        repository,
        OpenAIEmbeddingProvider(settings),
        ocr_provider=OpenAIOCRProvider(settings),
    )
    result = pipeline.ingest(source, force=True)
    print(f"{result.title}: {result.status}; chunks={result.chunks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
