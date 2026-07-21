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


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete one indexed document and its children.")
    parser.add_argument("document_id")
    parser.add_argument(
        "--confirm-id",
        required=True,
        help="Repeat the exact document UUID to confirm deletion.",
    )
    args = parser.parse_args()
    if args.confirm_id != args.document_id:
        parser.error("--confirm-id must exactly match document_id")

    settings = get_settings()
    errors = settings.ingestion_configuration_errors()
    if errors:
        parser.error("; ".join(errors))
    repository = SupabaseRepository(create_supabase_client(settings, privileged=True))
    repository.delete_document(args.document_id)
    print(f"Deleted document {args.document_id} and its indexed children.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
