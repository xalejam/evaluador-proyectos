# Cierre: Team Workload — Miembros por proyecto y dashboard de carga

**Fecha de cierre:** 2026-05-20
**Spec:** `docs/superpowers/specs/2026-05-19-team-workload-design.md`
**Plan:** `docs/superpowers/plans/2026-05-19-team-workload.md`
**Estado:** Completo

---

## Commits entregados

| Hash | Descripción |
|---|---|
| `9573226` | docs: add spec for team workload feature (project_members + dashboard) |
| `e32c2ff` | docs: add implementation plan for team workload feature |
| `ad897aa` | feat: add project_members table with CRUD functions |
| `96c744d` | feat: add get_workload_df query for team workload dashboard |
| `fd6be31` | feat: add team members management section to project capture tab |
| `9b5c207` | feat: add Carga del equipo workload section to executive dashboard |

---

## Qué se implementó

### Schema — `infra/db_migrations.py`
- Nueva tabla `project_members` con `UNIQUE(project_id, member_name)` e índice por `project_id`
- Funciones CRUD: `ensure_members_schema`, `get_project_members`, `add_project_member`, `remove_project_member`, `get_all_known_members`
- `ensure_all_operational_schema` actualizado para incluir `ensure_members_schema`
- `ensure_members_schema` también llamado en el arranque del tab operativo

### UI — Gestión de miembros (`_render_members_section`)
- Sección colapsable **"Equipo del proyecto"** en Captura rápida, después del bloque de links
- Lista de miembros actuales con botón `✕` + confirmación inline antes de eliminar
- `st.selectbox` con sugerencias de nombres ya usados en otros proyectos + opción "Nuevo..."
- Persistencia inmediata sin necesidad de submit general del formulario

### Query — `get_workload_df`
- JOIN de `project_members` + `projects` + `project_notes` filtrando por status
- Devuelve `member_name`, `project_id`, `name`, `status`, `total_hours` (suma de `effort_hours`)
- Respeta el filtro de status del tab ejecutivo

### Dashboard — Bloque "Carga del equipo" (`_render_workload_section`)
- Agregado al final de `_render_executive_tab`, después del gráfico de avance por proyecto
- Un bloque por miembro con `st.metric` (proyectos activos + horas acumuladas) y tabla detalle
- Bloques separados por `st.divider()`
- Mensaje informativo si no hay miembros asignados aún

---

## Tests entregados (`tests/unit/test_team_workload.py`)

| Test | Qué verifica |
|---|---|
| `test_ensure_members_schema_creates_table` | La tabla se crea |
| `test_ensure_members_schema_is_idempotent` | Migración idempotente |
| `test_add_member_persists` | Agregar miembro y recuperarlo |
| `test_duplicate_member_is_ignored` | UNIQUE no lanza excepción |
| `test_remove_member` | Eliminar miembro, el otro queda |
| `test_get_project_members_returns_empty_list_for_unknown_project` | Caso vacío |
| `test_get_all_known_members_returns_unique_names` | Sugerencias sin duplicados |
| `test_workload_df_sums_hours_per_project` | Query suma horas correctamente |
| `test_workload_df_empty_when_no_members` | Proyecto sin miembros no aparece |
| `test_workload_df_filters_by_status` | Filtro de status funciona |

**Resultado final:** 76 tests pasando, 0 fallos.

---

## Decisiones de diseño aplicadas

- Horas no se distribuyen entre miembros — la captura es grupal, mostrar el total del proyecto por persona es suficiente
- Nombres libres con sugerencias — evita over-engineering de catálogo de usuarios para equipo pequeño
- El campo `owner` existente en `projects` se mantiene sin cambios — `project_members` es complementario, no reemplaza
