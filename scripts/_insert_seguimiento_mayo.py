#!/usr/bin/env python3
"""Inserta notas de seguimiento de mayo 2026 separadas por tipo en project_viability.db."""

import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.db_migrations import ensure_notes_schema, ensure_projects_schema

DB_PATH = Path(__file__).resolve().parent.parent / "project_viability.db"

# Cada entrada genera 4 notas: general, proximo_paso, bloqueador, riesgo.
# entry_group_id compartido agrupa las 4 notas del mismo corte.
ENTRIES = [
    # MX-DDD-0001
    {
        "project_id": "MX-DDD-0001",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": 97,
        "general": "Se probaron los archivos reportados con errores y el codigo funciona correctamente con los ultimos cambios aplicados.",
        "proximo_paso": "Validar el archivo restante pendiente cuando este disponible para prueba.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "MX-DDD-0001",
        "created_at": "2026-05-11 16:05:00",
        "progress_percent": 97,
        "general": "Se indico que el desarrollo pasara a etapa de pruebas por parte de D&D para su entrega final.",
        "proximo_paso": "Ejecutar pruebas y mover el estado a completado cuando finalicen.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "MX-DDD-0001",
        "created_at": "2026-05-19 16:05:00",
        "progress_percent": 98,
        "general": "Programa final entregado a D&D para sus pruebas.",
        "proximo_paso": "Recibir feedback para cerrar el proyecto.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    # HI-DDD-0001
    {
        "project_id": "HI-DDD-0001",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": 10,
        "general": "No se registraron avances ni cambios en este frente.",
        "proximo_paso": "Retomar actividades cuando se priorice nuevamente.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "HI-DDD-0001",
        "created_at": "2026-05-11 16:05:00",
        "progress_percent": 10,
        "general": "No se registraron avances ni cambios en este frente.",
        "proximo_paso": "Retomar actividades cuando se priorice nuevamente.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "HI-DDD-0001",
        "created_at": "2026-05-18 16:05:00",
        "progress_percent": 10,
        "general": "No se registraron avances ni cambios en este frente.",
        "proximo_paso": "Retomar actividades cuando se priorice nuevamente.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    # MX-DDD-0004
    {
        "project_id": "MX-DDD-0004",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": 95,
        "general": "No se ha avanzado en revision de errores debido a prioridad en otros desarrollos.",
        "proximo_paso": "Retomar analisis de errores cuando se libere capacidad.",
        "bloqueador": "Prioridad en otras tareas.",
        "riesgo": "Retraso acumulado en correcciones.",
    },
    {
        "project_id": "MX-DDD-0004",
        "created_at": "2026-05-11 16:05:00",
        "progress_percent": 95,
        "general": "No se realizaron avances ni ejecuciones relacionadas con Walmart.",
        "proximo_paso": "Retomar el tema en una siguiente sesion de trabajo.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "MX-DDD-0004",
        "created_at": "2026-05-18 16:05:00",
        "progress_percent": None,
        "general": "No se ha avanzado aun porque se priorizo cerrar Order Forms y hay dudas pendientes sobre definiciones funcionales.",
        "proximo_paso": "Retomar los cambios una vez finalizado Order Forms y aclarar las definiciones necesarias.",
        "bloqueador": "Prioridad en otros desarrollos y falta de foco en este frente.",
        "riesgo": "Acumulacion de trabajo pendiente si se sigue postergando.",
    },
    # MX-DDD-0005
    {
        "project_id": "MX-DDD-0005",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": 50,
        "general": "Se avanzo significativamente y es la prioridad actual del equipo. Se identifico que la conexion a SharePoint requiere credenciales especificas; por el momento se decide hacer el programa local.",
        "proximo_paso": "Continuar con el desarrollo y validaciones pendientes. Se requiere informacion de jerarquias para completar la hoja de productos.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    {
        "project_id": "MX-DDD-0005",
        "created_at": "2026-05-11 16:05:00",
        "progress_percent": 50,
        "general": "El codigo esta refactorizado y se estan ajustando filtros, estructura de repositorio y descargas automaticas pendientes.",
        "proximo_paso": "Implementar lo faltante de ventanas y celdas, incluyendo la descarga automatica del package master.",
        "bloqueador": "Complejidad del repositorio y pendientes de permisos.",
        "riesgo": "Retraso si los permisos o dependencias no quedan correctamente configurados.",
    },
    {
        "project_id": "MX-DDD-0005",
        "created_at": "2026-05-18 16:05:00",
        "progress_percent": None,
        "general": "Se estan realizando ajustes para manejar filas incompletas y recuperar columnas necesarias para reportes.",
        "proximo_paso": "Completar los cambios y coordinar la carga del programa considerando la posible nueva columna de estado activo/inactivo.",
        "bloqueador": "Definicion pendiente sobre la nueva columna y disponibilidad de validacion.",
        "riesgo": "Reprocesos si la estructura final cambia despues.",
    },
    # MX-DDD-0006
    {
        "project_id": "MX-DDD-0006",
        "created_at": "2026-05-01 16:05:00",
        "progress_percent": None,
        "general": "Se genero un boceto con los comentarios de la reunion anterior.",
        "proximo_paso": "Compartir boceto con equipo AA para implementar.",
        "bloqueador": "Ninguno.",
        "riesgo": "Retraso en implementacion visual.",
    },
    {
        "project_id": "MX-DDD-0006",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": None,
        "general": "Prototipos revisados con Advance y cambios de graficos quedaron del lado de ellos.",
        "proximo_paso": "Generar boceto de insumos graficos para implementar en Power BI.",
        "bloqueador": "Dependencia de entrega por parte de Advanced A.",
        "riesgo": "Retraso en implementacion visual.",
    },
    {
        "project_id": "MX-DDD-0006",
        "created_at": "2026-05-18 16:05:00",
        "progress_percent": None,
        "general": "Se compartio un boceto en Power BI con el area comercial y se espera feedback.",
        "proximo_paso": "Recibir validacion del area comercial para confirmar si la solucion propuesta es util.",
        "bloqueador": "Espera de feedback de comerciales.",
        "riesgo": "Que la solucion no sea aceptada y requiera rediseno.",
    },
    # LA-DDD-0002
    {
        "project_id": "LA-DDD-0002",
        "created_at": "2026-05-05 16:05:00",
        "progress_percent": 60,
        "general": "Se avanza con la creacion del template de Coppel.",
        "proximo_paso": "Terminar configuracion de PPT.",
        "bloqueador": "Ninguno.",
        "riesgo": "Lentitud de programacion.",
    },
    {
        "project_id": "LA-DDD-0002",
        "created_at": "2026-05-11 16:05:00",
        "progress_percent": 70,
        "general": "Se avanza con la creacion del template de Coppel.",
        "proximo_paso": "Compartir con comercial para comparar valores.",
        "bloqueador": "Ninguno.",
        "riesgo": "Lentitud de programacion.",
    },
    {
        "project_id": "LA-DDD-0002",
        "created_at": "2026-05-19 16:05:00",
        "progress_percent": 90,
        "general": "Se termino de hacer la configuracion y se genero la PPT de Q4 para comparar versus entregado.",
        "proximo_paso": "Se envia la presentacion para evaluar por comercial.",
        "bloqueador": "Ninguno.",
        "riesgo": "Ninguno.",
    },
    # LA-COPILOT-0001
    {
        "project_id": "LA-COPILOT-0001",
        "created_at": "2026-05-08 16:05:00",
        "progress_percent": 90,
        "general": "Se presentaron los principales agentes al board recibiendo feedback y mejoras a implementar.",
        "proximo_paso": "Actualizar Casos de Uso basado en feedbacks.",
        "bloqueador": "Ninguna.",
        "riesgo": "Ninguna.",
    },
    {
        "project_id": "LA-COPILOT-0001",
        "created_at": "2026-05-16 16:05:00",
        "progress_percent": 90,
        "general": "PPT de casos de uso actualizado. Se identifico la necesidad de estructurar repositorios en SharePoint para que la IA pueda leer y usar la informacion eficientemente.",
        "proximo_paso": "Disenar una estructura base de carpetas y un marco de organizacion enfocado en facilidad de busqueda y lectura.",
        "bloqueador": "Falta de estructura homogenea entre paises.",
        "riesgo": "Que la IA consuma informacion desordenada o incompleta.",
    },
]

TYPE_MAP = {
    "general": "general",
    "proximo_paso": "proximo_paso",
    "bloqueador": "bloqueador",
    "riesgo": "riesgo",
}


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    ensure_projects_schema(conn)
    ensure_notes_schema(conn)

    # Borrar las notas 'seguimiento' insertadas previamente en esta sesion
    deleted = conn.execute(
        "DELETE FROM project_notes WHERE note_type = 'seguimiento' AND created_at >= '2026-05-01'"
    ).rowcount
    print(f"Eliminadas {deleted} notas tipo 'seguimiento' previas.")

    inserted = 0
    for entry in ENTRIES:
        group_id = uuid.uuid4().hex
        # La nota general lleva el progress_percent; las demas no
        for field, note_type in TYPE_MAP.items():
            text = entry[field].strip()
            progress = entry.get("progress_percent") if field == "general" else None
            conn.execute(
                """INSERT INTO project_notes
                   (project_id, note_text, note_type, author, tags, is_private,
                    entry_group_id, note_title, progress_percent, estimated_end_date, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["project_id"],
                    text,
                    note_type,
                    "Xiomara",
                    "",
                    0,
                    group_id,
                    f"Seguimiento {entry['created_at'][:10]}",
                    progress,
                    None,
                    entry["created_at"],
                ),
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Insertadas {inserted} notas ({inserted // 4} entradas x 4 tipos).")


if __name__ == "__main__":
    main()
