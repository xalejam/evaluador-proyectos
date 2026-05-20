# Team Workload — Diseño de Feature

**Fecha:** 2026-05-19
**Objetivo:** Registrar uno o más responsables por proyecto y visualizar la carga del equipo (proyectos activos + horas acumuladas) en el dashboard ejecutivo.

---

## Contexto y motivación

El sistema actualmente tiene `owner` (un solo responsable) y `delivery_team` (texto libre sin estructura) en la tabla `projects`. Ninguno de los dos permite agregar múltiples miembros de forma que se pueda sumar y comparar carga entre personas. Con el feature de `effort_hours` ya implementado, es natural agregar una capa de atribución de proyectos por persona para responder: ¿quién tiene cuántos proyectos y cuántas horas acumuladas?

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|---|---|---|
| Estructura de miembros | Tabla relacional `project_members` | Permite múltiples miembros por proyecto, consultas limpias, escalable a otros equipos |
| Distribución de horas | No se distribuyen entre miembros | La captura es grupal (una persona captura por el equipo); distribuir matemáticamente sería impreciso |
| Métrica de carga | Proyectos activos + horas totales del proyecto | Muestra volumen y esfuerzo sin suposiciones sobre tiempo individual |
| UI de gestión | Sección colapsable por proyecto | Consistente con el patrón de links/artifacts ya existente |
| Nombres de miembros | Texto libre con sugerencias de proyectos existentes | Evita over-engineering de un catálogo de usuarios para un equipo de 2-4 personas |

---

## Schema

### Nueva tabla: `project_members`

```sql
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    member_name TEXT NOT NULL,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, member_name)
)
```

- Migración idempotente vía `ensure_projects_schema` en `infra/db_migrations.py`
- La constraint `UNIQUE(project_id, member_name)` previene duplicados
- El campo `owner` existente en `projects` se mantiene sin cambios
- Índice: `idx_project_members_pid ON project_members(project_id)`

### Funciones nuevas en `infra/db_migrations.py`

```python
def ensure_members_schema(conn) -> None
def get_project_members(conn, project_id: str) -> list[str]
def add_project_member(conn, project_id: str, member_name: str) -> None
def remove_project_member(conn, project_id: str, member_name: str) -> None
def get_all_known_members(conn) -> list[str]  # para sugerencias
```

---

## UI — Gestión de miembros por proyecto

**Ubicación:** `ui/tabs/seguimiento_operativo.py`, dentro de `_render_capture_tab`, en el bloque de links/configuración del proyecto (sección colapsable existente).

**Componente nuevo:** `_render_members_section(conn, project)`

```
▸ Equipo del proyecto
  Ana  [×]   Xiomara  [×]
  [Agregar miembro ▼]  [+ Agregar]
```

**Comportamiento:**
- Muestra chips con nombre + botón de eliminar por cada miembro actual
- `st.selectbox` con opciones de nombres ya usados en otros proyectos + opción "Nuevo..."
- Al seleccionar "Nuevo...", aparece `st.text_input` para escribir el nombre
- Validaciones: nombre no vacío, no duplicado en el proyecto
- Persistencia inmediata (sin submit general del formulario)
- Confirmación inline antes de eliminar: `st.warning` con botón "Confirmar eliminación"

---

## UI — Dashboard de carga del equipo

**Ubicación:** `ui/tabs/seguimiento_operativo.py`, función `_render_executive_tab`, nueva sección al final de la página llamada "Carga del equipo".

**Query de datos:**

```sql
SELECT
    pm.member_name,
    p.project_id,
    p.name,
    p.status,
    COALESCE(SUM(pn.effort_hours), 0) AS total_hours
FROM project_members pm
JOIN projects p ON p.project_id = pm.project_id
LEFT JOIN project_notes pn ON pn.project_id = p.project_id
WHERE p.status IN (/* statuses del filtro actual */)
GROUP BY pm.member_name, p.project_id, p.name, p.status
ORDER BY pm.member_name, total_hours DESC
```

**Render por miembro:**

```
Xiomara
  Proyectos activos: 4    Horas acumuladas: 87 h
  ┌─────────────────────────────┬────────────┬────────┐
  │ Proyecto                    │ Status     │ Horas  │
  ├─────────────────────────────┼────────────┼────────┤
  │ Automatización reportes     │ executing  │ 34 h   │
  │ Dashboard ventas            │ executing  │ 28 h   │
  │ Auditoría datos             │ executing  │ 25 h   │
  │ Migración CRM               │ in_agenda  │  0 h   │
  └─────────────────────────────┴────────────┴────────┘
```

- Implementado con `st.metric` para las dos cifras resumen
- Tabla detalle con `st.dataframe` (sin edición)
- Un bloque por miembro, separados por `st.divider()`
- Si ningún proyecto tiene miembros asignados: `st.info("Aún no hay miembros asignados a proyectos.")`
- Respeta el filtro de status ya existente en `_render_executive_tab`

**Función nueva:** `get_workload_df(conn, statuses) -> pd.DataFrame`

---

## Archivos a modificar / crear

| Archivo | Acción |
|---|---|
| `infra/db_migrations.py` | Agregar `ensure_members_schema` y funciones CRUD de miembros |
| `ui/tabs/seguimiento_operativo.py` | Agregar `_render_members_section`, `get_workload_df`, y bloque en `_render_executive_tab` |
| `tests/unit/test_team_workload.py` | Tests de migraciones, CRUD, y query de carga |

---

## Tests

- `test_ensure_members_schema_creates_table` — migración idempotente
- `test_add_member_persists` — agregar miembro y recuperarlo
- `test_duplicate_member_ignored` — constraint UNIQUE no lanza excepción, se maneja
- `test_remove_member` — eliminar miembro
- `test_get_all_known_members_returns_unique_names` — sugerencias sin duplicados
- `test_workload_df_sums_hours_per_member` — query de carga agrega horas correctamente
- `test_workload_df_empty_when_no_members` — caso vacío sin error

---

## Captura de horas con múltiples colaboradores por semana

Cuando en una semana X dos personas trabajan en el mismo proyecto, **cada una captura su propia nota** con sus propias horas usando el campo `author` del formulario. El sistema ya lo soporta — múltiples notas del mismo proyecto con distinto `author` se suman correctamente en el dashboard porque `get_workload_df` agrega por `project_id`, no por `author`.

**Convención del equipo:** cualquier miembro listado en `project_members` puede (y debe) capturar su propia entrada semanal cuando trabaje en ese proyecto, independientemente de quién sea el `owner`.

No se requiere ningún cambio de schema ni de lógica para soportar este caso.

---

## Lo que NO se incluye (fuera de alcance)

- Roles por miembro (líder, analista, etc.) — no necesario para un equipo de 2-4 personas
- Distribución matemática de horas entre miembros — la captura es grupal por defecto
- Autenticación o catálogo de usuarios — nombres libres son suficientes para este contexto
- Historial de cambios de miembros — `added_at` guarda cuándo se agregó, pero no hay log de eliminaciones
