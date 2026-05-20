# Spec: Registro de Horas de Esfuerzo por Ciclo de Vida del Proyecto

**Fecha:** 2026-05-19
**Estado:** Aprobado

---

## Contexto

Hoy el sistema captura notas operativas semanales (status, próximos pasos, bloqueadores, riesgos) pero no registra cuántas horas se invierten por proyecto en cada semana. Tampoco existe mecanismo para registrar actividad post-cierre.

Esto impide calcular el tiempo real total invertido en un proyecto a lo largo de su ciclo de vida completo.

---

## Objetivo

Permitir registrar horas de esfuerzo en cada entrada de nota operativa, tanto durante el desarrollo activo como en actividades post-cierre (solicitudes que llegan después de que el proyecto fue entregado). El resultado final es una métrica de **"Tiempo real"** visible en el dashboard por proyecto.

---

## Alcance

### Dentro del scope
- Campo `effort_hours` obligatorio en captura semanal y en notas post-cierre
- Nuevo `note_type`: `soporte_post_entrega`
- Campo `closed_at` en `projects` para anclar la separación desarrollo/post-cierre
- Scripts de backfill histórico (export CSV + import CSV)
- Bloque de métricas "Tiempo real" en el dashboard

### Fuera del scope
- Reportes de horas por persona / equipo
- Integración con herramientas externas de timetracking
- Alertas o presupuestos de horas

---

## Sección 1: Schema

### `project_notes` — campo nuevo

```sql
ALTER TABLE project_notes ADD COLUMN effort_hours REAL;
```

- Nullable en BD para compatibilidad con historial existente.
- Obligatorio en UI y en scripts de importación (ver Sección 2).
- Solo la nota de tipo `general` dentro de un `entry_group_id` lleva `effort_hours` para las entradas de seguimiento semanal — evita multiplicar horas por los 4 tipos del mismo corte.
- Las notas `soporte_post_entrega` llevan su propio `effort_hours` independiente.

### `projects` — campo nuevo

```sql
ALTER TABLE projects ADD COLUMN closed_at DATETIME;
```

- Se llena automáticamente la primera vez que `status` cambia a `implemented`.
- Nullable: proyectos activos no tienen `closed_at`.
- Sirve como ancla temporal para clasificar horas: `created_at <= closed_at` → desarrollo; `note_type = 'soporte_post_entrega'` → post-cierre.

### Nuevo `note_type`: `soporte_post_entrega`

Se agrega al catálogo de tipos válidos para inserción, pero **separado** de `NOTE_TYPES` que gobierna las 4 tarjetas de "Últimas notas":

```python
NOTE_TYPES = ("general", "proximo_paso", "bloqueador", "riesgo")      # tarjetas + validación seguimiento normal
POST_CLOSURE_TYPE = "soporte_post_entrega"                             # validación + sección independiente
```

`POST_CLOSURE_TYPE` solo aparece en la sección **"Registrar actividad post-cierre"**, que se renderiza únicamente cuando `status = 'implemented'`. No aparece en las 4 tarjetas de "Últimas notas".

### Migración

Ambos `ALTER TABLE` son idempotentes — se ejecutan con `_add_column_if_missing()` ya existente en `db_migrations.py`. Sin pérdida de datos.

---

## Sección 2: Backfill histórico (una sola vez)

### `scripts/export_notes_for_hours.py`

Genera `notas_horas.csv` con todas las notas que tienen `effort_hours IS NULL`:

| Columna | Descripción |
|---|---|
| `note_id` | Llave primaria — no modificar |
| `project_id` | Referencia del proyecto |
| `note_type` | Tipo de nota |
| `note_title` | Título del corte |
| `created_at` | Fecha de la nota |
| `note_text` | Texto (solo lectura, para contexto) |
| `effort_hours` | **Llenar — obligatorio** |

### `scripts/import_notes_hours.py`

Lee el CSV y ejecuta `UPDATE project_notes SET effort_hours = ? WHERE note_id = ?`.

**Validaciones:**
- `note_id` debe existir en la BD — filas inválidas se rechazan con error.
- `effort_hours` debe ser un número positivo mayor a 0 — filas con valor vacío, 0 o negativo se rechazan e imprimen para corrección.
- No modifica ningún otro campo.

**Output:**
```
Actualizadas: 143 notas
Rechazadas:    12 notas (effort_hours faltante o inválido)
  → note_id 45: MX-DDD-0001 | Seguimiento 2026-03-05 | effort_hours vacío
  → note_id 67: HI-DDD-0001 | Seguimiento 2026-03-12 | effort_hours = 0
```

**Flujo completo:**
```bash
python scripts/export_notes_for_hours.py        # genera notas_horas.csv
# abrir en Excel, llenar columna effort_hours, guardar
python scripts/import_notes_hours.py notas_horas.csv
```

Los scripts permanecen en el repo para correcciones masivas futuras.

---

## Sección 3: Captura semanal (flujo ongoing)

### Campo de horas en Captura rápida

Se agrega al formulario existente en `ui/tabs/seguimiento_operativo.py`:

- **Input:** `st.number_input("Horas invertidas esta semana", min_value=0.5, max_value=80.0, step=0.5)`
- **Obligatorio:** el botón Guardar está deshabilitado si `effort_hours` es 0 o no se ha tocado.
- **Posición:** justo antes del botón Guardar, después del campo de progreso.
- **Almacenamiento:** se guarda en la nota `general` del grupo (`entry_group_id`). Las notas `proximo_paso`, `bloqueador` y `riesgo` del mismo corte tienen `effort_hours = NULL`.

### Captura de nota `soporte_post_entrega`

Para proyectos con `status = 'implemented'`:

- Aparece una sección adicional **"Registrar actividad post-cierre"** debajo del formulario principal.
- Campos: descripción de la actividad (`note_text` obligatorio) + horas (`effort_hours` obligatorio).
- Se guarda como una nota independiente con `note_type = 'soporte_post_entrega'` y su propio `entry_group_id`.
- No comparte `entry_group_id` con las notas de seguimiento normal.

### Trigger `closed_at`

En la función que persiste el cambio de status a `implemented` (vía `/end` en bitácora), se agrega:

```python
if new_status == "implemented" and project.closed_at is None:
    project.closed_at = datetime.utcnow()
```

---

## Sección 4: Dashboard — métricas de tiempo real

### Consulta

```sql
SELECT
    p.project_id,
    SUM(CASE
        WHEN pn.note_type != 'soporte_post_entrega'
         AND (p.closed_at IS NULL OR datetime(pn.created_at) <= datetime(p.closed_at))
        THEN pn.effort_hours ELSE 0
    END) AS dev_hours,
    SUM(CASE
        WHEN pn.note_type = 'soporte_post_entrega'
        THEN pn.effort_hours ELSE 0
    END) AS post_hours
FROM projects p
LEFT JOIN project_notes pn ON pn.project_id = p.project_id
GROUP BY p.project_id
```

### UI

Bloque **"Tiempo real"** en la tarjeta del proyecto, usando `st.metric()` en columnas:

```
[ Horas desarrollo ]  [ Horas post-cierre ]  [ Total real ]
      143.5 h               12.0 h              155.5 h
```

- Si `post_hours = 0`, solo se muestran dos columnas (desarrollo + total).
- Si el proyecto no tiene ninguna hora registrada, el bloque no se renderiza.
- Formato limpio: número con una decimal + unidad `h`. Sin decimales extra ni texto adicional.

---

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `infra/db_migrations.py` | Agregar `effort_hours` y `closed_at` vía `_add_column_if_missing` |
| `infra/db/migrations.py` | Exponer nuevas migraciones |
| `ui/tabs/seguimiento_operativo.py` | Campo horas en formulario, sección post-cierre, bloque dashboard |
| `domain/models.py` | Sin cambios — las notas viven en `project_viability.db`, fuera del ORM SQLAlchemy |
| `scripts/export_notes_for_hours.py` | Nuevo |
| `scripts/import_notes_hours.py` | Nuevo |

---

## Criterios de éxito

1. El formulario de Captura rápida no permite guardar sin horas.
2. El backfill rechaza filas con horas vacías o en cero e imprime cuáles son.
3. Proyectos con `status = implemented` muestran la sección de post-cierre.
4. El dashboard muestra el bloque "Tiempo real" con formato `st.metric()` limpio.
5. Las migraciones son idempotentes y no rompen datos existentes.
