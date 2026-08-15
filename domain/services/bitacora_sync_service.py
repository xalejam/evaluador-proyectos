"""Sincroniza bitacora.md del vault de Obsidian con project_notes en Supabase.

Ver docs/superpowers/specs/2026-05-19-... en el vault de Obsidian
(repo separado) para el diseño completo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
ROLLUP_RE = re.compile(r"^_Acumulado del proyecto: [\d.]+h · Avance: (?:\d+%|sin dato)_\s*$")
AUTHOR_RE = re.compile(r"^### (.+?)(?: — ([\d.]+)h)?(?: _\(vía app\)_)?\s*$")
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
            entries.append(
                BitacoraEntry(
                    date=current_date,
                    author=author,
                    hours=hours,
                    via_app=via_app,
                    entry_group_id=entry_group_id,
                    avance_override=int(avance_match.group(1)) if avance_match else None,
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
            self.lines[j:j] = [""] + block_lines
        else:
            first_h2 = next((i for i, line in enumerate(self.lines) if DATE_RE.match(line)), len(self.lines))
            new_block = [f"## {entry.date}", ""] + block_lines + [""]
            self.lines[first_h2:first_h2] = new_block


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
    for label, note_type in _SECTION_LABELS:
        if entry.sections.get(note_type):
            parts.append(f"**{label}**")
            parts.append(entry.sections[note_type])
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"
