from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

from domain.services.executive_summary_service import (
    ALL_STATUSES,
    STATUS_LABELS_ES,
    PortfolioSummary,
    resolve_project_note,
)

PIPELINE_ORDER = ALL_STATUSES

DEFAULT_OUTPUT_PATH = Path("docs") / "Resumen_Proyectos_Ejecucion.pptx"
LOGO_PATH = Path("logo_DDNola.png")

# Paleta oficial Worldpanel (skill anthropic-skills:worldpanel-brand)
C_HEADER_BG = RGBColor(0x00, 0x4A, 0x52)  # Deep Teal
C_HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
C_HEADER_SUB = RGBColor(0x2E, 0xEF, 0xEE)  # Aqua
C_HEADER_CUT = RGBColor(0x2E, 0xEF, 0xEE)  # Aqua
C_BODY_BG = RGBColor(0xFF, 0xFF, 0xFF)
C_ROW_ODD = RGBColor(0xFF, 0xFF, 0xFF)
C_ROW_EVEN = RGBColor(0xF2, 0xF7, 0xF7)
C_ROW_BORDER = RGBColor(0xDC, 0xE6, 0xE6)
C_SEPARATOR = RGBColor(0xDC, 0xE6, 0xE6)
C_TEXT_DARK = RGBColor(0x00, 0x4A, 0x52)  # Deep Teal
C_TEXT_MID = RGBColor(0x3D, 0x63, 0x67)
C_TEXT_LIGHT = RGBColor(0x6B, 0x8A, 0x8D)
C_TEXT_BLUE = RGBColor(0x00, 0xA8, 0xB8)  # Worldpanel Blue
C_TEXT_BLUE2 = RGBColor(0x2E, 0xEF, 0xEE)  # Aqua
C_CARD_BG = RGBColor(0xEA, 0xF6, 0xF6)
C_CARD_BORDER = RGBColor(0xCF, 0xE6, 0xE6)
C_RISK_HIGH = RGBColor(0xF8, 0x71, 0xA0)  # Rose (chart: pérdidas)
C_RISK_MED = RGBColor(0xFF, 0xD6, 0x1F)  # Yellow

# Colores de estado para el pipeline — paleta "no secuencial" de charts.
# evaluated/backlog comparten color: dashboard.md también los trata igual (⚪).
C_STATUS = {
    "evaluated": RGBColor(0xFF, 0x82, 0x00),  # Orange
    "backlog": RGBColor(0xFF, 0x82, 0x00),  # Orange
    "approved": RGBColor(0x01, 0x79, 0xFF),  # Cobalt
    "executing": RGBColor(0x00, 0xA8, 0xB8),  # Worldpanel Blue
    "implemented": RGBColor(0x2B, 0xEF, 0xB9),  # Mint
    "on_hold": RGBColor(0xFF, 0xD6, 0x1F),  # Yellow
    "handed_off": RGBColor(0x00, 0x4A, 0x52),  # Deep Teal
    "rejected": RGBColor(0xF8, 0x71, 0xA0),  # Rose
}

# Layout — slide dimensions
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
HEADER_H = Inches(0.78)
ROW_H = Inches(1.15)

# Slide 1: metrics + col headers above rows
COL_HEADER_Y_S1 = Inches(2.28)
ROW_START_Y_S1 = Inches(2.50)

# Slide 2+: rows start right after header
COL_HEADER_Y_SN = Inches(0.90)
ROW_START_Y_SN = Inches(1.12)

# Column positions
COL_NAME_X = Inches(0.65)
COL_NAME_W = Inches(3.15)
COL_BADGE_X = Inches(3.85)
COL_BADGE_W = Inches(0.90)
COL_NOTES_X = Inches(4.90)
COL_NOTES_W = Inches(4.20)
COL_SEP_X = Inches(9.18)
COL_RISK_X = Inches(9.30)
COL_RISK_W = Inches(1.95)
COL_DATE_X = Inches(11.35)
COL_DATE_W = Inches(1.40)

ROWS_PER_SLIDE = 4


@dataclass
class ProjectStatus:
    project_id: str
    name: str
    progress_percent: int | None
    progress_at: str | None
    general_note: str
    next_step: str
    blocker: str
    risk: str


def fetch_all_projects(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT project_id, name, status, description, closed_at, hours_saved_per_month FROM projects"
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_executing_projects(conn) -> list[ProjectStatus]:
    sql = """
    WITH latest_progress AS (
        SELECT project_id, progress_percent, created_at,
               ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at DESC, note_id DESC) AS rn
        FROM project_notes
        WHERE progress_percent IS NOT NULL
    ),
    latest_notes AS (
        SELECT project_id, note_type, note_text, created_at,
               ROW_NUMBER() OVER (PARTITION BY project_id, note_type ORDER BY created_at DESC, note_id DESC) AS rn
        FROM project_notes
    )
    SELECT
        p.project_id,
        p.name,
        lp.progress_percent,
        lp.created_at AS progress_at,
        COALESCE(gn.note_text, '') AS general_note,
        COALESCE(pn.note_text, '') AS next_step,
        COALESCE(bn.note_text, '') AS blocker,
        COALESCE(rk.note_text, '') AS risk
    FROM projects p
    LEFT JOIN latest_progress lp ON lp.project_id = p.project_id AND lp.rn = 1
    LEFT JOIN latest_notes gn ON gn.project_id = p.project_id AND gn.note_type = 'general' AND gn.rn = 1
    LEFT JOIN latest_notes pn ON pn.project_id = p.project_id AND pn.note_type = 'proximo_paso' AND pn.rn = 1
    LEFT JOIN latest_notes bn ON bn.project_id = p.project_id AND bn.note_type = 'bloqueador' AND bn.rn = 1
    LEFT JOIN latest_notes rk ON rk.project_id = p.project_id AND rk.note_type = 'riesgo' AND rk.rn = 1
    WHERE lower(COALESCE(p.status, '')) = 'executing'
    ORDER BY COALESCE(lp.created_at, p.updated_at, p.created_date) DESC, p.project_id
    """
    rows = conn.execute(sql).fetchall()
    return [ProjectStatus(**dict(row)) for row in rows]


def average_progress(projects: Iterable[ProjectStatus]) -> int:
    values = [p.progress_percent for p in projects if isinstance(p.progress_percent, int)]
    return round(sum(values) / len(values)) if values else 0


def latest_update(projects: Iterable[ProjectStatus]) -> str:
    values = [datetime.fromisoformat(p.progress_at) for p in projects if p.progress_at]
    return max(values).strftime("%d %b %Y") if values else "Sin actualizacion"


def progress_color(progress: int | None) -> RGBColor:
    if progress is None:
        return C_TEXT_LIGHT
    if progress >= 70:
        return RGBColor(0x2B, 0xEF, 0xB9)  # Mint
    if progress >= 50:
        return RGBColor(0xFF, 0xD6, 0x1F)  # Yellow
    return RGBColor(0xF8, 0x71, 0xA0)  # Rose


def risk_color(risk: str) -> RGBColor:
    r = (risk or "").lower()
    if any(w in r for w in ("critico", "crítico", "alto")):
        return C_RISK_HIGH
    if r not in ("", "ninguno", "ninguna", "n/a"):
        return C_RISK_MED
    return C_TEXT_LIGHT


def blocker_color(blocker: str) -> RGBColor:
    b = (blocker or "").strip().lower()
    return C_RISK_HIGH if b not in ("", "ninguno", "ninguna") else C_TEXT_LIGHT


def trim_text(value: str, limit: int) -> str:
    clean = " ".join((value or "").split())
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def add_textbox(slide, left, top, width, height, text, font_size, *, bold=False, color=None, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    run = p.runs[0]
    run.font.size = Pt(font_size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    return box


def add_metric_card(slide, left, title, value, subtitle):
    card = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, Inches(1.05), Inches(2.2), Inches(1.25))
    card.fill.solid()
    card.fill.fore_color.rgb = C_CARD_BG
    card.line.color.rgb = C_CARD_BORDER
    add_textbox(slide, left + Inches(0.12), Inches(1.13), Inches(1.95), Inches(0.22), title, 10, color=C_TEXT_BLUE)
    add_textbox(
        slide, left + Inches(0.12), Inches(1.35), Inches(1.95), Inches(0.55), value, 20, bold=True, color=C_TEXT_DARK
    )
    add_textbox(slide, left + Inches(0.12), Inches(1.93), Inches(1.95), Inches(0.2), subtitle, 9, color=C_TEXT_LIGHT)


def _draw_header(slide, prs, slide_num: int, total_slides: int, title: str, subtitle: str) -> None:
    header = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, prs.slide_width, HEADER_H)
    header.fill.solid()
    header.fill.fore_color.rgb = C_HEADER_BG
    header.line.color.rgb = C_HEADER_BG

    add_textbox(slide, Inches(0.45), Inches(0.18), Inches(9.0), Inches(0.3), title, 24, bold=True, color=C_HEADER_TEXT)
    add_textbox(slide, Inches(0.45), Inches(0.5), Inches(6.0), Inches(0.18), subtitle, 9, color=C_HEADER_SUB)

    if total_slides > 1:
        add_textbox(
            slide,
            Inches(10.3),
            Inches(0.28),
            Inches(1.5),
            Inches(0.18),
            f"{slide_num} / {total_slides}",
            10,
            color=C_HEADER_CUT,
            align=PP_ALIGN.RIGHT,
        )

    if LOGO_PATH.exists():
        try:
            slide.shapes.add_picture(str(LOGO_PATH), Inches(12.0), Inches(0.09), height=Inches(0.58))
        except Exception:
            pass


def _draw_column_headers(slide, col_header_y) -> None:
    cols = [
        (COL_NAME_X, COL_NAME_W, "Proyecto"),
        (COL_BADGE_X, COL_BADGE_W, "Avance"),
        (COL_NOTES_X, COL_NOTES_W, "Nota / Proximo paso"),
        (COL_RISK_X, COL_RISK_W, "Bloqueo & Riesgo"),
        (COL_DATE_X, COL_DATE_W, "Ultima act."),
    ]
    for x, w, label in cols:
        add_textbox(slide, x, col_header_y, w, Inches(0.18), label, 8, bold=True, color=C_TEXT_LIGHT)


def _draw_project_row(slide, project: ProjectStatus, row_index: int, row_start_y) -> None:
    top = row_start_y + row_index * ROW_H
    row_bg = C_ROW_ODD if row_index % 2 == 0 else C_ROW_EVEN
    row = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.45), top, Inches(12.4), ROW_H - Inches(0.05)
    )
    row.fill.solid()
    row.fill.fore_color.rgb = row_bg
    row.line.color.rgb = C_ROW_BORDER

    # Project name
    add_textbox(
        slide, COL_NAME_X, top + Inches(0.08), COL_NAME_W, Inches(0.30), project.name, 14, bold=True, color=C_TEXT_DARK
    )
    # Project ID — near bottom of card to avoid overlapping name
    add_textbox(
        slide,
        COL_NAME_X,
        top + ROW_H - Inches(0.35),
        COL_NAME_W,
        Inches(0.22),
        project.project_id,
        9,
        color=C_TEXT_LIGHT,
    )

    # Progress badge
    progress = project.progress_percent or 0
    badge = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, COL_BADGE_X, top + Inches(0.14), COL_BADGE_W, Inches(0.36)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = progress_color(project.progress_percent)
    badge.line.color.rgb = progress_color(project.progress_percent)
    add_textbox(
        slide,
        COL_BADGE_X,
        top + Inches(0.18),
        COL_BADGE_W,
        Inches(0.22),
        f"{progress}%",
        16,
        bold=True,
        color=C_TEXT_DARK,
        align=PP_ALIGN.CENTER,
    )

    # Vertical separator between notes and risk
    sep = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, COL_SEP_X, top + Inches(0.08), Inches(0.02), ROW_H - Inches(0.20)
    )
    sep.fill.solid()
    sep.fill.fore_color.rgb = C_SEPARATOR
    sep.line.color.rgb = C_SEPARATOR

    # Notes column
    add_textbox(
        slide, COL_NOTES_X, top + Inches(0.05), COL_NOTES_W, Inches(0.14), "NOTA", 7, bold=True, color=C_TEXT_LIGHT
    )
    add_textbox(
        slide,
        COL_NOTES_X,
        top + Inches(0.19),
        COL_NOTES_W,
        Inches(0.32),
        trim_text(project.general_note, 160),
        9,
        color=C_TEXT_MID,
    )
    add_textbox(
        slide,
        COL_NOTES_X,
        top + Inches(0.55),
        COL_NOTES_W,
        Inches(0.14),
        "PROX. PASO",
        7,
        bold=True,
        color=C_TEXT_LIGHT,
    )
    add_textbox(
        slide,
        COL_NOTES_X,
        top + Inches(0.69),
        COL_NOTES_W,
        Inches(0.30),
        trim_text(project.next_step or "Sin definir", 100),
        9,
        color=C_TEXT_BLUE,
    )

    # Risk / blocker column
    add_textbox(
        slide, COL_RISK_X, top + Inches(0.05), COL_RISK_W, Inches(0.14), "BLOQUEADOR", 7, bold=True, color=C_TEXT_LIGHT
    )
    add_textbox(
        slide,
        COL_RISK_X,
        top + Inches(0.19),
        COL_RISK_W,
        Inches(0.24),
        trim_text(project.blocker or "Ninguno", 45),
        9,
        color=blocker_color(project.blocker or ""),
    )
    add_textbox(
        slide, COL_RISK_X, top + Inches(0.53), COL_RISK_W, Inches(0.14), "RIESGO", 7, bold=True, color=C_TEXT_LIGHT
    )
    add_textbox(
        slide,
        COL_RISK_X,
        top + Inches(0.67),
        COL_RISK_W,
        Inches(0.24),
        trim_text(project.risk or "Ninguno", 50),
        9,
        color=risk_color(project.risk or ""),
    )

    # Date
    date_text = datetime.fromisoformat(project.progress_at).strftime("%d %b %Y") if project.progress_at else "Sin fecha"
    add_textbox(
        slide,
        COL_DATE_X,
        top + Inches(0.24),
        COL_DATE_W,
        Inches(0.24),
        date_text,
        10,
        bold=True,
        color=C_TEXT_DARK,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        COL_DATE_X,
        top + Inches(0.50),
        COL_DATE_W,
        Inches(0.18),
        "Ultima act.",
        8,
        color=C_TEXT_LIGHT,
        align=PP_ALIGN.CENTER,
    )


def _draw_footer(slide, generated_at: str) -> None:
    add_textbox(
        slide,
        Inches(0.45),
        Inches(7.08),
        Inches(8.0),
        Inches(0.18),
        "Nota: el porcentaje corresponde al ultimo progreso capturado por proyecto.",
        8,
        color=C_TEXT_LIGHT,
    )
    add_textbox(
        slide,
        Inches(9.0),
        Inches(7.08),
        Inches(4.0),
        Inches(0.18),
        f"Corte: {generated_at}",
        8,
        color=C_TEXT_LIGHT,
        align=PP_ALIGN.RIGHT,
    )


def _draw_pipeline(slide, status_counts: dict[str, int], top) -> None:
    total = sum(status_counts.values()) or 1
    add_textbox(
        slide,
        Inches(0.45),
        top,
        Inches(6.0),
        Inches(0.2),
        f"Pipeline del portafolio · {sum(status_counts.values())} proyectos",
        9,
        bold=True,
        color=C_TEXT_LIGHT,
    )

    bar_top = top + Inches(0.3)
    bar_left = Inches(0.45)
    bar_width_total = Inches(12.4)
    x = int(bar_left)
    for status in PIPELINE_ORDER:
        count = status_counts[status]
        if count == 0:
            continue
        seg_w = int(bar_width_total * (count / total))
        seg = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Emu(x), bar_top, Emu(seg_w), Inches(0.3))
        seg.fill.solid()
        seg.fill.fore_color.rgb = C_STATUS[status]
        seg.line.color.rgb = C_STATUS[status]
        x += seg_w

    legend_top = bar_top + Inches(0.45)
    col_w = Inches(1.55)
    for i, status in enumerate(PIPELINE_ORDER):
        cx = Emu(int(bar_left) + int(col_w) * i)
        dot = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL, cx, legend_top + Inches(0.03), Inches(0.12), Inches(0.12)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = C_STATUS[status]
        dot.line.color.rgb = C_STATUS[status]
        add_textbox(
            slide,
            cx + Inches(0.18),
            legend_top,
            Inches(1.35),
            Inches(0.2),
            f"{STATUS_LABELS_ES[status]} {status_counts[status]}",
            8,
            color=C_TEXT_MID,
        )


def _draw_speaker_notes(slide, summary: PortfolioSummary, notes_by_id: dict, all_projects: list[dict]) -> None:
    lines = [
        "Supuesto: 40 horas/semana = 1 persona a tiempo completo. La unidad "
        "(semanas/meses/años) se elige según la magnitud del total.",
        f"Principal contribuyente: {summary.top_contributor}.",
        "",
        "Proyectos, por estado:",
    ]
    by_status: dict[str, list[str]] = {}
    for p in all_projects:
        que_es, estado_frase = resolve_project_note(p, notes_by_id)
        by_status.setdefault(p["status"], []).append(f"- {p['name']}: {que_es} {estado_frase}")

    for status in PIPELINE_ORDER:
        rows = by_status.get(status)
        if not rows:
            continue
        lines.append(f"\n{STATUS_LABELS_ES[status]}:")
        lines.extend(rows)

    slide.notes_slide.notes_text_frame.text = "\n".join(lines)


def build_summary_slide(
    prs: Presentation,
    summary: PortfolioSummary,
    notes_by_id: dict,
    all_projects: list[dict],
    generated_at: str,
    slide_num: int,
    total_slides: int,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = C_BODY_BG

    _draw_header(
        slide,
        prs,
        slide_num,
        total_slides,
        title="Resumen ejecutivo · Portafolio Data & Automatización",
        subtitle=f"Corte: {generated_at} · Fuente: Supabase (projects)",
    )

    cards = [
        ("Horas ahorradas / mes", f"{summary.hours_saved_closed:,.0f} h", "proyectos cerrados"),
        ("Equivale a", summary.fte_equivalent, "1 persona, tiempo completo"),
        ("Proyectos cerrados", str(summary.closed_count), "implementados + entregados"),
        ("En ejecución", str(summary.executing_count), "activos hoy"),
    ]
    for i, (title, value, subtitle) in enumerate(cards):
        add_metric_card(slide, Inches(0.45 + i * 2.45), title, value, subtitle)

    add_textbox(
        slide,
        Inches(0.45),
        Inches(2.05),
        Inches(12.4),
        Inches(0.5),
        f"Cada mes, el equipo ahorra el equivalente a {summary.fte_equivalent} de trabajo de una "
        f"persona a tiempo completo — con base en las {summary.closed_count} automatizaciones ya cerradas.",
        12,
        color=C_TEXT_DARK,
    )

    _draw_pipeline(slide, summary.status_counts, Inches(2.75))
    _draw_speaker_notes(slide, summary, notes_by_id, all_projects)
    _draw_footer(slide, generated_at)


def build_slide(
    prs: Presentation,
    chunk: list[ProjectStatus],
    slide_num: int,
    total_slides: int,
    generated_at: str,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = C_BODY_BG

    _draw_header(
        slide,
        prs,
        slide_num,
        total_slides,
        title="Detalle · Proyectos en ejecución",
        subtitle="Fuente: Supabase (project_notes)",
    )

    _draw_column_headers(slide, COL_HEADER_Y_SN)

    for i, project in enumerate(chunk):
        _draw_project_row(slide, project, i, ROW_START_Y_SN)

    _draw_footer(slide, generated_at)


def _build_prs(
    all_projects: list[dict],
    executing: list[ProjectStatus],
    summary: PortfolioSummary,
    notes_by_id: dict,
) -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    chunks = [executing[i : i + ROWS_PER_SLIDE] for i in range(0, len(executing), ROWS_PER_SLIDE)]
    total_slides = 1 + len(chunks)

    build_summary_slide(prs, summary, notes_by_id, all_projects, generated_at, 1, total_slides)
    for n, chunk in enumerate(chunks, start=2):
        build_slide(prs, chunk, n, total_slides, generated_at)
    return prs


def build_presentation(
    all_projects: list[dict],
    executing: list[ProjectStatus],
    summary: PortfolioSummary,
    notes_by_id: dict,
    output_path: Path,
) -> Path:
    prs = _build_prs(all_projects, executing, summary, notes_by_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path


def build_presentation_bytes(
    all_projects: list[dict], executing: list[ProjectStatus], summary: PortfolioSummary, notes_by_id: dict
) -> bytes:
    buf = BytesIO()
    _build_prs(all_projects, executing, summary, notes_by_id).save(buf)
    return buf.getvalue()


def build_detail_only_presentation_bytes(executing: list[ProjectStatus]) -> bytes:
    """Genera solo las diapositivas de detalle (sin portada de resumen).

    Preserva el comportamiento previo a la portada de resumen para el boton
    "Generar presentacion" de Seguimiento Operativo, que sigue trabajando con
    su propia consulta y no con el flujo de portafolio completo.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    chunks = [executing[i : i + ROWS_PER_SLIDE] for i in range(0, len(executing), ROWS_PER_SLIDE)]
    total_slides = len(chunks)

    for n, chunk in enumerate(chunks, start=1):
        build_slide(prs, chunk, n, total_slides, generated_at)

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()


def portfolio_summary_to_json(summary: PortfolioSummary) -> str:
    return json.dumps(
        {
            "hours_saved_closed": summary.hours_saved_closed,
            "fte_equivalent": summary.fte_equivalent,
            "closed_count": summary.closed_count,
            "executing_count": summary.executing_count,
        }
    )


def parse_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Genera el deck ejecutivo (resumen + detalle operativo).")
    parser.add_argument("--notes", default=None, help="Ruta al JSON de notas por proyecto (opcional).")
    parser.add_argument("--out", default=None, help="Ruta de salida del .pptx.")
    return parser.parse_args(argv)


def main() -> None:
    from infra.db.adapter import get_connection

    if not os.environ.get("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL no está seteada. Este script requiere Supabase — "
            "seteala en la sesión antes de correr (mismo requisito que /sync-bitacora)."
        )

    args = parse_args()

    conn = get_connection()
    try:
        all_projects = fetch_all_projects(conn)
        executing = fetch_executing_projects(conn)
    finally:
        conn.close()

    if not all_projects:
        raise SystemExit("No hay proyectos en Supabase.")

    from domain.services.executive_summary_service import compute_portfolio_summary, load_project_notes

    summary = compute_portfolio_summary(all_projects)
    notes_by_id = load_project_notes(args.notes)
    out_path = Path(args.out) if args.out else DEFAULT_OUTPUT_PATH

    path = build_presentation(all_projects, executing, summary, notes_by_id, out_path)
    print(path)
    print(portfolio_summary_to_json(summary))


if __name__ == "__main__":
    main()
