"""Repositorio de notas operativas inmutables."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from infra.db.connection import get_sqlite_conn


class NotesRepository:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path

    def insert_notes_batch(self, notes: list[dict[str, Any]]) -> list[int]:
        cleaned = []
        for n in notes:
            if not str(n.get("project_id", "")).strip() or not str(n.get("note_text", "")).strip():
                continue
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
                )
            )
        if not cleaned:
            return []

        with get_sqlite_conn(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO project_notes
                    (project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                cleaned,
            )
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
            SELECT note_id, project_id, note_type, note_title, author, tags, is_private, note_text, created_at, entry_group_id
            FROM project_notes
            WHERE 1=1
        """
        params: list[Any] = []
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if text_query:
            p = f"%{text_query.strip()}%"
            sql += " AND (note_text LIKE ? OR note_title LIKE ?)"
            params.extend([p, p])
        if tag_contains:
            sql += " AND tags LIKE ?"
            params.append(f"%{tag_contains.strip()}%")
        if note_type:
            sql += " AND note_type = ?"
            params.append(note_type)
        if date_from:
            sql += " AND date(created_at) >= date(?)"
            params.append(date_from.isoformat())
        if date_to:
            sql += " AND date(created_at) <= date(?)"
            params.append(date_to.isoformat())
        sql += " ORDER BY datetime(created_at) DESC, note_id DESC LIMIT ?"
        params.append(int(limit))
        with get_sqlite_conn(self.db_path) as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def get_latest_notes_by_type(self, project_id: str) -> dict[str, dict[str, Any]]:
        with get_sqlite_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM v_project_latest_notes WHERE project_id = ?",
                (project_id,),
            ).fetchall()
            return {r["note_type"]: dict(r) for r in rows}

    def get_last_note(self, project_id: str) -> dict[str, Any] | None:
        with get_sqlite_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM v_project_last_note WHERE project_id = ? LIMIT 1",
                (project_id,),
            ).fetchone()
            return dict(row) if row else None
