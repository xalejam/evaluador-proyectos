"""Seed histórico de notas para LA-COPILOT-001."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infra.db.connection import get_sqlite_conn

PROJECT_ID = "LA-COPILOT-0001"
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