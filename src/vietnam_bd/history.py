from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4


DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "bd_history.sqlite3"
DATABASE_URL_KEYS = ("BD_HISTORY_DATABASE_URL", "DATABASE_URL")


@dataclass(frozen=True)
class HistorySummary:
    history_id: str
    title: str
    seed_preview: str
    result_version: str
    created_at: str
    status: str
    engine: str
    research_provider: str
    updated_at: str


@dataclass(frozen=True)
class HistoryRecord(HistorySummary):
    seed: str
    result: dict[str, Any]
    research_trace: dict[str, Any]
    guided_context: str
    error_message: str


def _database_path() -> Path:
    configured = os.getenv("BD_HISTORY_DB_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_HISTORY_PATH


def _database_url() -> str:
    for key in DATABASE_URL_KEYS:
        if value := os.getenv(key, "").strip():
            return value

    # Streamlit Community Cloud exposes secrets through st.secrets rather than
    # ordinary environment variables. Keep this module usable without Streamlit.
    try:
        import streamlit as st

        for key in DATABASE_URL_KEYS:
            value = str(st.secrets.get(key, "")).strip()
            if value:
                return value
    except Exception:
        pass
    return ""


class _Connection:
    def __init__(self, raw: Any, *, backend: str) -> None:
        self.raw = raw
        self.backend = backend

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if self.backend == "postgresql":
            sql = sql.replace("?", "%s")
        return self.raw.execute(sql, params)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


def _initialize_sqlite(raw: sqlite3.Connection) -> None:
    raw.execute("PRAGMA busy_timeout = 30000")
    raw.execute(
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
    migrations = {
        "status": "TEXT NOT NULL DEFAULT 'completed'",
        "engine": "TEXT NOT NULL DEFAULT ''",
        "research_provider": "TEXT NOT NULL DEFAULT 'existing'",
        "guided_context": "TEXT NOT NULL DEFAULT ''",
        "error_message": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    columns = {row["name"] for row in raw.execute("PRAGMA table_info(bd_analysis_history)")}
    for name, declaration in migrations.items():
        if name not in columns:
            raw.execute(f"ALTER TABLE bd_analysis_history ADD COLUMN {name} {declaration}")


def _initialize_postgresql(raw: Any) -> None:
    raw.execute(
        """
        CREATE TABLE IF NOT EXISTS bd_analysis_history (
            history_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            seed TEXT NOT NULL,
            seed_preview TEXT NOT NULL,
            result_version TEXT NOT NULL,
            result_json TEXT NOT NULL DEFAULT '{}',
            research_trace_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            engine TEXT NOT NULL DEFAULT '',
            research_provider TEXT NOT NULL DEFAULT 'existing',
            guided_context TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    migrations = {
        "status": "TEXT NOT NULL DEFAULT 'completed'",
        "engine": "TEXT NOT NULL DEFAULT ''",
        "research_provider": "TEXT NOT NULL DEFAULT 'existing'",
        "guided_context": "TEXT NOT NULL DEFAULT ''",
        "error_message": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    for name, declaration in migrations.items():
        raw.execute(
            f"ALTER TABLE bd_analysis_history ADD COLUMN IF NOT EXISTS {name} {declaration}"
        )


def _connect() -> _Connection:
    database_url = _database_url()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Shared BD history requires psycopg. Install project requirements first."
            ) from exc
        raw = psycopg.connect(database_url, row_factory=dict_row, connect_timeout=15)
        _initialize_postgresql(raw)
        return _Connection(raw, backend="postgresql")

    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(path, timeout=30)
    raw.row_factory = sqlite3.Row
    _initialize_sqlite(raw)
    return _Connection(raw, backend="sqlite")


@contextmanager
def _connection():
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def start_analysis(
    *,
    seed: str,
    engine: str,
    research_provider: str = "existing",
    guided_context: str = "",
) -> str:
    """Persist an analysis attempt before any external search or AI call starts."""

    history_id = uuid4().hex
    created_at = _now()
    title = " ".join(seed.split())[:120] or "Untitled BD analysis"
    with _connection() as connection:
        connection.execute(
            """INSERT INTO bd_analysis_history
            (history_id, title, seed, seed_preview, result_version, result_json,
             research_trace_json, created_at, status, engine, research_provider,
             guided_context, error_message, updated_at)
            VALUES (?, ?, ?, ?, ?, '{}', '{}', ?, 'running', ?, ?, ?, '', ?)""",
            (
                history_id,
                title,
                seed,
                " ".join(seed.split())[:120],
                "pending",
                created_at,
                engine,
                research_provider,
                guided_context,
                created_at,
            ),
        )
    return history_id


def update_analysis_progress(history_id: str, research_trace: dict[str, Any]) -> None:
    with _connection() as connection:
        connection.execute(
            """UPDATE bd_analysis_history
            SET research_trace_json = ?, updated_at = ? WHERE history_id = ?""",
            (json.dumps(research_trace, ensure_ascii=False), _now(), history_id),
        )


def complete_analysis(
    history_id: str,
    *,
    result_version: str,
    result: dict[str, Any],
    research_trace: dict[str, Any] | None = None,
) -> None:
    title = str(result.get("opportunity_title") or "Untitled BD analysis")
    with _connection() as connection:
        connection.execute(
            """UPDATE bd_analysis_history
            SET title = ?, result_version = ?, result_json = ?, research_trace_json = ?,
                status = 'completed', error_message = '', updated_at = ?
            WHERE history_id = ?""",
            (
                title,
                result_version,
                json.dumps(result, ensure_ascii=False),
                json.dumps(research_trace or {}, ensure_ascii=False),
                _now(),
                history_id,
            ),
        )


def fail_analysis(
    history_id: str,
    *,
    error_message: str,
    research_trace: dict[str, Any] | None = None,
) -> None:
    with _connection() as connection:
        connection.execute(
            """UPDATE bd_analysis_history
            SET status = 'failed', error_message = ?, research_trace_json = ?, updated_at = ?
            WHERE history_id = ?""",
            (
                error_message[:2000],
                json.dumps(research_trace or {}, ensure_ascii=False),
                _now(),
                history_id,
            ),
        )


def save_analysis(
    *,
    seed: str,
    result_version: str,
    result: dict[str, Any],
    research_trace: dict[str, Any] | None = None,
) -> str:
    """Backward-compatible one-shot persistence for completed analyses."""

    history_id = start_analysis(seed=seed, engine=result_version)
    complete_analysis(
        history_id,
        result_version=result_version,
        result=result,
        research_trace=research_trace,
    )
    return history_id


def list_analyses(limit: int = 200) -> list[HistorySummary]:
    safe_limit = max(1, min(limit, 1000))
    with _connection() as connection:
        rows = connection.execute(
            """SELECT history_id, title, seed_preview, result_version, created_at,
                      status, engine, research_provider, updated_at
            FROM bd_analysis_history
            ORDER BY created_at DESC, updated_at DESC, history_id DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
    return [HistorySummary(**dict(row)) for row in rows]


def _record_from_row(row: Mapping[str, Any]) -> HistoryRecord:
    return HistoryRecord(
        history_id=row["history_id"],
        title=row["title"],
        seed=row["seed"],
        seed_preview=row["seed_preview"],
        result_version=row["result_version"],
        result=json.loads(row["result_json"]),
        research_trace=json.loads(row["research_trace_json"]),
        created_at=row["created_at"],
        status=row["status"],
        engine=row["engine"],
        research_provider=row["research_provider"],
        updated_at=row["updated_at"],
        guided_context=row["guided_context"],
        error_message=row["error_message"],
    )


def get_analysis(history_id: str) -> HistoryRecord | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM bd_analysis_history WHERE history_id = ?", (history_id,)
        ).fetchone()
    return _record_from_row(row) if row is not None else None


def export_analyses(limit: int = 1000) -> list[dict[str, Any]]:
    """Return complete history records for an explicit backup or migration."""

    safe_limit = max(1, min(limit, 10000))
    with _connection() as connection:
        rows = connection.execute(
            """SELECT * FROM bd_analysis_history
            ORDER BY created_at ASC, updated_at ASC, history_id ASC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
    return [asdict(_record_from_row(row)) for row in rows]


def import_analyses(records: Iterable[Mapping[str, Any]]) -> int:
    """Idempotently copy exported analyses into the configured history store."""

    imported = 0
    with _connection() as connection:
        for record in records:
            params = (
                str(record["history_id"]),
                str(record.get("title") or "Untitled BD analysis"),
                str(record.get("seed") or ""),
                str(record.get("seed_preview") or ""),
                str(record.get("result_version") or "pending"),
                json.dumps(record.get("result") or {}, ensure_ascii=False),
                json.dumps(record.get("research_trace") or {}, ensure_ascii=False),
                str(record.get("created_at") or _now()),
                str(record.get("status") or "completed"),
                str(record.get("engine") or ""),
                str(record.get("research_provider") or "existing"),
                str(record.get("guided_context") or ""),
                str(record.get("error_message") or ""),
                str(record.get("updated_at") or record.get("created_at") or _now()),
            )
            if connection.backend == "postgresql":
                cursor = connection.execute(
                    """INSERT INTO bd_analysis_history
                    (history_id, title, seed, seed_preview, result_version, result_json,
                     research_trace_json, created_at, status, engine, research_provider,
                     guided_context, error_message, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (history_id) DO NOTHING""",
                    params,
                )
            else:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO bd_analysis_history
                    (history_id, title, seed, seed_preview, result_version, result_json,
                     research_trace_json, created_at, status, engine, research_provider,
                     guided_context, error_message, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    params,
                )
            imported += max(cursor.rowcount, 0)
    return imported
