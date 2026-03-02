"""Servicio de seguimiento operativo (bitacora)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pandas as pd

from infra.db.connection import get_sqlite_conn
from infra.db.migrations import ensure_notes_schema, ensure_projects_schema
from infra.db.repositories.notes_repo import NotesRepository
from infra.db.repositories.project_repo import ProjectRepository


class OperationalTrackingService:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path
        self.notes_repo = NotesRepository(db_path)
        self.project_repo = ProjectRepository(db_path)

    def ensure_schema(self) -> None:
        with get_sqlite_conn(self.db_path) as conn:
            ensure_projects_schema(conn)
            ensure_notes_schema(conn)

    def add_update(
        self,
        project_id: str,
        payload_4_textareas: dict[str, str],
        author: str,
        tags: str,
        note_title: str = "",
    ) -> list[int]:
        entry_group_id = uuid.uuid4().hex
        notes = []
        for ntype in ("general", "proximo_paso", "bloqueador", "riesgo"):
            txt = str(payload_4_textareas.get(ntype, "")).strip()
            if txt:
                notes.append(
                    {
                        "project_id": project_id,
                        "note_type": ntype,
                        "note_text": txt,
                        "author": author,
                        "tags": tags,
                        "entry_group_id": entry_group_id,
                        "note_title": note_title,
                        "is_private": False,
                    }
                )
        return self.notes_repo.insert_notes_batch(notes)

    def get_executive_summary(self, filters: dict[str, Any]) -> pd.DataFrame:
        statuses = filters.get("statuses") or []
        search = (filters.get("search") or "").strip().lower()
        min_days = int(filters.get("min_days", 0) or 0)

        projects = self.project_repo.list_projects(statuses=statuses)
        rows = []
        today = date.today()

        for p in projects:
            pid = p.get("project_id") or p.get("id")
            if not pid:
                continue
            by_type = self.notes_repo.get_latest_notes_by_type(pid)
            last = self.notes_repo.get_last_note(pid)
            last_note_text = (last or {}).get("note_text", "")
            last_created = (last or {}).get("created_at")
            days_since = 99999
            if last_created:
                try:
                    days_since = max(0, (today - pd.to_datetime(last_created).date()).days)
                except Exception:
                    days_since = 99999

            row = {
                "project_id": pid,
                "name": p.get("name", ""),
                "status": p.get("status", ""),
                "days_since_last_note": days_since,
                "last_note": last_note_text,
                "last_proximo_paso": (by_type.get("proximo_paso") or {}).get("note_text", ""),
                "last_bloqueador": (by_type.get("bloqueador") or {}).get("note_text", ""),
                "last_riesgo": (by_type.get("riesgo") or {}).get("note_text", ""),
                "loop_url": p.get("loop_url", ""),
            }
            hay = " ".join([str(v) for v in row.values()]).lower()
            if search and search not in hay:
                continue
            if row["days_since_last_note"] < min_days:
                continue
            rows.append(row)

        if not rows:
            return pd.DataFrame(
                columns=[
                    "project_id",
                    "name",
                    "status",
                    "days_since_last_note",
                    "last_note",
                    "last_proximo_paso",
                    "last_bloqueador",
                    "last_riesgo",
                    "loop_url",
                ]
            )
        return pd.DataFrame(rows).sort_values(["days_since_last_note", "project_id"], ascending=[False, True])

    def get_timeline(self, filters: dict[str, Any]) -> pd.DataFrame:
        return self.notes_repo.list_notes(
            project_id=filters.get("project_id"),
            text_query=filters.get("text"),
            tag_contains=filters.get("tag"),
            note_type=filters.get("note_type"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            limit=int(filters.get("limit", 200) or 200),
        )
