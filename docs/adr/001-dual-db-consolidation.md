# ADR 001: Consolidación de Base de Datos Dual

**Estado:** Implementado  **Fecha:** 2026-04-24  **Completado:** 2026-05-20

## Contexto

El proyecto nació con `project_viability.db` (SQLite raw) y luego agregó `data/projects.db` (SQLAlchemy ORM) para el módulo Use Case Matrix. El dual-DB crea riesgo de divergencia silenciosa: proyectos aprobados en el DB principal pueden no estar reflejados en la matrix, y viceversa.

## Decisión

Consolidar a `project_viability.db` como única fuente de verdad. Migrar el esquema de SQLAlchemy para apuntar a la misma DB. Eliminar la lógica de sync en `use_case_matrix_sync.py`.

## Consecuencias

- **Positivo:** elimina divergencia, simplifica infra, un solo punto de backup y auditoría
- **Negativo:** requiere migración de datos existentes en `data/projects.db`
- **Mitigación:** `scripts/audit_db_sync.py` identifica divergencias antes de la migración

## Implementación (2026-05-20)

- Audit ejecutado: `scripts/audit_db_sync.py` reportó **0 proyectos divergentes**
- `use_case_matrix_sync.py` ya escribía a `project_viability.db` directamente
- `ui/use_case_matrix.py` ya leía de `project_viability.db`
- `ui/tabs/planning.py` tenía copia local de `sync_to_use_case_matrix` usando SQLAlchemy → `data/projects.db` — eliminada y reemplazada por import de `infra.integrations.use_case_matrix_sync`
- `data/projects.db` ya no recibe escrituras desde ningún módulo activo; el archivo físico se conserva como backup
