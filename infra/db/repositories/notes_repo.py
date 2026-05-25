"""Repositorio de notas operativas inmutables."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from infra.db.adapter import IS_CLOUD, PLACEHOLDER, db_read_dataframe
from infra.db.connection import get_sqlite_conn


class NotesRepository:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path

    def insert_notes_batch(self, notes: list[dict[str, Any]]) -> list[int]:
        cleaned = []
        for n in notes:
            if not str(n.get("project_id", "")).strip() or not str(n.get("note_text", "")).strip():
                continue
            progress_percent = n.get("progress_percent")
            if progress_percent in ("", None):
                progress_percent = None
            elif not isinstance(progress_percent, int):
                raise ValueError("progress_percent must be an integer between 0 and 100.")
            if progress_percent is not None and not (0 <= progress_percent <= 100):
                raise ValueError("progress_percent must be between 0 and 100.")
            cleaned.append(
                (
                    str(n.get("project_id", "")).strip(),
                    str(n.get("note_text", "")).strip(),
                    str(n.get("note_type", "general")).strip(),
                    str(n.get("author", "")).strip(),
                    str(n.get("tags", "")).strip(),
                    1 if bool(n.get("is_private", False)) else 0,
                    str(n.get("entry_group_id", "")).strip(),
                    str(n.get("note_title", "")).strip(),
                    progress_percent,
                    str(n.get("estimated_end_date", "")).strip() or None,
                )
            )
        if not cleaned:
            return []

        placeholders_str = ", ".join([PLACEHOLDER] * 10)
        with get_sqlite_conn(self.db_path) as conn:
            conn.executemany(
                f"""
                INSERT INTO project_notes
                    (
                        project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title,
                        progress_percent, estimated_end_date
                    )
                VALUES ({placeholders_str})
                """,
                cleaned,
            )
            if IS_CLOUD:
                row = conn.execute("SELECT MAX(note_id) AS last_id FROM project_notes").fetchone()
            else:
                row = conn.execute("SELECT last_insert_rowid() AS last_id").fetchone()
            conn.commit()
            last_id = int(row["last_id"]) if row else 0
            first_id = max(1, last_id - len(cleaned) + 1)
            return list(range(first_id, last_id + 1))

    def list_notes(
        self,
        *,
        project_id: str | None = None,
        text_query: str | None = None,
        tag_contains: str | None = None,
        note_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 200,
    ) -> pd.DataFrame:
        sql = """
            SELECT
                note_id, project_id, note_type, note_title, author, tags, is_private, note_text, created_at,
                entry_group_id, progress_percent, estimated_end_date
            FROM project_notes
            WHERE 1=1
        """
        params: list[Any] = []
        if project_id:
            sql += f" AND project_id = {PLACEHOLDER}"
            params.append(project_id)
        if text_query:
            p = f"%{text_query.strip()}%"
            sql += f" AND (note_text LIKE {PLACEHOLDER} OR note_title LIKE {PLACEHOLDER})"
            params.extend([p, p])
        if tag_contains:
            sql += f" AND tags LIKE {PLACEHOLDER}"
            params.append(f"%{tag_contains.strip()}%")
        if note_type:
            sql += f" AND note_type = {PLACEHOLDER}"
            params.append(note_type)
        if date_from:
            sql += (
                f" AND created_at::date >= {PLACEHOLDER}::date"
                if IS_CLOUD
                else f" AND date(created_at) >= date({PLACEHOLDER})"
            )
            params.append(date_from.isoformat())
        if date_to:
            sql += (
                f" AND created_at::date <= {PLACEHOLDER}::date"
                if IS_CLOUD
                else f" AND date(created_at) <= date({PLACEHOLDER})"
            )
            params.append(date_to.isoformat())
        sql += (
            f" ORDER BY created_at DESC, note_id DESC LIMIT {PLACEHOLDER}"
            if IS_CLOUD
            else f" ORDER BY datetime(created_at) DESC, note_id DESC LIMIT {PLACEHOLDER}"
        )
        params.append(int(limit))
        with get_sqlite_conn(self.db_path) as conn:
            return db_read_dataframe(conn, sql, params=params)

    def get_latest_notes_by_type(self, project_id: str) -> dict[str, dict[str, Any]]:
        with get_sqlite_conn(self.db_path) as conn:
            if IS_CLOUD:
                sql = f"""
                    SELECT DISTINCT ON (note_type) *
                    FROM project_notes
                    WHERE project_id = {PLACEHOLDER}
                    ORDER BY note_type, created_at DESC, note_id DESC
                """
            else:
                sql = f"SELECT * FROM v_project_latest_notes WHERE project_id = {PLACEHOLDER}"
            rows = conn.execute(sql, (project_id,)).fetchall()
            return {r["note_type"]: dict(r) for r in rows}

    def get_last_note(self, project_id: str) -> dict[str, Any] | None:
        with get_sqlite_conn(self.db_path) as conn:
            if IS_CLOUD:
                sql = f"""
                    SELECT * FROM project_notes
                    WHERE project_id = {PLACEHOLDER}
                    ORDER BY created_at DESC, note_id DESC LIMIT 1
                """
            else:
                sql = f"SELECT * FROM v_project_last_note WHERE project_id = {PLACEHOLDER} LIMIT 1"
            row = conn.execute(sql, (project_id,)).fetchone()
            return dict(row) if row else None

    def get_project_progress_trend(self, project_id: str, *, limit: int = 50) -> pd.DataFrame:
        if IS_CLOUD:
            sql = f"""
                SELECT DISTINCT ON (project_id, COALESCE(NULLIF(entry_group_id, ''), CAST(note_id AS TEXT)))
                    project_id, note_id, entry_group_id, author, note_type, note_title,
                    progress_percent, estimated_end_date, created_at
                FROM project_notes
                WHERE project_id = {PLACEHOLDER}
                  AND progress_percent IS NOT NULL
                ORDER BY project_id, COALESCE(NULLIF(entry_group_id, ''), CAST(note_id AS TEXT)),
                         created_at DESC, note_id DESC
                LIMIT {PLACEHOLDER}
            """
        else:
            sql = f"""
                SELECT
                    project_id, note_id, entry_group_id, author, note_type, note_title,
                    progress_percent, estimated_end_date, created_at
                FROM v_project_progress_history
                WHERE project_id = {PLACEHOLDER}
                ORDER BY datetime(created_at) DESC, note_id DESC
                LIMIT {PLACEHOLDER}
            """
        with get_sqlite_conn(self.db_path) as conn:
            return db_read_dataframe(conn, sql, params=[project_id, int(limit)])
