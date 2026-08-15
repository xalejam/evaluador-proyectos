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
