"""Sincroniza bitacora.md del vault de Obsidian con project_notes en Supabase.

Ver docs/superpowers/specs/2026-08-14-bitacora-supabase-sync-design.md en el
vault de Obsidian (repo separado) para el diseño completo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
ROLLUP_RE = re.compile(r"^_Acumulado del proyecto: [\d.]+h · Avance: (?:\d+%|sin dato)_\s*$")
AUTHOR_RE = re.compile(r"^### (.+?)(?: — (\d+(?:\.\d+)?)h)?(?: _\(vía app\)_)?\s*$")
ENTRY_GROUP_RE = re.compile(r"^<!-- entry_group_id: (\S+) -->\s*$")
AVANCE_OVERRIDE_RE = re.compile(r"\*\*Avance:\*\*\s*(\d+)%")
SECTION_LABEL_RE = re.compile(r"^\*\*(Bloqueador|Riesgo|Por dónde seguir)\*\*\s*$")

NOTE_TYPE_BY_LABEL = {
    "Bloqueador": "bloqueador",
    "Riesgo": "riesgo",
    "Por dónde seguir": "proximo_paso",
}
NOTE_TYPES_IN_ORDER = ("general", "proximo_paso", "bloqueador", "riesgo")


@dataclass
class BitacoraEntry:
    date: str
    author: str
    hours: float | None
    via_app: bool
    entry_group_id: str | None
    avance_override: int | None
    sections: dict[str, str] = field(default_factory=dict)


def parse_bitacora_markdown(text: str) -> list[BitacoraEntry]:
    lines = text.splitlines()
    entries: list[BitacoraEntry] = []
    current_date: str | None = None
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        date_match = DATE_RE.match(line)
        if date_match:
            current_date = date_match.group(1)
            i += 1
            continue
        author_match = AUTHOR_RE.match(line) if current_date else None
        if author_match:
            author = author_match.group(1).strip()
            hours = float(author_match.group(2)) if author_match.group(2) else None
            via_app = "_(vía app)_" in line
            i += 1
            entry_group_id = None
            if i < n:
                eg_match = ENTRY_GROUP_RE.match(lines[i])
                if eg_match:
                    entry_group_id = eg_match.group(1)
                    i += 1
            body_start = i
            while i < n and not DATE_RE.match(lines[i]) and not AUTHOR_RE.match(lines[i]):
                i += 1
            body = "\n".join(lines[body_start:i])
            avance_match = AVANCE_OVERRIDE_RE.search(body)
            if avance_match:
                avance_value = int(avance_match.group(1))
                if not 0 <= avance_value <= 100:
                    raise ValueError(
                        f"Avance fuera de rango (0-100): {avance_value}% en la entrada de "
                        f"{author} del {current_date}"
                    )
            entries.append(
                BitacoraEntry(
                    date=current_date,
                    author=author,
                    hours=hours,
                    via_app=via_app,
                    entry_group_id=entry_group_id,
                    avance_override=avance_value if avance_match else None,
                    sections=_split_sections(body),
                )
            )
            continue
        i += 1
    return entries


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"general": []}
    current = "general"
    for line in body.splitlines():
        label_match = SECTION_LABEL_RE.match(line.strip())
        if label_match:
            current = NOTE_TYPE_BY_LABEL[label_match.group(1)]
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


SLUG_RE = re.compile(r"[^a-z0-9]+")
_ACCENTS = str.maketrans("áéíóúñ", "aeioun")


def slugify_author(author: str) -> str:
    normalized = author.strip().lower().translate(_ACCENTS)
    return SLUG_RE.sub("-", normalized).strip("-")


def build_entry_group_id(project_id: str, date: str, author: str, existing_ids: set[str]) -> str:
    base = f"{project_id}-{date}-{slugify_author(author)}"
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


class BitacoraDocument:
    def __init__(self, text: str) -> None:
        self.lines: list[str] = text.splitlines()

    def entries(self) -> list[BitacoraEntry]:
        return parse_bitacora_markdown("\n".join(self.lines))

    def known_entry_group_ids(self) -> set[str]:
        return {e.entry_group_id for e in self.entries() if e.entry_group_id}

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"

    def assign_missing_entry_group_ids(self, project_id: str) -> list[BitacoraEntry]:
        """Inserta <!-- entry_group_id: ... --> bajo cada H3 sin id.
        Devuelve las entradas recién asignadas (no las que ya tenían id)."""
        ids_before = self.known_entry_group_ids()
        used_ids = set(ids_before)
        i = 0
        current_date: str | None = None
        while i < len(self.lines):
            line = self.lines[i]
            date_match = DATE_RE.match(line)
            if date_match:
                current_date = date_match.group(1)
                i += 1
                continue
            author_match = AUTHOR_RE.match(line) if current_date else None
            if author_match:
                has_id = i + 1 < len(self.lines) and ENTRY_GROUP_RE.match(self.lines[i + 1])
                if not has_id:
                    author = author_match.group(1).strip()
                    new_id = build_entry_group_id(project_id, current_date, author, used_ids)
                    used_ids.add(new_id)
                    self.lines.insert(i + 1, f"<!-- entry_group_id: {new_id} -->")
                    i += 1
                i += 1
                continue
            i += 1
        return [e for e in self.entries() if e.entry_group_id and e.entry_group_id not in ids_before]

    def append_pulled_entry(self, entry: BitacoraEntry) -> None:
        block_lines = render_entry_block(entry).splitlines()
        date_idx = next(
            (i for i, line in enumerate(self.lines) if DATE_RE.match(line) and DATE_RE.match(line).group(1) == entry.date),
            None,
        )
        if date_idx is not None:
            j = date_idx + 1
            while j < len(self.lines) and not DATE_RE.match(self.lines[j]):
                j += 1
            prefix = [] if (j > 0 and self.lines[j - 1].strip() == "") else [""]
            self.lines[j:j] = prefix + block_lines + [""]
        else:
            first_h2 = next((i for i, line in enumerate(self.lines) if DATE_RE.match(line)), len(self.lines))
            new_block = [f"## {entry.date}", ""] + block_lines + [""]
            self.lines[first_h2:first_h2] = new_block

    def set_rollup(self, date: str, total_hours: float, progress_percent: int | None) -> None:
        for i, line in enumerate(self.lines):
            m = DATE_RE.match(line)
            if m and m.group(1) == date:
                rollup_text = _format_rollup(total_hours, progress_percent)
                j = i + 1
                if j < len(self.lines) and self.lines[j].strip() == "":
                    j += 1
                if j < len(self.lines) and ROLLUP_RE.match(self.lines[j]):
                    self.lines[j] = rollup_text
                else:
                    self.lines[i + 1:i + 1] = ["", rollup_text]
                return
        raise ValueError(f"No existe la fecha {date} en el documento")


_SECTION_LABELS = (("Bloqueador", "bloqueador"), ("Riesgo", "riesgo"), ("Por dónde seguir", "proximo_paso"))


def render_entry_block(entry: BitacoraEntry) -> str:
    header = f"### {entry.author}"
    if entry.hours is not None:
        header += f" — {entry.hours:g}h"
    if entry.via_app:
        header += " _(vía app)_"
    parts = [header, f"<!-- entry_group_id: {entry.entry_group_id} -->", ""]
    if entry.sections.get("general"):
        parts.append(entry.sections["general"])
        parts.append("")
    if entry.avance_override is not None:
        parts.append(f"**Avance:** {entry.avance_override}%")
        parts.append("")
    for label, note_type in _SECTION_LABELS:
        if entry.sections.get(note_type):
            parts.append(f"**{label}**")
            parts.append(entry.sections[note_type])
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _format_rollup(total_hours: float, progress_percent: int | None) -> str:
    avance_text = f"{progress_percent}%" if progress_percent is not None else "sin dato"
    return f"_Acumulado del proyecto: {total_hours:g}h · Avance: {avance_text}_"


from infra.db.adapter import IS_CLOUD, PLACEHOLDER  # noqa: E402


def project_exists(conn, project_id: str) -> bool:
    row = conn.execute(f"SELECT 1 FROM projects WHERE project_id = {PLACEHOLDER}", (project_id,)).fetchone()
    return row is not None


def find_existing_entry_group_ids(conn, project_id: str) -> set[str]:
    rows = conn.execute(
        f"SELECT DISTINCT entry_group_id FROM project_notes "
        f"WHERE project_id = {PLACEHOLDER} AND entry_group_id IS NOT NULL AND entry_group_id != ''",
        (project_id,),
    ).fetchall()
    return {(r["entry_group_id"] if isinstance(r, dict) else r[0]) for r in rows}


def push_entry(conn, project_id: str, entry: BitacoraEntry) -> int:
    """Inserta una fila de project_notes por cada sección presente.
    Las horas solo se guardan en la fila 'general' — ver Global Constraints
    del plan sobre por qué no se reusa NotesRepository.insert_notes_batch."""
    inserted = 0
    created_at = f"{entry.date} 12:00:00"
    for note_type in NOTE_TYPES_IN_ORDER:
        text = entry.sections.get(note_type, "").strip()
        if not text:
            continue
        effort_hours = entry.hours if note_type == "general" else None
        conn.execute(
            f"""
            INSERT INTO project_notes
                (project_id, note_text, note_type, author, tags, is_private,
                 entry_group_id, note_title, progress_percent, estimated_end_date,
                 effort_hours, created_at)
            VALUES ({', '.join([PLACEHOLDER] * 12)})
            """,
            (
                project_id, text, note_type, entry.author, "", 0,
                entry.entry_group_id, "", entry.avance_override, None,
                effort_hours, created_at,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def compute_rollup(conn, project_id: str) -> tuple[float, int | None]:
    hours_row = conn.execute(
        f"SELECT COALESCE(SUM(effort_hours), 0) AS total FROM project_notes WHERE project_id = {PLACEHOLDER}",
        (project_id,),
    ).fetchone()
    total_hours = float(hours_row["total"] if isinstance(hours_row, dict) else hours_row[0])

    order_by = "created_at DESC, note_id DESC" if IS_CLOUD else "datetime(created_at) DESC, note_id DESC"
    progress_row = conn.execute(
        f"""
        SELECT progress_percent FROM project_notes
        WHERE project_id = {PLACEHOLDER} AND progress_percent IS NOT NULL
        ORDER BY {order_by} LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    progress_percent = None
    if progress_row is not None:
        val = progress_row["progress_percent"] if isinstance(progress_row, dict) else progress_row[0]
        progress_percent = int(val) if val is not None else None
    return total_hours, progress_percent


def pull_new_entries(conn, project_id: str, known_ids: set[str]) -> list[BitacoraEntry]:
    order_by = "created_at ASC, note_id ASC" if IS_CLOUD else "datetime(created_at) ASC, note_id ASC"
    rows = conn.execute(
        f"""
        SELECT note_id, note_type, note_text, author, effort_hours, created_at,
               entry_group_id, progress_percent
        FROM project_notes
        WHERE project_id = {PLACEHOLDER} AND entry_group_id IS NOT NULL AND entry_group_id != ''
        ORDER BY {order_by}
        """,
        (project_id,),
    ).fetchall()

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        row = dict(r) if not isinstance(r, dict) else r
        gid = row["entry_group_id"]
        if gid in known_ids:
            continue
        grouped.setdefault(gid, []).append(row)

    entries: list[BitacoraEntry] = []
    for gid, group_rows in grouped.items():
        first = group_rows[0]
        sections = {r["note_type"]: r["note_text"] for r in group_rows if r["note_text"]}
        hours = next((r["effort_hours"] for r in group_rows if r["effort_hours"] is not None), None)
        avance = next((r["progress_percent"] for r in group_rows if r["progress_percent"] is not None), None)
        entries.append(
            BitacoraEntry(
                date=str(first["created_at"])[:10],
                author=first["author"],
                hours=float(hours) if hours is not None else None,
                via_app=True,
                entry_group_id=gid,
                avance_override=int(avance) if avance is not None else None,
                sections=sections,
            )
        )
    return entries


from pathlib import Path  # noqa: E402

from infra.db_migrations import get_project_members  # noqa: E402

FRONTMATTER_PROJECT_ID_RE = re.compile(r"^project_id:\s*(\S+)\s*$", re.MULTILINE)


def read_frontmatter_project_id(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = FRONTMATTER_PROJECT_ID_RE.search(text[3:end])
    return m.group(1) if m else None


def sync_bitacora_file(conn, vault_path: Path) -> dict:
    text = vault_path.read_text(encoding="utf-8")
    project_id = read_frontmatter_project_id(text)
    if not project_id or not project_exists(conn, project_id):
        return {"pushed": 0, "pulled": 0, "skipped": True, "project_id": project_id}

    doc = BitacoraDocument(text)
    new_local_entries = doc.assign_missing_entry_group_ids(project_id)

    # Fix 1: no confiar solo en los <!-- entry_group_id --> del archivo local
    # (git checkout/reset, merge conflicts o clones viejos pueden perder ese
    # comentario). Antes de insertar, verificar contra lo que ya existe en
    # Supabase para evitar duplicar filas inmutables.
    existing_supabase_ids = find_existing_entry_group_ids(conn, project_id)
    entries_to_push = [e for e in new_local_entries if e.entry_group_id not in existing_supabase_ids]
    for entry in entries_to_push:
        push_entry(conn, project_id, entry)

    known_ids = doc.known_entry_group_ids()
    pulled_entries = pull_new_entries(conn, project_id, known_ids)
    for entry in pulled_entries:
        doc.append_pulled_entry(entry)

    touched_dates = {e.date for e in entries_to_push} | {e.date for e in pulled_entries}
    if touched_dates:
        total_hours, progress_percent = compute_rollup(conn, project_id)
        doc.set_rollup(max(touched_dates), total_hours, progress_percent)

    # Fix 4: avisar de autores que no están dados de alta como miembro del
    # proyecto (typos silenciosos que "Carga del equipo" nunca mostraría).
    # Si el proyecto no tiene miembros registrados todavía no se avisa: es
    # un hueco preexistente distinto al de este fix.
    unknown_authors: list[str] = []
    members = get_project_members(conn, project_id)
    if members:
        member_set = set(members)
        unknown_authors = sorted(
            {e.author for e in new_local_entries + pulled_entries if e.author not in member_set}
        )

    if new_local_entries or pulled_entries:
        vault_path.write_text(doc.render(), encoding="utf-8")

    return {
        "pushed": len(entries_to_push),
        "pulled": len(pulled_entries),
        "skipped": False,
        "project_id": project_id,
        "unknown_authors": unknown_authors,
    }
