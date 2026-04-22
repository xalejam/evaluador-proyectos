# Seguimiento Operativo

## 1. Propósito

Permite registrar el avance operativo de proyectos en ejecución mediante notas inmutables, cambios de estado automáticos y un resumen ejecutivo consolidado.

**Usuarios:** Project managers y responsables de proyectos (Worldpanel Developers).

---

## 2. Inputs

### Fuentes de datos
- `project_viability.db` → tabla `projects` (proyectos y su estado actual)
- `project_viability.db` → tabla `project_notes` (historial inmutable de notas)
- Vistas derivadas: `v_project_latest_notes`, `v_project_last_note`, `v_project_progress_history`

### Parámetros del usuario
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Proyecto | selectbox | Selección del proyecto activo |
| Estados incluidos | multiselect | Filtro de estados visibles |
| Autor | text_input | Quién registra la nota |
| Nota general | text_area | Actualización libre; acepta `/end` como comando |
| Próximo paso | text_area | Acción concreta con responsable y fecha |
| Bloqueador | text_area | Impedimento activo |
| Riesgo | text_area | Riesgo identificado |
| % Avance | number_input | 0–100, opcional |
| Fecha estimada de fin | date_input | Calcula sugerencia de avance automáticamente |
| Loop URL | text_input | Requerido para guardar |
| Repo URL | text_input | Opcional |
| Artifacts URL + tipo | text_input + selectbox | Opcional |
| Tech stack | selectbox | python / vba / powerbi / agent / other |

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Notas insertadas | Filas en `project_notes` | DB |
| Cambio de estado del proyecto | UPDATE en `projects` | DB |
| Tarjetas de última nota por tipo | UI (4 columnas) | Sub-tab Captura |
| Resumen ejecutivo | `st.dataframe` | Sub-tab Resumen |
| Gráfico comparativo de avance | `st.line_chart` | Sub-tab Resumen |
| Exportación | CSV + JSON | Botones de descarga |

---

## 4. Lógica de negocio

### Notas inmutables
- Las notas **nunca se editan ni eliminan**. Solo se insertan (`INSERT`).
- Cada guardado genera un `entry_group_id` (UUID hex) que agrupa las notas del mismo momento.

### Tipos de nota válidos
`general` | `proximo_paso` | `bloqueador` | `riesgo`

Solo se insertan tipos con texto no vacío.

### Transiciones automáticas de estado
```
SI "/end" en nota general (case-insensitive)
    → status = "implemented"

SI es primera nota del proyecto
   AND status actual IN (evaluated, approved, in_agenda)
    → status = "executing"

ELSE → sin cambio de estado
```

### Validaciones de guardado
```
author != ""          → bloqueo con error
loop_url != ""        → bloqueo con error
progress_percent IN [0, 100]  → error si viola rango
```

### Progreso automático sugerido
```
SI estimated_end_date <= hoy → suggested = 100%
SI estimated_end_date > hoy:
    total_days = 120
    elapsed = total_days - (estimated_end_date - hoy).days
    suggested = max(0, min(100, round(elapsed / total_days * 100)))
```

### Executive summary — cálculos
- `Days since last`: días desde `last_note_at` hasta hoy. Si NULL → 99999 (aparece al final).
- `Progress Trend`:
  - ↑ si último valor > penúltimo
  - ↓ si último valor < penúltimo
  - → si igual o solo 1 punto
- `Progress Delta`: `last[0] - last[1]` (puede ser negativo)
- Ordenamiento: más días sin actualizar primero, luego alfabético por nombre.

---

## 5. Flujo funcional

La pestaña tiene **3 sub-tabs**:

### Sub-tab A — Captura Rápida
1. Usuario selecciona estados a incluir (multiselect)
2. Usuario selecciona proyecto del selectbox
3. Se muestra: estado actual, fecha última actualización, % de avance previo, links (Loop/Repo/Artifacts)
4. Si faltan links → botón "Configurar links" abre expander de edición
5. Usuario llena formulario de notas + % avance + fecha estimada
6. Al guardar:
   - Valida author y loop_url
   - Genera `entry_group_id`
   - Inserta notas no vacías en batch
   - Evalúa transición de estado (`/end` o primera entrada)
   - Muestra confirmación y hace `st.rerun()`
7. Se renderizan tarjetas de última nota por tipo (4 columnas)

### Sub-tab B — Resumen Ejecutivo
1. Usuario filtra por estados, texto libre y días sin actualización
2. Se construye DataFrame con 1 fila por proyecto (JOIN con vistas)
3. Se renderiza `st.dataframe` con columnas configuradas
4. Botones de exportación CSV/JSON
5. Gráfico de líneas comparativo de avance por proyecto

### Sub-tab C — Historial / Timeline
1. Usuario selecciona proyecto
2. Aplica filtros: texto, tipo de nota, rango de fechas, límite de filas
3. Se renderizan tarjetas agrupadas por `entry_group_id`
4. Vista global (todos los proyectos) con los mismos filtros debajo

---

## 6. Queries / lógica de datos

### Vista `v_project_latest_notes`
Última nota por `(project_id, note_type)`.
```sql
ROW_NUMBER() OVER (PARTITION BY project_id, note_type ORDER BY created_at DESC, note_id DESC) = 1
```
Fallback sin window functions: `JOIN` con `MAX(created_at)` + `MAX(note_id)`.

### Vista `v_project_last_note`
Última nota global por `project_id` (sin discriminar tipo).

### Vista `v_project_progress_history`
Entradas con `progress_percent IS NOT NULL`, deduplicadas por `entry_group_id`.
```sql
ROW_NUMBER() OVER (PARTITION BY project_id, COALESCE(NULLIF(entry_group_id,''), CAST(note_id AS TEXT)) ORDER BY note_id ASC) = 1
```

### Query del resumen ejecutivo
```sql
SELECT p.*, gg.note_text, ln.note_text, pp.note_text, bb.note_text, rr.note_text, ph.progress_percent
FROM projects p
LEFT JOIN v_project_last_note ln ON ln.project_id = p.project_id
LEFT JOIN v_project_latest_notes gg ON gg.project_id = p.project_id AND gg.note_type = 'general'
LEFT JOIN v_project_latest_notes pp ON ... note_type = 'proximo_paso'
LEFT JOIN v_project_latest_notes bb ON ... note_type = 'bloqueador'
LEFT JOIN v_project_latest_notes rr ON ... note_type = 'riesgo'
LEFT JOIN (último progress por proyecto) ph ON ph.project_id = p.project_id
WHERE p.status IN (?)
```

### Query de filtrado de notas (timeline)
```sql
SELECT * FROM project_notes
WHERE [project_id = ?] AND [note_text/note_title LIKE ?] AND [tags LIKE ?]
  AND [note_type = ?] AND [date(created_at) BETWEEN ? AND ?]
ORDER BY created_at DESC, note_id DESC
LIMIT ?
```

### Índices en `project_notes`
```sql
idx_project_notes_pid_date        (project_id, created_at DESC)
idx_project_notes_pid_type_date   (project_id, note_type, created_at DESC)
idx_project_notes_type            (note_type)
idx_project_notes_tags            (tags)
```

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.tabs` (3) | Captura / Resumen / Historial |
| `st.multiselect` | Filtro de estados del proyecto |
| `st.selectbox` (proyecto) | Selección del proyecto activo |
| `st.columns([1,1,2])` | Info rápida: estado, última actualización, loop link |
| `st.expander` (links) | Configuración de URLs del proyecto |
| `st.form` | Captura de notas (clear_on_submit=True) |
| `st.text_area` × 4 | Notas por tipo |
| `st.number_input` (0–100) | % de avance |
| `st.date_input` | Fecha estimada de fin |
| `st.checkbox` | Habilitar/deshabilitar captura de progreso |
| `st.columns(4)` | Tarjetas de última nota por tipo |
| `st.dataframe` | Resumen ejecutivo con column_config |
| `st.line_chart` | Comparativo de avance por proyecto |
| `st.download_button` × 2 | Exportar CSV y JSON |
| `st.link_button` | Abrir Loop / Repo / Artifacts |

---

## 8. Dependencias

### Otras pestañas
- Ninguna dependencia directa de estado compartido con otras tabs.
- Los proyectos que aparecen aquí son creados/editados en **Viabilidad** (tab 1).

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `infra.db.connection.get_sqlite_conn` | Conexión a SQLite |
| `ui.tabs.shared.t()` | Traducciones i18n (ES/EN) |
| `ui.i18n_labels.label_note_type` | Etiqueta legible de tipo de nota |
| `ui.i18n_labels.label_status` | Etiqueta legible de estado |
| `pandas` | DataFrames y queries con `read_sql_query` |
| `sqlite3` | Fallback de conexión y migraciones |
| `uuid` | Generación de `entry_group_id` |

### DB
- `project_viability.db` (SQLite)

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Proyecto sin notas previas | `is_first_entry = True` → auto-transición a `executing` si aplica |
| Todos los campos de nota vacíos | Warning "no hay contenido que guardar", no inserta nada |
| `loop_url` vacío | Bloqueo de guardado con error |
| `author` vacío | Bloqueo de guardado con error |
| `progress_percent` fuera de [0, 100] | `ValueError` capturado, error en UI |
| `estimated_end_date` <= hoy | `suggested_progress = 100%` |
| `/end` en nota general (mayúsculas) | Detectado (lower() antes de check) → `implemented` |
| SQLite sin soporte de window functions | Fallback con `MAX(created_at)` + subquery |
| Proyectos sin notas → resumen ejecutivo | `Days since last = 99999`, aparece al fondo |
| `progress_percent = NULL` en nota | Se omite del historial de progreso |

---

## 10. Performance

### Situación actual
- Índices cubrientes en `project_notes` para los patrones de consulta más frecuentes.
- El resumen ejecutivo hace **N queries adicionales** de `get_project_progress_trend()` (una por proyecto), ejecutadas en un loop Python.
- No hay `st.cache_data` en ninguna función de lectura.

### Mejoras necesarias
- [ ] Cachear `get_executive_summary_df()` con `st.cache_data(ttl=60)` para evitar re-queries en cada interacción del usuario.
- [ ] Consolidar las N queries de progress_trend en una sola query con window function sobre `v_project_progress_history`.
- [ ] Considerar paginación en el resumen ejecutivo si el número de proyectos supera ~50.

---

## 11. Validación

### Checks en guardado
- `author` no vacío
- `loop_url` no vacío
- `progress_percent` en [0, 100] si se provee
- Al menos 1 nota con texto no vacío

### Consistencia esperada
- Cada `entry_group_id` debe tener entre 1 y 4 notas (una por tipo).
- Una nota con `progress_percent` reportado en el resumen debe coincidir con el último valor en `v_project_progress_history`.
- Un proyecto con `/end` guardado debe tener `status = 'implemented'` en `projects`.

### Ejemplo esperado
```
Input:  general = "Entregamos resultado final /end", project = MX-XIO-0001
Output: 1 nota insertada (type=general), status MX-XIO-0001 → "implemented"
```

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2026-01 | Versión inicial v2 con notas inmutables | Xiomara |
| 2026-02 | Agrega `progress_percent` y `estimated_end_date` | Xiomara |
| 2026-03 | Agrega comparativo de avance (line chart) en resumen ejecutivo | Xiomara |
| 2026-04 | Agrega links (repo_url, artifacts_url, tech_stack) | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Descriptivas / operativas**: estado del proyecto en tiempo real, días sin actualización, % de avance reportado.
- No hay métricas predictivas actualmente.

### Supuestos
- El `progress_percent` es **auto-reportado** por el responsable, no calculado automáticamente (salvo la sugerencia basada en `estimated_end_date` con ventana de 120 días).
- "Días sin actualización" mide la frecuencia de uso de la herramienta, no necesariamente el avance real del proyecto.

### Limitaciones
- No hay control de acceso: cualquier usuario puede registrar notas en cualquier proyecto.
- `progress_percent` puede ser inconsistente si diferentes autores reportan valores no coordinados.
- La ventana de 120 días para `calculate_auto_progress` es fija en código, no configurable.

### Mejoras futuras (próxima fase)

#### Email de seguimiento post-cierre
Al guardar `/end` en un proyecto, programar un correo automático que se envíe de **1 mes a 3 meses después** de la fecha de cierre con una encuesta de evaluación del impacto real.

**Diseño sugerido:**
```
Trigger:   status → "implemented" (evento de cierre)
Acción:    registrar en tabla `scheduled_emails`:
           - project_id
           - recipient_email (owner del proyecto)
           - send_at: fecha_cierre + 30 días  (primer correo)
           - send_at: fecha_cierre + 90 días  (segundo correo)
           - template: "post_impl_survey"
           - status: "pending"

Ejecución: proceso externo (cron / Azure Function) consulta
           scheduled_emails WHERE send_at <= NOW() AND status = 'pending'
           → envía correo con link a encuesta
           → marca status = 'sent'
```

**Dependencias a resolver:**
- Definir proveedor de email (SMTP, SendGrid, Microsoft Graph API)
- Definir link/formulario de encuesta (Microsoft Forms)
- Decidir si el cron corre en la misma máquina o en Azure
