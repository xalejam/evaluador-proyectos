# ADR 002: Notas Operacionales como Audit Trail Inmutable

**Estado:** Aceptado  **Fecha:** 2026-04-24

## Contexto

Las notas de seguimiento operativo (bloqueadores, riesgos, próximos pasos) necesitan trazabilidad completa para auditoría y análisis de tendencias. Permitir edición/eliminación destruiría el historial y haría imposible reconstruir el estado de un proyecto en un momento dado.

## Decisión

`project_notes` es append-only. No se permiten UPDATE ni DELETE sobre notas existentes. Las "correcciones" se hacen agregando una nueva nota que reemplaza semánticamente a la anterior.

## Consecuencias

- **Positivo:** historial completo, reproducible y auditable; facilita análisis de tendencias
- **Negativo:** mayor tamaño de DB con el tiempo; la UI debe manejar la semántica de "última nota válida"
- **Mitigación:** índice compuesto en `(project_id, created_at DESC)` para queries eficientes; vistas `v_project_latest_notes` y `v_project_last_note` encapsulan la lógica de "última nota"
