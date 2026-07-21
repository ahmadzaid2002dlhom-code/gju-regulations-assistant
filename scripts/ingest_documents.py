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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index official GJU PDF documents.")
    parser.add_argument("--manifest", default="data/sources.json")
    parser.add_argument("--title", help="Index only the source with this exact title.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract and replace an unchanged document's indexed content.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    errors = settings.ingestion_configuration_errors()
    if errors:
        print("Configuration error: " + "; ".join(errors), file=sys.stderr)
        return 2

    sources = load_source_manifest(Path(args.manifest))
    if args.title:
        sources = [source for source in sources if source.title == args.title]
    if not sources:
        print("No matching sources are configured.")
        return 0

    repository = SupabaseRepository(create_supabase_client(settings, privileged=True))
    pipeline = IngestionPipeline(
        repository,
        OpenAIEmbeddingProvider(settings),
        ocr_provider=OpenAIOCRProvider(settings),
    )
    for source in sources:
        result = pipeline.ingest(source, force=args.force)
        print(
            f"{result.title}: {result.status}; pages={result.pages}; "
            f"sections={result.sections}; chunks={result.chunks}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
