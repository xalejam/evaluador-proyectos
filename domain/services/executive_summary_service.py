"""Agregados de portafolio para el resumen ejecutivo (/presentacion-ejecutiva).

Ver docs/superpowers/specs/2026-09-04-presentacion-ejecutiva-design.md en el
vault de Obsidian (repo separado) para el diseño completo. Toda cifra que
llega a un slide se calcula acá, nunca la redacta un LLM en tiempo de
ejecución — así el número no cambia de una corrida a otra.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

HOURS_PER_WEEK_FTE = 40
WEEKS_PER_MONTH = 4.345
WEEKS_PER_YEAR = 52

ALL_STATUSES = [
    "evaluated",
    "backlog",
    "approved",
    "executing",
    "implemented",
    "on_hold",
    "handed_off",
    "rejected",
]
CLOSED_STATUSES = {"implemented", "handed_off"}
STATUS_LABELS_ES = {
    "evaluated": "En evaluación",
    "backlog": "Backlog",
    "approved": "Aprobado",
    "executing": "En ejecución",
    "implemented": "Implementado",
    "on_hold": "En pausa",
    "handed_off": "Entregado",
    "rejected": "Descartado",
}


def format_fte_equivalent(total_hours: float) -> str:
    """Convierte horas totales a un texto de tiempo-persona a tiempo completo.

    Unidad automática: semanas si es poco, meses o años si es mucho, para
    que el número no suene absurdo (ej. "141 semanas" se vuelve "2 años y 9
    meses"). Base: 40h/semana = 1 persona a tiempo completo.
    """
    weeks = total_hours / HOURS_PER_WEEK_FTE

    if weeks < 8:
        whole_weeks = int(weeks)
        rem_hours = round((weeks - whole_weeks) * HOURS_PER_WEEK_FTE)
        plural = "s" if whole_weeks != 1 else ""
        if rem_hours == 0:
            return f"{whole_weeks} semana{plural}"
        return f"{whole_weeks} semana{plural} y {rem_hours} h"

    if weeks < WEEKS_PER_YEAR:
        months = weeks / WEEKS_PER_MONTH
        return f"{months:.1f} meses"

    years = weeks / WEEKS_PER_YEAR
    whole_years = int(years)
    rem_months = round((years - whole_years) * 12)
    if rem_months == 12:
        whole_years += 1
        rem_months = 0
    plural = "s" if whole_years != 1 else ""
    if rem_months == 0:
        return f"{whole_years} año{plural}"
    mes_plural = "es" if rem_months != 1 else ""
    return f"{whole_years} año{plural} y {rem_months} mes{mes_plural}"


@dataclass
class PortfolioSummary:
    hours_saved_closed: float
    closed_count: int
    executing_count: int
    fte_equivalent: str
    top_contributor: str
    status_counts: dict[str, int] = field(default_factory=dict)


def compute_portfolio_summary(projects: list[dict]) -> PortfolioSummary:
    status_counts = {s: 0 for s in ALL_STATUSES}
    closed_hours = 0.0
    top_name: str | None = None
    top_hours = 0.0

    for p in projects:
        status = p.get("status")
        if status in status_counts:
            status_counts[status] += 1
        if status in CLOSED_STATUSES:
            hours = p.get("hours_saved_per_month") or 0.0
            closed_hours += hours
            if hours > top_hours:
                top_hours = hours
                top_name = p.get("name")

    top_contributor = f"{top_name} ({top_hours:,.0f} h/mes)" if top_name else "N/D"

    return PortfolioSummary(
        hours_saved_closed=closed_hours,
        closed_count=status_counts["implemented"] + status_counts["handed_off"],
        executing_count=status_counts["executing"],
        fte_equivalent=format_fte_equivalent(closed_hours),
        top_contributor=top_contributor,
        status_counts=status_counts,
    )


def load_project_notes(path: str | None) -> dict[str, dict]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return {p["project_id"]: p for p in data.get("projects", [])}


def resolve_project_note(project: dict, notes_by_id: dict[str, dict]) -> tuple[str, str]:
    note = notes_by_id.get(project["project_id"])
    if note:
        return note.get("que_es", ""), note.get("estado_frase", "")
    que_es = f"{project['name']} — sin resumen disponible."
    label = STATUS_LABELS_ES.get(project.get("status", ""), project.get("status", ""))
    estado_frase = f"Estado: {label}."
    return que_es, estado_frase
