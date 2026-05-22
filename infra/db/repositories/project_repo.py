"""Repositorio de proyectos compatible con PostgreSQL (cloud) y SQLite (local)."""

from __future__ import annotations

from typing import Any

from infra.db.adapter import PLACEHOLDER, db_now, db_table_columns
from infra.db.connection import get_sqlite_conn


class ProjectRepository:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with get_sqlite_conn(self.db_path) as conn:
            row = conn.execute(
                f"SELECT * FROM projects WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER} LIMIT 1",
                (project_id, project_id),
            ).fetchone()
            return dict(row) if row else None

    def upsert_project(self, project_payload: dict[str, Any]) -> str:
        project_id = str(project_payload.get("id") or project_payload.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("project_id/id es obligatorio para upsert_project")

        with get_sqlite_conn(self.db_path) as conn:
            exists = conn.execute(
                f"SELECT 1 FROM projects WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER} LIMIT 1",
                (project_id, project_id),
            ).fetchone()
            cols = db_table_columns(conn, "projects")

            if exists:
                updates = {k: v for k, v in project_payload.items() if k in cols and k not in ("id", "project_id")}
                if updates:
                    set_sql = ", ".join([f"{k} = {PLACEHOLDER}" for k in updates.keys()])
                    params = list(updates.values()) + [project_id, project_id]
                    conn.execute(
                        f"UPDATE projects SET {set_sql} WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}", params
                    )
            else:
                record = dict(project_payload)
                record.setdefault("id", project_id)
                if "project_id" in cols:
                    record.setdefault("project_id", project_id)
                valid = {k: v for k, v in record.items() if k in cols}
                if not valid:
                    raise ValueError("No hay columnas válidas para insertar proyecto")
                col_sql = ", ".join(valid.keys())
                val_sql = ", ".join([PLACEHOLDER] * len(valid))
                conn.execute(
                    f"INSERT INTO projects ({col_sql}) VALUES ({val_sql}) ON CONFLICT (id) DO NOTHING",
                    tuple(valid.values()),
                )
            conn.commit()
        return project_id

    def update_status(
        self,
        project_id: str,
        status: str,
        loop_url: str | None = None,
        delivery_team: str | None = None,
    ) -> None:
        with get_sqlite_conn(self.db_path) as conn:
            cols = db_table_columns(conn, "projects")
            updates = [f"status = {PLACEHOLDER}", f"updated_at = {PLACEHOLDER}"]
            params: list[Any] = [status, db_now()]
            if loop_url is not None and "loop_url" in cols:
                updates.append(f"loop_url = {PLACEHOLDER}")
                params.append(loop_url)
            if delivery_team is not None and "delivery_team" in cols:
                updates.append(f"delivery_team = {PLACEHOLDER}")
                params.append(delivery_team)
            params.extend([project_id, project_id])
            conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}",
                params,
            )
            conn.commit()

    def update_project_links(
        self,
        project_id: str,
        *,
        loop_url: str | None = None,
        repo_url: str | None = None,
        artifacts_url: str | None = None,
        artifacts_type: str | None = None,
        tech_stack: str | None = None,
    ) -> None:
        with get_sqlite_conn(self.db_path) as conn:
            cols = db_table_columns(conn, "projects")
            updates = [f"updated_at = {PLACEHOLDER}"]
            params: list[Any] = [db_now()]

            mapping = {
                "loop_url": loop_url,
                "repo_url": repo_url,
                "artifacts_url": artifacts_url,
                "artifacts_type": artifacts_type,
                "tech_stack": tech_stack,
            }
            for col, val in mapping.items():
                if val is not None and col in cols:
                    updates.append(f"{col} = {PLACEHOLDER}")
                    params.append(str(val).strip())

            if len(updates) == 1:
                return

            params.extend([project_id, project_id])
            conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}",
                params,
            )
            conn.commit()

    def get_project_links(self, project_id: str) -> dict[str, Any]:
        with get_sqlite_conn(self.db_path) as conn:
            cols = db_table_columns(conn, "projects")
            id_expr = "project_id" if "project_id" in cols else "id"
            select_cols = ["id", id_expr]
            for col in ("loop_url", "repo_url", "artifacts_url", "artifacts_type", "tech_stack"):
                if col in cols:
                    select_cols.append(col)
            row = conn.execute(
                f"SELECT {', '.join(dict.fromkeys(select_cols))} FROM projects WHERE id = {PLACEHOLDER} OR {id_expr} = {PLACEHOLDER} LIMIT 1",
                (project_id, project_id),
            ).fetchone()
            if not row:
                return {}
            data = dict(row)
            return {
                "project_id": data.get("project_id") or data.get("id") or project_id,
                "loop_url": data.get("loop_url", "") or "",
                "repo_url": data.get("repo_url", "") or "",
                "artifacts_url": data.get("artifacts_url", "") or "",
                "artifacts_type": data.get("artifacts_type", "") or "",
                "tech_stack": data.get("tech_stack", "") or "",
            }

    def list_projects_with_links(
        self,
        *,
        year: int | None = None,
        teams: list[str] | None = None,
        statuses: list[str] | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.list_projects(year=year, teams=teams, statuses=statuses, search=search)
        for row in rows:
            row.setdefault("loop_url", "")
            row.setdefault("repo_url", "")
            row.setdefault("artifacts_url", "")
            row.setdefault("artifacts_type", "")
            row.setdefault("tech_stack", "")
        return rows

    def list_projects(
        self,
        *,
        year: int | None = None,
        teams: list[str] | None = None,
        statuses: list[str] | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM projects WHERE 1=1"
        params: list[Any] = []
        if statuses:
            sql += f" AND status IN ({','.join([PLACEHOLDER]*len(statuses))})"
            params.extend(statuses)
        if teams:
            sql += f" AND delivery_team IN ({','.join([PLACEHOLDER]*len(teams))})"
            params.extend(teams)
        if year:
            sql += f" AND LEFT(COALESCE(updated_at, created_date, ''), 4) = {PLACEHOLDER}"
            params.append(str(year))
        if search:
            q = f"%{search.strip()}%"
            sql += f" AND (COALESCE(name,'') LIKE {PLACEHOLDER} OR COALESCE(owner,'') LIKE {PLACEHOLDER} OR COALESCE(project_id,id,'') LIKE {PLACEHOLDER})"
            params.extend([q, q, q])
        sql += " ORDER BY COALESCE(updated_at, created_date, '') DESC"
        with get_sqlite_conn(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
