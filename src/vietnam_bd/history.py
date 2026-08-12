from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "bd_history.sqlite3"


@dataclass(frozen=True)
class HistorySummary:
    history_id: str
    title: str
    seed_preview: str
    result_version: str
    created_at: str


@dataclass(frozen=True)
class HistoryRecord(HistorySummary):
    seed: str
    result: dict[str, Any]
    research_trace: dict[str, Any]


def _database_path() -> Path:
    configured = os.getenv("BD_HISTORY_DB_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_HISTORY_PATH


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bd_analysis_history (
            history_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            seed TEXT NOT NULL,
            seed_preview TEXT NOT NULL,
            result_version TEXT NOT NULL,
            result_json TEXT NOT NULL,
            research_trace_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def save_analysis(*, seed: str, result_version: str, result: dict[str, Any], research_trace: dict[str, Any] | None = None) -> str:
    history_id = uuid4().hex
    title = str(result.get("opportunity_title") or seed.strip() or "제목 없는 BD 분석")
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute(
            """INSERT INTO bd_analysis_history
            (history_id, title, seed, seed_preview, result_version, result_json, research_trace_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (history_id, title, seed, " ".join(seed.split())[:120], result_version,
             json.dumps(result, ensure_ascii=False), json.dumps(research_trace or {}, ensure_ascii=False), created_at),
        )
    return history_id


def list_analyses(limit: int = 50) -> list[HistorySummary]:
    safe_limit = max(1, min(limit, 200))
    with _connect() as connection:
        rows = connection.execute(
            """SELECT history_id, title, seed_preview, result_version, created_at
            FROM bd_analysis_history ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
    return [HistorySummary(**dict(row)) for row in rows]


def get_analysis(history_id: str) -> HistoryRecord | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM bd_analysis_history WHERE history_id = ?", (history_id,)).fetchone()
    if row is None:
        return None
    return HistoryRecord(
        history_id=row["history_id"], title=row["title"], seed=row["seed"],
        seed_preview=row["seed_preview"], result_version=row["result_version"],
        result=json.loads(row["result_json"]), research_trace=json.loads(row["research_trace_json"]),
        created_at=row["created_at"],
    )

