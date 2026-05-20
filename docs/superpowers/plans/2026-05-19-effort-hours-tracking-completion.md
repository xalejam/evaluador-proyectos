# Cierre: Registro de Horas de Esfuerzo por Ciclo de Vida del Proyecto

**Fecha de cierre:** 2026-05-20
**Spec:** `docs/superpowers/specs/2026-05-19-effort-hours-tracking-design.md`
**Plan:** `docs/superpowers/plans/2026-05-19-effort-hours-tracking.md`
**Estado:** Completo

---

## Commits entregados

| Hash | Descripción |
|---|---|
| `5a7ec32` | docs: add spec for effort_hours tracking across project lifecycle |
| `8c20127` | docs: add implementation plan for effort_hours tracking feature |
| `91ba6fa` | feat: add effort_hours to project_notes and closed_at to projects schema |
| `0e2fa3c` | feat: add CSV backfill scripts for effort_hours (export + import with validation) |
| `63cb537` | feat: add mandatory effort_hours field to weekly note capture form |

---

## Qué se implementó

### Schema
- Campo `effort_hours REAL` agregado a `project_notes` vía `_add_column_if_missing` (migración idempotente)
- Campo `closed_at DATETIME` agregado a `projects` vía `_add_column_if_missing`
- `closed_at` se llena automáticamente la primera vez que `status` cambia a `implemented`

### Backfill histórico
- `scripts/export_notes_for_hours.py` — genera `notas_horas.csv` con las notas sin horas para llenar en Excel
- `scripts/import_notes_hours.py` — lee el CSV e imputa `effort_hours`, rechazando filas vacías/cero/negativas con mensaje explícito

### UI — Captura semanal
- Campo `st.number_input` de horas en formulario de Captura rápida (obligatorio, mínimo 0.5 h)
- Solo la nota `general` del grupo lleva `effort_hours`; los otros tipos del mismo corte quedan en NULL
- Sección **"Registrar actividad post-cierre"** para proyectos con `status = implemented`, con `note_type = soporte_post_entrega`

### Dashboard
- Bloque **"Tiempo real"** con `st.metric`: Horas desarrollo / Horas post-cierre / Total real
- Consulta separa horas de desarrollo (antes de `closed_at`) vs. post-cierre (`soporte_post_entrega`)
- Si el proyecto no tiene horas, el bloque no se renderiza

---

## Criterios de éxito — verificados

- [x] El formulario no permite guardar sin horas
- [x] El backfill rechaza filas inválidas e imprime cuáles son
- [x] Proyectos `implemented` muestran sección de post-cierre
- [x] Dashboard muestra métricas con formato limpio `st.metric`
- [x] Migraciones idempotentes — no rompen datos existentes

---

## Notas de implementación

- `note_type = soporte_post_entrega` no aparece en las 4 tarjetas de "Últimas notas"; tiene sección propia
- El campo `closed_at` se ancla en el primer cambio a `implemented` y no se sobreescribe
- Los scripts de backfill permanecen en el repo para correcciones masivas futuras
