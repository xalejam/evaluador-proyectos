# Specs de Pestañas — Evaluador de Proyectos

Documentación funcional y técnica de cada pestaña del sistema. Cada spec sigue la misma plantilla de 13 secciones: propósito, inputs, outputs, lógica de negocio, flujo, queries, UI, dependencias, casos borde, performance, validación, historial y definición analítica.

## Índice

| # | Pestaña | Archivo | Descripción |
|---|---------|---------|-------------|
| 1 | Viabilidad | [viabilidad.md](viabilidad.md) | Evaluación y scoring de nuevos proyectos de automatización |
| 2 | Seguimiento Operativo | [seguimiento_operativo.md](seguimiento_operativo.md) | Notas inmutables, cambios de estado y resumen ejecutivo |
| 3 | Impact KPIs | [post_impl.md](post_impl.md) | Seguimiento post-implementación vs. proyecciones originales |
| 4 | Dashboard | [dashboard.md](dashboard.md) | Vista general del portafolio con KPIs y gráficos |
| 5 | Use Case Matrix | [use_case_matrix.md](use_case_matrix.md) | Scatter Impact vs Effort para priorización estratégica |
| 6 | Feedback | [feedback.md](feedback.md) | Procesamiento de encuestas de satisfacción desde Excel |
| 7 | SQL | [sql.md](sql.md) | Terminal de consultas SELECT sobre project_viability.db |

## Arquitectura general

Ver [../architecture.md](../architecture.md) para el diagrama de bloques del sistema.

Ver [../data-model.md](../data-model.md) para el esquema completo de tablas.

## Flujo entre pestañas

```
Viabilidad ──────────────────┬──► Use Case Matrix (sync automático al guardar)
    │                        │
    │ (crea proyectos)       └──► Dashboard (lee portafolio)
    │
Seguimiento Operativo ────────────► (cambia estados via /end)
    │
    └──► Email post-cierre (PENDIENTE — próxima fase)

Impact KPIs ◄────────────────────── Feedback (comparte FeedbackProcessor)
    │
    └──► Dashboard (tracking_df)
```

## Mejoras pendientes (cross-tab)

| Mejora | Afecta | Prioridad |
|--------|--------|-----------|
| Email programado al cerrar proyecto (`/end`) | Seguimiento Operativo, Feedback | Alta |
| Modo read-only real en SQL (SQLite URI) | SQL | Media |
| `st.cache_data` en lecturas frecuentes | Dashboard, Seguimiento, Post-impl | Media |
| Consolidar dual DB en una sola fuente | Viabilidad, Use Case Matrix | Alta |
| Path configurable de `encuesta_feedback.xlsx` | Impact KPIs, Feedback | Baja |
| Agregar `adoption_rate` al cuestionario de encuesta | Feedback, Impact KPIs | Baja |
