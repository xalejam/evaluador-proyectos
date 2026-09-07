# Presentación ejecutiva del portafolio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un comando manual en el vault de Obsidian (`/presentacion-ejecutiva`) arma un `.pptx` de 2 slides — portada con impacto agregado del portafolio + pipeline, y detalle operativo de proyectos en ejecución — extendiendo el generador que ya existe en el repo evaluador, migrado de SQLite local a Supabase y reskineado a marca Worldpanel.

**Architecture:** Claude, desde el vault, consulta Supabase (solo lectura, vía MCP) y el propio vault para condensar una frase de "qué es" + "estado" por proyecto, y escribe un JSON chico. Ese JSON se pasa como argumento a `scripts/generate_execution_status_presentation.py` (repo evaluador), que ahora lee Supabase directo (antes SQLite local), calcula los agregados de portafolio con una fórmula determinística (nunca la redacta un LLM), y arma el `.pptx` con python-pptx.

**Tech Stack:** Python 3.11+, python-pptx (ya en el repo evaluador), psycopg2 vía `infra/db/adapter.py` (ya existe), pytest. Sin dependencias nuevas. El repo de Obsidian no ejecuta Python directamente — solo dispara el script del otro repo, igual que `/sync-bitacora`.

**Spec:** [docs/superpowers/specs/2026-09-04-presentacion-ejecutiva-design.md](../specs/2026-09-04-presentacion-ejecutiva-design.md)

## Global Constraints

- Solo lectura sobre Supabase — ningún paso de este flujo escribe en la base de datos.
- El script requiere `DATABASE_URL` seteada — a diferencia del resto del repo evaluador, **no** cae de vuelta a SQLite local si falta: ese fallback silencioso es justo el bug que se está corrigiendo (ver spec, sección "Prerrequisito confirmado").
- `effort_hours` es una tabla muerta (confirmado en spec y en `docs/superpowers/plans/2026-08-14-bitacora-supabase-sync.md:19` del repo evaluador) — no se lee, no se migra, no se menciona en código nuevo.
- El equivalente en tiempo-persona (semanas/meses/años) lo calcula una función pura determinística — nunca lo redacta Claude ni ningún LLM en tiempo de ejecución.
- Colores: paleta oficial Worldpanel únicamente (hex exactos abajo) — nunca inventar tonos "parecidos" (regla del skill `worldpanel-brand`).
- El `.pptx` y el JSON de notas nunca se comitean — ambos en `presentaciones/` (vault), que va a `.gitignore`.
- Nada se dispara solo — comando manual, mismo patrón que `/revisar` y `/sync-bitacora`.

**Paleta Worldpanel usada en este plan** (fuente: skill `anthropic-skills:worldpanel-brand` y su `references/brand-guide.md`):

| Uso | Nombre | Hex |
|---|---|---|
| Fondo de header, texto sobre blanco | Deep Teal | `#004A52` |
| Acento primario / texto de énfasis | Worldpanel Blue | `#00A8B8` |
| Acento sobre fondo oscuro | Aqua | `#2EEFEE` |
| Positivo (avance alto, chart) | Mint | `#2BEFB9` |
| Caución (avance medio, on_hold) | Yellow | `#FFD61F` |
| Negativo (riesgo alto, rejected) | Rose | `#F871A0` |
| Chart no-secuencial | Cobalt | `#0179FF` |
| Chart no-secuencial | Orange | `#FF8200` |

---

## Mapa de archivos

| Repo | Archivo | Acción | Responsabilidad |
|---|---|---|---|
| Evaluador | `domain/services/executive_summary_service.py` | Crear | Funciones puras: fórmula de tiempo-persona, agregados de portafolio, resolución de notas por proyecto |
| Evaluador | `tests/unit/test_executive_summary_service.py` | Crear | Tests de todo lo anterior |
| Evaluador | `scripts/generate_execution_status_presentation.py` | Modificar | Migrar a Supabase, reskin, portada nueva, CLI |
| Evaluador | `tests/unit/test_generate_execution_status_presentation.py` | Crear | Tests de fetch (SQL portable) y smoke test de generación |
| Obsidian (este repo) | `.claude/commands/presentacion-ejecutiva.md` | Crear | Comando que junta datos y llama al script del evaluador |
| Obsidian (este repo) | `.gitignore` | Modificar | Ignorar `presentaciones/` |
| Obsidian (este repo) | `AGENTS.md` / `CLAUDE.md` | Modificar | Agregar el comando a la lista |

Rutas absolutas usadas en los pasos de abajo:
- Repo evaluador: `C:\Users\xiomara.monroy\OneDrive - Numerator International\Documents\Project Managment\ReportesAdhoc\EvaluadorDeProyectos\Repositorio Evaluador`
- Repo Obsidian: `C:\Users\xiomara.monroy\OneDrive - Numerator International\Documents\Project Managment\Agentes-IA\Obsidian`

Todos los comandos `pytest`/`python` de las Tasks 1-5 se corren con el cwd en el repo evaluador, usando su entorno virtual: `.venv\Scripts\python`.

---

## Task 1: Servicio de dominio — fórmula de tiempo-persona y agregados de portafolio

**Files:**
- Create: `domain/services/executive_summary_service.py`
- Create: `tests/unit/test_executive_summary_service.py`

**Interfaces:**
- Produces: `ALL_STATUSES: list[str]`, `CLOSED_STATUSES: set[str]`, `STATUS_LABELS_ES: dict[str, str]`, `format_fte_equivalent(total_hours: float) -> str`, `PortfolioSummary` (dataclass: `hours_saved_closed: float`, `closed_count: int`, `executing_count: int`, `fte_equivalent: str`, `top_contributor: str`, `status_counts: dict[str, int]`), `compute_portfolio_summary(projects: list[dict]) -> PortfolioSummary`, `load_project_notes(path: str | None) -> dict[str, dict]`, `resolve_project_note(project: dict, notes_by_id: dict[str, dict]) -> tuple[str, str]`.

- [ ] **Step 1: Escribir los tests de `format_fte_equivalent`**

Crear `tests/unit/test_executive_summary_service.py`. Importa solo lo que
existe en este punto — los imports de `PortfolioSummary`,
`compute_portfolio_summary`, `load_project_notes` y `resolve_project_note`
se agregan en los Steps 5 y 9, cuando esas funciones ya existen (importar
nombres que todavía no existen rompe la colección de pytest con
`ImportError`, no falla test por test):

```python
from domain.services.executive_summary_service import format_fte_equivalent


def test_fte_under_8_weeks_shows_weeks_and_hours():
    assert format_fte_equivalent(100) == "2 semanas y 20 h"


def test_fte_exact_weeks_omits_hours():
    assert format_fte_equivalent(40) == "1 semana"


def test_fte_plural_weeks():
    assert format_fte_equivalent(80) == "2 semanas"


def test_fte_between_8_and_52_weeks_shows_months():
    assert format_fte_equivalent(2000) == "11.5 meses"


def test_fte_52_weeks_or_more_shows_years_and_months():
    assert format_fte_equivalent(5661.54) == "2 años y 9 meses"


def test_fte_exact_years_omits_months():
    assert format_fte_equivalent(40 * 52 * 3) == "3 años"


def test_fte_singular_year():
    assert format_fte_equivalent(40 * 52) == "1 año"
```

- [ ] **Step 2: Correr los tests — deben fallar**

```bash
cd "C:\Users\xiomara.monroy\OneDrive - Numerator International\Documents\Project Managment\ReportesAdhoc\EvaluadorDeProyectos\Repositorio Evaluador"
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: FAIL — `domain.services.executive_summary_service` no existe.

- [ ] **Step 3: Crear `domain/services/executive_summary_service.py` con la fórmula**

```python
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
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: 7 PASSED.

- [ ] **Step 5: Agregar tests de `compute_portfolio_summary`**

Añadir a `tests/unit/test_executive_summary_service.py` — primero, una
segunda línea de import junto a la del Step 1 (no la reemplaces):

```python
from domain.services.executive_summary_service import PortfolioSummary, compute_portfolio_summary
```

Y las funciones de test:

```python
def _project(project_id, name, status, hours=0.0):
    return {"project_id": project_id, "name": name, "status": status, "hours_saved_per_month": hours}


def test_compute_portfolio_summary_counts_and_sums_closed_only():
    projects = [
        _project("A", "Proyecto A", "implemented", hours=100),
        _project("B", "Proyecto B", "handed_off", hours=5000),
        _project("C", "Proyecto C", "executing", hours=9999),  # no cuenta en el ahorro
        _project("D", "Proyecto D", "approved"),
    ]
    summary = compute_portfolio_summary(projects)
    assert summary.hours_saved_closed == 5100
    assert summary.closed_count == 2
    assert summary.executing_count == 1
    assert summary.fte_equivalent == format_fte_equivalent(5100)


def test_compute_portfolio_summary_top_contributor():
    projects = [
        _project("A", "Proyecto chico", "implemented", hours=10),
        _project("B", "Proyecto grande", "handed_off", hours=5000),
    ]
    summary = compute_portfolio_summary(projects)
    assert summary.top_contributor == "Proyecto grande (5,000 h/mes)"


def test_compute_portfolio_summary_status_counts_include_zeros():
    projects = [_project("A", "Proyecto A", "implemented", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.status_counts == {
        "evaluated": 0, "backlog": 0, "approved": 0, "executing": 0,
        "implemented": 1, "on_hold": 0, "handed_off": 0, "rejected": 0,
    }


def test_compute_portfolio_summary_no_closed_projects():
    projects = [_project("A", "Proyecto A", "executing", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.hours_saved_closed == 0
    assert summary.top_contributor == "N/D"
    assert summary.fte_equivalent == format_fte_equivalent(0)


def test_compute_portfolio_summary_ignores_unknown_status():
    # defensivo: un status fuera del enum no debe romper el conteo
    projects = [_project("A", "Proyecto A", "algo_nuevo", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.closed_count == 0
    assert summary.executing_count == 0
```

- [ ] **Step 6: Correr — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: FAIL — `PortfolioSummary`/`compute_portfolio_summary` no existen.

- [ ] **Step 7: Agregar `PortfolioSummary` y `compute_portfolio_summary` al final del archivo**

```python
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
```

- [ ] **Step 8: Correr — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: 12 PASSED (los de `load_project_notes`/`resolve_project_note` siguen sin existir todavía).

- [ ] **Step 9: Agregar tests de `load_project_notes` y `resolve_project_note`**

Añadir a `tests/unit/test_executive_summary_service.py` — de nuevo, una
línea de import más (sin tocar las dos anteriores) y, al principio del
archivo (junto al resto de imports), `import json`:

```python
import json  # agregar junto a los imports del principio del archivo

from domain.services.executive_summary_service import load_project_notes, resolve_project_note
```

Y las funciones de test:

```python
def test_load_project_notes_returns_empty_dict_when_path_is_none():
    assert load_project_notes(None) == {}


def test_load_project_notes_returns_empty_dict_when_file_missing(tmp_path):
    assert load_project_notes(str(tmp_path / "no-existe.json")) == {}


def test_load_project_notes_indexes_by_project_id(tmp_path):
    path = tmp_path / "notas.json"
    path.write_text(
        json.dumps({
            "generated_at": "2026-09-04",
            "projects": [
                {"project_id": "MX-DDD-0005", "que_es": "Automatiza Order Forms.", "estado_frase": "Implementado."},
            ],
        }),
        encoding="utf-8",
    )
    notes = load_project_notes(str(path))
    assert notes["MX-DDD-0005"]["que_es"] == "Automatiza Order Forms."


def test_resolve_project_note_uses_notes_when_present():
    project = {"project_id": "MX-DDD-0005", "name": "Order Forms", "status": "implemented"}
    notes_by_id = {"MX-DDD-0005": {"que_es": "Automatiza Order Forms.", "estado_frase": "Implementado."}}
    que_es, estado_frase = resolve_project_note(project, notes_by_id)
    assert que_es == "Automatiza Order Forms."
    assert estado_frase == "Implementado."


def test_resolve_project_note_falls_back_when_missing():
    project = {"project_id": "XX-DDD-0099", "name": "Proyecto sin notas", "status": "approved"}
    que_es, estado_frase = resolve_project_note(project, {})
    assert que_es == "Proyecto sin notas — sin resumen disponible."
    assert estado_frase == "Estado: Aprobado."
```

- [ ] **Step 10: Correr — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: FAIL — `load_project_notes`/`resolve_project_note` no existen.

- [ ] **Step 11: Agregar `load_project_notes` y `resolve_project_note` al final del archivo**

```python
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
```

- [ ] **Step 12: Correr — deben pasar todos**

```bash
.venv\Scripts\python -m pytest tests/unit/test_executive_summary_service.py -v
```

Esperado: 17 PASSED.

- [ ] **Step 13: Commit**

```bash
git add domain/services/executive_summary_service.py tests/unit/test_executive_summary_service.py
git commit -m "feat: agregar servicio de agregados para el resumen ejecutivo"
```

---

## Task 2: Migrar las consultas del script a Supabase (SQL portable)

**Files:**
- Modify: `scripts/generate_execution_status_presentation.py:82-134` (reemplaza `fetch_executing_projects`, agrega `fetch_all_projects`)
- Create: `tests/unit/test_generate_execution_status_presentation.py`

**Interfaces:**
- Consumes: `infra.db.adapter.get_connection` (ya existe: `get_connection(local_path: str = "project_viability.db")`, devuelve un adapter con `.execute(sql, params)`, `.commit()`, `.close()`, filas tipo dict).
- Produces: `fetch_all_projects(conn) -> list[dict]` (claves: `project_id, name, status, description, closed_at, hours_saved_per_month`); `fetch_executing_projects(conn) -> list[ProjectStatus]` (misma dataclass `ProjectStatus` que ya existe en el archivo).

Las dos consultas usan `ROW_NUMBER() OVER (PARTITION BY ...)` en vez del `DISTINCT ON` propio de Postgres — es la misma sintaxis que ya usaba la versión SQLite, y **funciona igual en SQLite (3.25+) y en Postgres**, así que se puede testear con una SQLite temporal aunque en producción corra contra Supabase.

- [ ] **Step 1: Escribir los tests de las nuevas funciones de fetch**

Crear `tests/unit/test_generate_execution_status_presentation.py`:

```python
import sqlite3

from infra.db.adapter import get_connection
from scripts.generate_execution_status_presentation import (
    ProjectStatus,
    fetch_all_projects,
    fetch_executing_projects,
)

SCHEMA = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,
    description TEXT,
    closed_at TEXT,
    updated_at TEXT,
    created_date TEXT,
    hours_saved_per_month REAL
);
CREATE TABLE project_notes (
    note_id INTEGER PRIMARY KEY,
    project_id TEXT,
    note_type TEXT,
    note_text TEXT,
    created_at TEXT,
    progress_percent INTEGER
);
"""


def _seed(conn, projects, notes):
    conn.executescript(SCHEMA)
    for p in projects:
        conn.execute(
            "INSERT INTO projects (project_id, name, status, description, closed_at, updated_at, created_date, hours_saved_per_month) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            p,
        )
    for n in notes:
        conn.execute(
            "INSERT INTO project_notes (project_id, note_type, note_text, created_at, progress_percent) VALUES (?, ?, ?, ?, ?)",
            n,
        )
    conn.commit()


def test_fetch_all_projects_returns_every_row(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Proyecto A", "implemented", "desc A", "2026-06-01", "2026-06-01", "2026-01-01", 10.0),
            ("B", "Proyecto B", "executing", "desc B", None, "2026-06-01", "2026-01-01", 0.0),
        ],
        [],
    )
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_all_projects(conn)
    conn.close()

    assert len(rows) == 2
    assert rows[0]["project_id"] == "A"
    assert rows[0]["hours_saved_per_month"] == 10.0


def test_fetch_executing_projects_only_returns_executing_with_latest_note_and_progress(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Proyecto A", "executing", "desc A", None, "2026-06-01", "2026-01-01", 0.0),
            ("B", "Proyecto B", "implemented", "desc B", "2026-06-01", "2026-06-01", "2026-01-01", 10.0),
        ],
        [
            ("A", "general", "nota vieja", "2026-08-01 00:00:00", 40),
            ("A", "general", "nota nueva", "2026-08-15 00:00:00", 70),
            ("A", "bloqueador", "bloqueo actual", "2026-08-10 00:00:00", None),
        ],
    )
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_executing_projects(conn)
    conn.close()

    assert len(rows) == 1
    project = rows[0]
    assert isinstance(project, ProjectStatus)
    assert project.project_id == "A"
    assert project.progress_percent == 70
    assert project.general_note == "nota nueva"
    assert project.blocker == "bloqueo actual"
    assert project.risk == ""


def test_fetch_executing_projects_returns_empty_list_when_none_executing(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(raw, [("A", "Proyecto A", "implemented", "desc A", "2026-06-01", "2026-06-01", "2026-01-01", 10.0)], [])
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_executing_projects(conn)
    conn.close()

    assert rows == []
```

- [ ] **Step 2: Correr los tests — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_generate_execution_status_presentation.py -v
```

Esperado: FAIL — `fetch_all_projects` no existe todavía / `fetch_executing_projects` tiene otra firma.

- [ ] **Step 3: Reemplazar `fetch_executing_projects` (líneas 82-134) y agregar `fetch_all_projects`**

En `scripts/generate_execution_status_presentation.py`, reemplazar la función completa (desde `def fetch_executing_projects(db_path: Path) -> list[ProjectStatus]:` hasta el `return [ProjectStatus(**dict(row)) for row in rows]` que la cierra) por:

```python
def fetch_all_projects(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT project_id, name, status, description, closed_at, hours_saved_per_month FROM projects"
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_executing_projects(conn) -> list[ProjectStatus]:
    sql = """
    WITH latest_progress AS (
        SELECT project_id, progress_percent, created_at,
               ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at DESC) AS rn
        FROM project_notes
        WHERE progress_percent IS NOT NULL
    ),
    latest_notes AS (
        SELECT project_id, note_type, note_text, created_at,
               ROW_NUMBER() OVER (PARTITION BY project_id, note_type ORDER BY created_at DESC) AS rn
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
```

No cambia la dataclass `ProjectStatus` (línea 70-79) ni `average_progress`/`latest_update`/`progress_color`/`risk_color`/`blocker_color`/`trim_text` — siguen igual.

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_generate_execution_status_presentation.py -v
```

Esperado: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_execution_status_presentation.py tests/unit/test_generate_execution_status_presentation.py
git commit -m "feat: migrar fetch de proyectos a infra.db.adapter (Supabase-ready)"
```

---

## Task 3: Reskin a paleta oficial Worldpanel

**Files:**
- Modify: `scripts/generate_execution_status_presentation.py:16-38` (constantes), `:147-168` (`progress_color`/`risk_color`/`blocker_color`)

**Interfaces:**
- Consumes: nada nuevo.
- Produces: mismos nombres de constante que ya existen (`C_HEADER_BG`, `C_TEXT_DARK`, etc.) — solo cambian los valores hex, y se agrega `C_STATUS: dict[str, RGBColor]` para el pipeline de la Task 4.

No hay TDD aquí — son constantes de color, no hay comportamiento que testear más allá de "el archivo sigue importando". Se verifica visualmente en la Task 5 (smoke test que abre el `.pptx` generado).

- [ ] **Step 1: Reemplazar el bloque de constantes de color (líneas 20-38)**

```python
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
    "executing": RGBColor(0x1A, 0xA7, 0xB7),  # Worldpanel Blue (variante chart)
    "implemented": RGBColor(0x2B, 0xEF, 0xB9),  # Mint
    "on_hold": RGBColor(0xFF, 0xD6, 0x1F),  # Yellow
    "handed_off": RGBColor(0x00, 0x4A, 0x52),  # Deep Teal
    "rejected": RGBColor(0xF8, 0x71, 0xA0),  # Rose
}
```

- [ ] **Step 2: Actualizar `progress_color` y `risk_color`/`blocker_color` (líneas 147-168) para usar los mismos tonos de riesgo**

```python
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
```

(`risk_color`/`blocker_color` no cambian de lógica, solo quedan documentadas junto al nuevo `progress_color` para que el diff sea claro — ya usan `C_RISK_HIGH`/`C_RISK_MED`, que ya se redefinieron en el Step 1.)

- [ ] **Step 3: Verificar que el módulo sigue importando sin errores**

```bash
.venv\Scripts\python -c "import scripts.generate_execution_status_presentation"
```

Esperado: sin output, sin traceback.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_execution_status_presentation.py
git commit -m "style: reskinear el generador a paleta oficial Worldpanel"
```

---

## Task 4: Slide 1 — portada de resumen ejecutivo + pipeline + notas del presentador

**Files:**
- Modify: `scripts/generate_execution_status_presentation.py:1-14` (imports), `:203-249` (`_draw_header`), agrega `_draw_pipeline`, `_draw_speaker_notes`, `build_summary_slide` antes de `build_slide` (línea 455)

**Interfaces:**
- Consumes: `PortfolioSummary`, `resolve_project_note`, `STATUS_LABELS_ES`, `ALL_STATUSES`, `CLOSED_STATUSES` (Task 1); `C_STATUS`, `C_TEXT_DARK`, etc. (Task 3); `add_textbox`, `add_metric_card` (ya existen).
- Produces: `PIPELINE_ORDER: list[str]` (alias de `ALL_STATUSES`, mismo orden que `dashboard.md`), `build_summary_slide(prs, summary, notes_by_id, all_projects, generated_at, slide_num, total_slides) -> None`. También cambia la firma de `build_slide` (ya existía): pierde el parámetro `all_projects`, que se queda en `build_slide(prs, chunk, slide_num, total_slides, generated_at) -> None` — la Task 5 lo llama con esa firma nueva.

- [ ] **Step 1: Agregar `Emu` a los imports (línea 14)**

Reemplazar:
```python
from pptx.util import Inches, Pt
```
por:
```python
from pptx.util import Emu, Inches, Pt
```

Y agregar el import del servicio de dominio, junto a los imports existentes (después de la línea 8, `from typing import Iterable`):
```python
from domain.services.executive_summary_service import (
    ALL_STATUSES,
    STATUS_LABELS_ES,
    PortfolioSummary,
    resolve_project_note,
)

PIPELINE_ORDER = ALL_STATUSES
```

- [ ] **Step 2: Generalizar `_draw_header` (líneas 203-249) para recibir título y subtítulo**

Reemplazar la firma y el cuerpo de `_draw_header`:

```python
def _draw_header(slide, prs, slide_num: int, total_slides: int, title: str, subtitle: str) -> None:
    header = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, prs.slide_width, HEADER_H)
    header.fill.solid()
    header.fill.fore_color.rgb = C_HEADER_BG
    header.line.color.rgb = C_HEADER_BG

    add_textbox(
        slide, Inches(0.45), Inches(0.18), Inches(9.0), Inches(0.3), title, 24, bold=True, color=C_HEADER_TEXT
    )
    add_textbox(
        slide, Inches(0.45), Inches(0.5), Inches(6.0), Inches(0.18), subtitle, 9, color=C_HEADER_SUB
    )

    if total_slides > 1:
        add_textbox(
            slide, Inches(10.3), Inches(0.28), Inches(1.5), Inches(0.18),
            f"{slide_num} / {total_slides}", 10, color=C_HEADER_CUT, align=PP_ALIGN.RIGHT,
        )

    if LOGO_PATH.exists():
        try:
            slide.shapes.add_picture(str(LOGO_PATH), Inches(12.0), Inches(0.09), height=Inches(0.58))
        except Exception:
            pass
```

(Igual que antes, solo agrega los parámetros `title`/`subtitle` en vez del texto fijo "Resumen ejecutivo | Proyectos en ejecucion". `LOGO_PATH` sigue apuntando a un archivo que hoy no existe — ese `if .exists()` ya lo hacía opcional; exportar el logo real desde el SVG de marca a PNG es un paso manual fuera de este plan.)

- [ ] **Step 3: Agregar `_draw_pipeline` (antes de `build_slide`, línea 455)**

```python
def _draw_pipeline(slide, status_counts: dict[str, int], top) -> None:
    total = sum(status_counts.values()) or 1
    add_textbox(
        slide, Inches(0.45), top, Inches(6.0), Inches(0.2),
        f"Pipeline del portafolio · {sum(status_counts.values())} proyectos", 9, bold=True, color=C_TEXT_LIGHT,
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
        dot = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, cx, legend_top + Inches(0.03), Inches(0.12), Inches(0.12))
        dot.fill.solid()
        dot.fill.fore_color.rgb = C_STATUS[status]
        dot.line.color.rgb = C_STATUS[status]
        add_textbox(
            slide, cx + Inches(0.18), legend_top, Inches(1.35), Inches(0.2),
            f"{STATUS_LABELS_ES[status]} {status_counts[status]}", 8, color=C_TEXT_MID,
        )
```

- [ ] **Step 4: Agregar `_draw_speaker_notes`**

```python
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
```

- [ ] **Step 5: Agregar `build_summary_slide`**

```python
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
        slide, prs, slide_num, total_slides,
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
        slide, Inches(0.45), Inches(2.05), Inches(12.4), Inches(0.5),
        f"Cada mes, el equipo ahorra el equivalente a {summary.fte_equivalent} de trabajo de una "
        f"persona a tiempo completo — con base en las {summary.closed_count} automatizaciones ya cerradas.",
        12, color=C_TEXT_DARK,
    )

    _draw_pipeline(slide, summary.status_counts, Inches(2.75))
    _draw_speaker_notes(slide, summary, notes_by_id, all_projects)
    _draw_footer(slide, generated_at)
```

- [ ] **Step 6: Actualizar el único call site restante de `_draw_header`, dentro de `build_slide` (línea ~468)**

En `build_slide` (la función que dibuja las slides de detalle), cambiar:
```python
    _draw_header(slide, prs, slide_num, total_slides)
```
por:
```python
    _draw_header(
        slide, prs, slide_num, total_slides,
        title="Detalle · Proyectos en ejecución",
        subtitle="Fuente: Supabase (project_notes)",
    )
```

Y eliminar el bloque `if slide_num == 1: _draw_metrics(...)` de `build_slide` — ya no aplica, la slide 1 la arma `build_summary_slide` por separado. Con eso, el parámetro `all_projects` de `build_slide` deja de tener consumidor (era solo para `_draw_metrics`) — se elimina de la firma en vez de dejarlo sin uso. `build_slide` queda usando siempre `COL_HEADER_Y_SN`/`ROW_START_Y_SN`:

```python
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
        slide, prs, slide_num, total_slides,
        title="Detalle · Proyectos en ejecución",
        subtitle="Fuente: Supabase (project_notes)",
    )

    _draw_column_headers(slide, COL_HEADER_Y_SN)

    for i, project in enumerate(chunk):
        _draw_project_row(slide, project, i, ROW_START_Y_SN)

    _draw_footer(slide, generated_at)
```

`_draw_metrics` (líneas 409-428 del archivo original) queda sin uso — eliminarla junto con este cambio.

- [ ] **Step 7: Verificar que el módulo sigue importando**

```bash
.venv\Scripts\python -c "import scripts.generate_execution_status_presentation"
```

Esperado: sin traceback.

- [ ] **Step 8: Commit**

```bash
git add scripts/generate_execution_status_presentation.py
git commit -m "feat: agregar slide de portada con resumen ejecutivo y pipeline"
```

---

## Task 5: CLI (`--notes`, `--out`), guard de `DATABASE_URL` y smoke test end-to-end

**Files:**
- Modify: `scripts/generate_execution_status_presentation.py:16-18` (rutas), `:486-519` (`_build_prs`, `build_presentation`, `build_presentation_bytes`, `main`)
- Modify: `tests/unit/test_generate_execution_status_presentation.py` (agrega el smoke test)

**Interfaces:**
- Consumes: todo lo de las Tasks 1-4.
- Produces: `parse_args(argv=None)`, `main()` actualizado, `_build_prs(all_projects, executing, summary, notes_by_id) -> Presentation`, `build_presentation(all_projects, executing, summary, notes_by_id, output_path) -> Path`.

- [ ] **Step 1: Escribir el smoke test**

Agregar dos imports nuevos al principio de `tests/unit/test_generate_execution_status_presentation.py`
(no dupliques el `from scripts.generate_execution_status_presentation import (...)` que ya
agregó la Task 2 — sumale `build_presentation` a esa misma línea):

```python
from pptx import Presentation as PptxReader

from domain.services.executive_summary_service import compute_portfolio_summary
from scripts.generate_execution_status_presentation import (
    ProjectStatus,
    build_presentation,
    fetch_all_projects,
    fetch_executing_projects,
)
```

Y añadir al final del archivo:

```python
def test_build_presentation_writes_summary_plus_detail_slides(tmp_path):
    all_projects = [
        {"project_id": "A", "name": "Cerrado", "status": "implemented", "hours_saved_per_month": 100},
        {"project_id": "B", "name": "Activo", "status": "executing", "hours_saved_per_month": 0},
    ]
    executing = [
        ProjectStatus(
            project_id="B", name="Activo", progress_percent=50, progress_at="2026-09-01",
            general_note="nota", next_step="paso", blocker="", risk="",
        )
    ]
    summary = compute_portfolio_summary(all_projects)
    out_path = tmp_path / "out.pptx"

    result_path = build_presentation(all_projects, executing, summary, {}, out_path)

    assert result_path == out_path
    assert out_path.exists()
    prs = PptxReader(str(out_path))
    assert len(prs.slides) == 2  # 1 portada + 1 slide de detalle (1 chunk de <=4 filas)


def test_build_presentation_with_no_executing_projects_still_has_summary_slide(tmp_path):
    all_projects = [{"project_id": "A", "name": "Cerrado", "status": "implemented", "hours_saved_per_month": 100}]
    summary = compute_portfolio_summary(all_projects)
    out_path = tmp_path / "out.pptx"

    build_presentation(all_projects, [], summary, {}, out_path)

    prs = PptxReader(str(out_path))
    assert len(prs.slides) == 1
```

- [ ] **Step 2: Correr — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_generate_execution_status_presentation.py -v
```

Esperado: FAIL — `build_presentation` todavía tiene la firma vieja.

- [ ] **Step 3: Reemplazar rutas hardcodeadas (líneas 16-18)**

```python
DEFAULT_OUTPUT_PATH = Path("docs") / "Resumen_Proyectos_Ejecucion.pptx"
LOGO_PATH = Path("logo_DDNola.png")
```

(Se elimina `DB_PATH` — ya no se usa un archivo SQLite fijo; la conexión sale de `infra.db.adapter.get_connection()`, que lee `DATABASE_URL`.)

- [ ] **Step 4: Reemplazar `_build_prs`, `build_presentation`, `build_presentation_bytes` y `main` (líneas 486-519)**

```python
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


def parse_args(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Genera el deck ejecutivo (resumen + detalle operativo).")
    parser.add_argument("--notes", default=None, help="Ruta al JSON de notas por proyecto (opcional).")
    parser.add_argument("--out", default=None, help="Ruta de salida del .pptx.")
    return parser.parse_args(argv)


def main() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL no está seteada. Este script requiere Supabase — "
            "seteala en la sesión antes de correr (mismo requisito que /sync-bitacora)."
        )

    args = parse_args()

    from infra.db.adapter import get_connection

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


if __name__ == "__main__":
    main()
```

También agregar `import os` al bloque de imports del principio del archivo si no está ya (verificar línea 1-8; no estaba en el archivo original).

- [ ] **Step 5: Correr los tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_generate_execution_status_presentation.py -v
```

Esperado: 5 PASSED (los 3 de fetch de la Task 2 + los 2 nuevos de `build_presentation`).

- [ ] **Step 6: Correr toda la suite del repo evaluador para confirmar que nada más se rompió**

```bash
.venv\Scripts\python -m pytest -v
```

Esperado: todo PASSED (sin regresiones en `test_scoring_engine.py`, `test_id_generator.py`, etc. — este plan no los toca).

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_execution_status_presentation.py tests/unit/test_generate_execution_status_presentation.py
git commit -m "feat: CLI --notes/--out y guard de DATABASE_URL en el generador"
```

---

## Task 6: `.gitignore` en el vault de Obsidian

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Agregar la carpeta de salida**

Añadir al final de `.gitignore`:

```
presentaciones/
```

- [ ] **Step 2: Confirmar que git la ignora**

```bash
mkdir presentaciones
echo test > presentaciones/test.txt
git status --short
```

Esperado: `presentaciones/` no aparece en la salida (o aparece solo si `.gitignore` no se guardó bien — en ese caso revisar el paso anterior).

```bash
rm -r presentaciones
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignorar carpeta de presentaciones generadas"
```

---

## Task 7: Comando `/presentacion-ejecutiva`

**Files:**
- Create: `.claude/commands/presentacion-ejecutiva.md`

**Interfaces:**
- Consumes: MCP de Supabase ya conectado en la sesión (`execute_sql` sobre el proyecto `wcicvyqvjbufpicvhoac`); `scripts/generate_execution_status_presentation.py --notes <json> --out <pptx>` (Tasks 1-5, interfaz de CLI ya fija: acepta ambos flags, requiere `DATABASE_URL` en el entorno).
- Produces: `presentaciones/notas-YYYY-MM-DD.json`, `presentaciones/presentacion-ejecutiva-YYYY-MM-DD.pptx`.

Este repo no tiene build ni tests (ver `CLAUDE.md`) — el archivo de comando es texto de instrucciones para Claude, no código Python. No hay TDD acá; el equivalente es correrlo una vez y revisar el resultado (Step 3).

- [ ] **Step 1: Crear `.claude/commands/presentacion-ejecutiva.md`**

```markdown
---
description: Genera el .pptx ejecutivo del portafolio (resumen + pipeline + detalle operativo)
allowed-tools: Read, Glob, Grep, Write, Bash(python:*), PowerShell(python:*), Bash(mkdir:*)
---

# Presentación ejecutiva del portafolio

Arma un `.pptx` de 2 slides — resumen de impacto agregado + pipeline, y
detalle operativo de proyectos en ejecución — a partir de Supabase y del
vault, extendiendo el generador del repo evaluador. Ver el diseño completo en
[docs/superpowers/specs/2026-09-04-presentacion-ejecutiva-design.md](../../docs/superpowers/specs/2026-09-04-presentacion-ejecutiva-design.md).

## Antes de correr

1. **Ruta al repo de la app.** Igual que `/sync-bitacora`: se lee de
   `.claude/sync-bitacora.local.json` (`evaluator_repo_path`). Si no existe,
   pregunta la ruta y créalo con el mismo formato que usa `/sync-bitacora`.
2. **`DATABASE_URL` de Supabase.** Tiene que estar seteada en el entorno de
   la sesión de terminal donde corras el script — nunca la adivines, no la
   guardes en ningún archivo de este repo, no la imprimas de vuelta en el
   chat.

## Al correr

1. Consulta la tabla `projects` de Supabase (proyecto `wcicvyqvjbufpicvhoac`)
   por `execute_sql`, solo lectura: `project_id, name, status, description,
   closed_at`.
2. Construye el mapa `project_id → slug` leyendo el frontmatter `project_id:`
   de cada `proyectos/*/index.md`.
3. Para cada proyecto de Supabase:
   - Si su `project_id` está en el mapa: lee el `## 📄 Overview` de su
     `index.md` y la entrada más reciente de su `bitacora.md`; redacta una
     frase de "qué es" y una de "estado actual" (puede usar el `estado` del
     `index.md` y, si hay, el hallazgo más reciente de la bitácora).
   - Si no está: condensa el campo `description` que trajiste de Supabase en
     una frase de "qué es"; para "estado actual" usa el `status` de Supabase
     y, si `closed_at` no es nulo, la fecha de cierre.
4. Asegúrate de que exista `presentaciones/` (créala si falta) y escribe
   `presentaciones/notas-<fecha-de-hoy>.json`:
   ```json
   {
     "generated_at": "<fecha-de-hoy YYYY-MM-DD>",
     "projects": [
       {"project_id": "...", "que_es": "...", "estado_frase": "..."}
     ]
   }
   ```
5. Corre, con `DATABASE_URL` ya seteada en el entorno:
   ```
   python "<evaluator_repo_path>/scripts/generate_execution_status_presentation.py" --notes "presentaciones/notas-<fecha-de-hoy>.json" --out "presentaciones/presentacion-ejecutiva-<fecha-de-hoy>.pptx"
   ```
6. Si el script termina con `DATABASE_URL no está seteada` u otro error,
   repórtalo tal cual — no reintentes con otra fuente de datos ni inventes
   números.
7. Entrega el `.pptx` resultante y reporta un resumen corto: horas
   ahorradas/mes, equivalente en tiempo-persona, proyectos cerrados y en
   ejecución (los mismos números que quedaron en la portada).
8. **No hagas commit** del `.pptx` ni del JSON de notas — están en
   `presentaciones/`, que está en `.gitignore` (ver Task 6 del plan de
   implementación).
```

- [ ] **Step 2: Verificar el frontmatter del comando**

```bash
head -5 .claude/commands/presentacion-ejecutiva.md
```

Esperado: bloque `---` con `description` y `allowed-tools`, igual formato que `.claude/commands/sync-bitacora.md`.

- [ ] **Step 3: Correrlo una vez de punta a punta**

Desde una sesión de Claude Code en este repo, con `DATABASE_URL` seteada:
```
/presentacion-ejecutiva
```
Esperado: se genera `presentaciones/notas-<hoy>.json` y
`presentaciones/presentacion-ejecutiva-<hoy>.pptx`; el resumen que reporta
Claude coincide con los números calculados a mano en la spec (2026-09-04:
5,662 h/mes, "2 años y 9 meses", 8 cerrados, 7 en ejecución — pueden variar
si el portafolio cambió desde entonces). Si `project_notes` sigue vacía en
Supabase (ver prerrequisito en la spec), el detalle operativo (slides 2+)
saldrá sin filas — es esperado hasta que se resuelva ese prerrequisito, no
es un bug de este comando.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/presentacion-ejecutiva.md
git commit -m "feat: agregar comando /presentacion-ejecutiva"
```

---

## Task 8: Documentar el comando en `AGENTS.md`/`CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Agregar la entrada a la lista de comandos**

En `CLAUDE.md`, sección "Específico de Claude Code" → "Comandos disponibles",
agregar después de la entrada de `/sync-bitacora`:

```markdown
  - `/presentacion-ejecutiva` — genera un `.pptx` de 2 slides (resumen de
    impacto agregado + pipeline, y detalle operativo de proyectos en
    ejecución) combinando Supabase con la documentación del vault. Ver
    `docs/superpowers/specs/2026-09-04-presentacion-ejecutiva-design.md`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: agregar /presentacion-ejecutiva a la lista de comandos"
```

---

## Orden de ejecución y prerrequisito pendiente

Tasks 1-6 y 8 no dependen de que `project_notes` esté poblada en Supabase —
se pueden implementar y comitear ya. La **Task 7, Step 3** (correr el
comando de punta a punta) es la primera vez que el plan toca datos reales:
si el detalle operativo sale vacío, es el prerrequisito confirmado en la
spec (sincronizar `project_notes` vía `/sync-bitacora`, y antes de eso
confirmar `DATABASE_URL` en los secrets de Streamlit Cloud), no un defecto
de este plan.
