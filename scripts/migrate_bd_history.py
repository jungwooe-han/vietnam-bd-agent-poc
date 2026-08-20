from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vietnam_bd.history import export_analyses, import_analyses


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy local BD analysis history into the configured shared database."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/bd_history.sqlite3"),
        help="Path to the local SQLite history database.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("BD_HISTORY_DATABASE_URL", ""),
        help="PostgreSQL URL. Prefer setting BD_HISTORY_DATABASE_URL instead.",
    )
    args = parser.parse_args()

    if not args.source.exists():
        parser.error(f"Source history database does not exist: {args.source}")
    if not args.database_url:
        parser.error("Set BD_HISTORY_DATABASE_URL or pass --database-url.")

    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("BD_HISTORY_DATABASE_URL", None)
    os.environ["BD_HISTORY_DB_PATH"] = str(args.source.resolve())
    records = export_analyses(limit=10000)

    os.environ.pop("BD_HISTORY_DB_PATH", None)
    os.environ["BD_HISTORY_DATABASE_URL"] = args.database_url
    imported = import_analyses(records)
    print(json.dumps({"source_records": len(records), "imported": imported}))


if __name__ == "__main__":
    main()
