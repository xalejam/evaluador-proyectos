# Seed LA-COPILOT-001 Historical Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insertar las 6 entradas históricas del proyecto LA-COPILOT-001 "Implementacion de Copilot" en la tabla `project_notes` de `project_viability.db`, y actualizar `loop_url` en la tabla `projects`.

**Architecture:** Script Python standalone (`scripts/seed_copilot_notes.py`) que reutiliza `infra.db.connection.get_sqlite_conn`. Cada entrada del usuario genera un `entry_group_id` (UUID hex) y entre 1–4 filas en `project_notes` (una por tipo no vacío). También hace `UPDATE projects SET loop_url = ?` para LA-COPILOT-001.

**Tech Stack:** Python 3, sqlite3, uuid, pathlib — sin dependencias externas adicionales.

---

## Estructura de archivos

| Acción | Archivo |
|--------|---------|
| Crear | `scripts/seed_copilot_notes.py` |
| Leer (solo referencia) | `infra/db/connection.py` |
| DB destino | `project_viability.db` (raíz del repo) |

### Schema relevante — `project_notes`
```
note_id          INTEGER PRIMARY KEY AUTOINCREMENT
project_id       TEXT NOT NULL
note_text        TEXT NOT NULL
note_type        TEXT NOT NULL   -- 'general' | 'proximo_paso' | 'bloqueador' | 'riesgo'
author           TEXT NOT NULL
tags             TEXT
is_private       INTEGER NOT NULL DEFAULT 0
created_at       TEXT NOT NULL   -- datetime ISO, e.g. '2026-02-11 00:00:00'
entry_group_id   TEXT            -- UUID hex, mismo para el grupo
note_title       TEXT
progress_percent INTEGER
estimated_end_date TEXT
```

### Entradas a insertar

| # | Fecha | Avance | Tipos |
|---|-------|--------|-------|
| 1 | 2026-02-11 | 0 | general, proximo_paso, bloqueador, riesgo |
| 2 | 2026-02-16 | 3 | general, proximo_paso, bloqueador, riesgo |
| 3 | 2026-02-16 | 6 | general, proximo_paso, bloqueador, riesgo |
| 4 | 2026-02-17 | 9 | general, proximo_paso, bloqueador, riesgo |
| 5 | 2026-03-07 | 12 | general, proximo_paso, bloqueador, riesgo |
| 6 | 2026-03-20 | 15 | general, proximo_paso |
| 7 | 2026-04-10 | 18 | general, proximo_paso, bloqueador, riesgo |

---

## Task 1: Crear el script de seed

**Files:**
- Create: `scripts/seed_copilot_notes.py`

- [ ] **Step 1: Crear `scripts/seed_copilot_notes.py`** con el contenido completo:

```python
"""Seed histórico de notas para LA-COPILOT-001."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infra.db.connection import get_sqlite_conn

PROJECT_ID = "LA-COPILOT-001"
AUTHOR = "Xiomara"
LOOP_URL = (
    "https://loop.cloud.microsoft/join/eyJnIjoiVDBSVFVIeHJkR2RzWW5WakxuTm9ZWEpsY0c5cGJuUXVZMjl0ZkdJaFYzVjJVRU5UTkVGeWF6SXljVTk2TTNKTExVb3RjbmxGWTFsZmEzazRVa3BwTUVsNlRVNVdTbTVTWVhoSk1GZzFTMWhsVlZSWk1XczRhVXBmVlc0NUxYd3dNVU5GTmtsUVRFNU9UVFZYVEVkWVRWQTBVa1JKVFZwTU5saEZXRk5LUWtoSiIsImkiOiJjY041dGRneUVDZmFGdXI0d3ExMXciLCJ3IjoiVDBSVFVIeHJkR2RzWW5WakxuTm9ZWEpsY0c5cGJuUXVZMjl0ZkdJaFYzVjJVRU5UTkVGeWF6SXljVTk2TTNKTExVb3RjbmxGWTFsZmEzazRVa3BwTUVsNlRVNVdTbTVTWVhoSk1GZzFTMWhsVlZSWk1XczRhVXBmVlc0NUxYd3dNVU5GTmtsUVRFNU9UVFZYVEVkWVRWQTBVa1JKVFZwTU5saEZXRk5LUWtoSiJ9"
)

# Cada entrada: (fecha_str, progress_percent, {note_type: text})
ENTRIES = [
    (
        "2026-02-11 00:00:00",
        0,
        {
            "general": (
                "Inicio formal del proyecto Copilot en LATAM. "
                "Se validó alcance, objetivos, metodología y rol de Champions, "
                "dejando lineamientos claros de gobernanza."
            ),
            "proximo_paso": (
                "Enviar calendario final de entrenamientos Microsoft – Gonzalo – feb/2026. "
                "Alinear Champions por área para identificación de casos de uso."
            ),
            "bloqueador": (
                "Capacidad inicial de adopción desigual; afecta ritmo del proyecto; "
                "lo destraban Champions y PMO."
            ),
            "riesgo": (
                "Riesgo de baja adopción temprana; probabilidad media; "
                "mitigar con capacitación obligatoria y comunicación clara."
            ),
        },
    ),
    (
        "2026-02-16 09:00:00",
        3,
        {
            "general": (
                "Se revisa inclusión del equipo NOLA en el proyecto. "
                "Se confirma participación en entrenamientos, pero no se garantiza "
                "licencia para todos por cupo limitado."
            ),
            "proximo_paso": (
                "Escalar necesidad de licencias vía jefaturas – Xiomara / Jorge – feb/2026. "
                "Asegurar acceso al material y sesiones sin licencia."
            ),
            "bloqueador": (
                "Licencias Copilot limitadas; impacta capacidad técnica; "
                "lo destraba liderazgo regional."
            ),
            "riesgo": (
                "Riesgo de subutilizar perfiles técnicos; probabilidad media; "
                "mitigar priorizando licencias por impacto."
            ),
        },
    ),
    (
        "2026-02-16 15:00:00",
        6,
        {
            "general": (
                "Se confirma inclusión al grupo Teams y acceso al calendario de cursos. "
                "Se habilita participación activa en entrenamientos del proyecto."
            ),
            "proximo_paso": (
                "Revisar publicaciones y definir sesiones clave a asistir – NOLA – feb/2026. "
                "Monitorear asistencia a entrenamientos críticos."
            ),
            "bloqueador": (
                "Sobrecarga de sesiones paralelas; impacto en foco; "
                "lo destraban PMO y líderes locales."
            ),
            "riesgo": (
                "Riesgo de dispersión de esfuerzo; probabilidad media; "
                "mitigar priorizando sesiones core."
            ),
        },
    ),
    (
        "2026-02-17 00:00:00",
        9,
        {
            "general": (
                "Se aclara que licencias ya fueron definidas fuera del alcance del PM. "
                "Las nuevas solicitudes deben gestionarse vía jefaturas."
            ),
            "proximo_paso": (
                "Formalizar solicitud de licencia con business case – Jorge / Xiomara – feb/2026. "
                "Evaluar impacto sin licencia full."
            ),
            "bloqueador": (
                "Gobernanza de licencias centralizada; limita flexibilidad; "
                "lo destraba dirección regional."
            ),
            "riesgo": (
                "Riesgo de fricción entre equipos; probabilidad baja-media; "
                "mitigar con criterios claros de asignación."
            ),
        },
    ),
    (
        "2026-03-07 00:00:00",
        12,
        {
            "general": (
                "Creación de Copilot para generar business case y aterrizar ideas del equipo."
            ),
            "proximo_paso": (
                "Crear business case con ideas a implementar. "
                "Evaluar impacto sin licencia full."
            ),
            "bloqueador": "",
            "riesgo": "Riesgo de que no usen la herramienta; probabilidad media.",
        },
    ),
    (
        "2026-03-20 00:00:00",
        15,
        {
            "general": (
                "Creación de business case con ideas que se podrían desarrollar."
            ),
            "proximo_paso": (
                "Presentar avances al board. "
                "Evaluar impacto sin licencia full."
            ),
            "bloqueador": "",
            "riesgo": "",
        },
    ),
    (
        "2026-04-10 00:00:00",
        18,
        {
            "general": (
                "Se presentan avances: +30 agentes y feedback del leadership. "
                "Se redefine foco hacia adopción, métricas de impacto y control de scope."
            ),
            "proximo_paso": (
                "Priorizar agentes con matriz impacto/esfuerzo – Gonzalo + Champions – abr/2026. "
                "Definir KPIs de adopción por agente – Xiomara – abr/2026."
            ),
            "bloqueador": (
                "Falta de métricas de adopción estandarizadas; "
                "impacta escalamiento; lo destraba PMO."
            ),
            "riesgo": (
                "Riesgo de exceso de scope; probabilidad alta; "
                "mitigar con MVP claro y criterios go/no-go."
            ),
        },
    ),
]

INSERT_SQL = """
    INSERT INTO project_notes
        (project_id, note_text, note_type, author, tags, is_private,
         created_at, entry_group_id, progress_percent)
    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
"""

UPDATE_LOOP_URL_SQL = """
    UPDATE projects SET loop_url = ? WHERE project_id = ?
"""


def seed() -> None:
    conn = get_sqlite_conn()
    try:
        # Verificar que el proyecto exista
        row = conn.execute(
            "SELECT project_id, name FROM projects WHERE project_id = ?",
            (PROJECT_ID,),
        ).fetchone()
        if row is None:
            print(f"ERROR: Proyecto {PROJECT_ID} no encontrado en la base de datos.")
            return
        print(f"Proyecto encontrado: {row['name']} ({row['project_id']})")

        # Actualizar loop_url en projects
        conn.execute(UPDATE_LOOP_URL_SQL, (LOOP_URL, PROJECT_ID))
        print("loop_url actualizado en projects.")

        inserted_total = 0
        for created_at, progress, notes in ENTRIES:
            group_id = uuid.uuid4().hex
            rows_in_group = 0
            for note_type, text in notes.items():
                text = text.strip()
                if not text:
                    continue
                conn.execute(
                    INSERT_SQL,
                    (PROJECT_ID, text, note_type, AUTHOR, None, created_at, group_id, progress),
                )
                rows_in_group += 1
            inserted_total += rows_in_group
            print(f"  {created_at}  avance={progress}%  → {rows_in_group} notas  [group {group_id[:8]}]")

        conn.commit()
        print(f"\nTotal insertado: {inserted_total} notas para {PROJECT_ID}.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
```

- [ ] **Step 2: Verificar que el proyecto existe antes de correr el script**

```bash
cd "c:/Users/ttMonroyX/OneDrive - Kantar/Documents/Project Managment/ReportesAdhoc/EvaluadorDeProyectos/Repositorio Evaluador"
python -c "
from infra.db.connection import get_sqlite_conn
conn = get_sqlite_conn()
row = conn.execute(\"SELECT project_id, name, status FROM projects WHERE project_id = 'LA-COPILOT-001'\").fetchone()
print(dict(row) if row else 'NO ENCONTRADO')
conn.close()
"
```

Resultado esperado: dict con `project_id='LA-COPILOT-001'` y el nombre del proyecto.

- [ ] **Step 3: Correr el script**

```bash
python scripts/seed_copilot_notes.py
```

Resultado esperado:
```
Proyecto encontrado: Implementacion de Copilot (LA-COPILOT-001)
loop_url actualizado en projects.
  2026-02-11 00:00:00  avance=0%  → 4 notas  [group xxxxxxxx]
  2026-02-16 09:00:00  avance=3%  → 4 notas  [group xxxxxxxx]
  2026-02-16 15:00:00  avance=6%  → 4 notas  [group xxxxxxxx]
  2026-02-17 00:00:00  avance=9%  → 4 notas  [group xxxxxxxx]
  2026-03-07 00:00:00  avance=12%  → 3 notas  [group xxxxxxxx]
  2026-03-20 00:00:00  avance=15%  → 2 notas  [group xxxxxxxx]
  2026-04-10 00:00:00  avance=18%  → 4 notas  [group xxxxxxxx]

Total insertado: 25 notas para LA-COPILOT-001.
```

- [ ] **Step 4: Verificar en la DB que las notas quedaron correctas**

```bash
python -c "
from infra.db.connection import get_sqlite_conn
conn = get_sqlite_conn()
rows = conn.execute(
    'SELECT created_at, note_type, progress_percent, note_text FROM project_notes WHERE project_id=? ORDER BY created_at, note_type',
    ('LA-COPILOT-001',)
).fetchall()
for r in rows:
    print(r['created_at'], r['note_type'], r['progress_percent'], r['note_text'][:60])
conn.close()
"
```

Resultado esperado: 25 filas ordenadas por fecha y tipo, con `progress_percent` correcto en cada grupo.

- [ ] **Step 5: Verificar loop_url en projects**

```bash
python -c "
from infra.db.connection import get_sqlite_conn
conn = get_sqlite_conn()
row = conn.execute('SELECT loop_url FROM projects WHERE project_id=?', ('LA-COPILOT-001',)).fetchone()
print('loop_url OK' if row and row['loop_url'] else 'loop_url FALTA')
conn.close()
"
```

- [ ] **Step 6: Commit**

```bash
git add scripts/seed_copilot_notes.py
git commit -m "feat: seed historical notes for LA-COPILOT-001 Copilot project (7 entries, 25 notes)"
```
