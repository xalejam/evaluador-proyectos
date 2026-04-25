# ADR 001: Consolidación de Base de Datos Dual

**Estado:** Aceptado  **Fecha:** 2026-04-24

## Contexto

El proyecto nació con `project_viability.db` (SQLite raw) y luego agregó `data/projects.db` (SQLAlchemy ORM) para el módulo Use Case Matrix. El dual-DB crea riesgo de divergencia silenciosa: proyectos aprobados en el DB principal pueden no estar reflejados en la matrix, y viceversa.

## Decisión

Consolidar a `project_viability.db` como única fuente de verdad. Migrar el esquema de SQLAlchemy para apuntar a la misma DB. Eliminar la lógica de sync en `use_case_matrix_sync.py`.

## Consecuencias

- **Positivo:** elimina divergencia, simplifica infra, un solo punto de backup y auditoría
- **Negativo:** requiere migración de datos existentes en `data/projects.db`
- **Mitigación:** `scripts/audit_db_sync.py` identifica divergencias antes de la migración (Task 4)
