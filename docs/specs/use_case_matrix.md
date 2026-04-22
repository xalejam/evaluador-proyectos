# Use Case Matrix

## 1. Propósito

Visualiza el portafolio de proyectos como un scatter Impact vs. Effort dividido en cuadrantes, permitiendo priorización visual y cambio de estado. Es una vista de solo lectura — no crea proyectos ni captura evaluaciones directamente.

**Usuarios:** Líderes de portfolio y PMs para priorización estratégica.

---

## 2. Inputs

### Fuentes de datos
- `project_viability.db` → tabla `projects` (metadata, estado, viability_score) — **fuente de verdad**
- `data/projects.db` → tabla `evaluations` con `is_current=1` (impact_score, effort_score)
- `config/scoring_config.json` → thresholds de impacto y esfuerzo para los cuadrantes

### Parámetros del usuario (filtros)
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Año | selectbox | Filtra por año de `updated_at` del proyecto |
| Delivery team | multiselect | NOLA / SOLA / Brazil / Champions / Other |
| Estado | multiselect | Todos los estados válidos |
| Búsqueda | text_input | Filtra por nombre, owner o project_id |

### Acción disponible
- Cambio de estado de un proyecto seleccionado (selectbox + botón guardar)

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Scatter Impact vs Effort con cuadrantes | `px.scatter` | Central |
| Detalle del proyecto seleccionado | `st.write` + `st.link_button` | Panel derecho |
| Tabla filtrada del portafolio | `st.dataframe` | Abajo del scatter |
| Exportación CSV + JSON | `st.download_button` × 2 | Debajo de tabla |
| Cambio de estado (UPDATE) | `project_viability.db` + espejo en `data/projects.db` | Al guardar |

---

## 4. Lógica de negocio

### Cuadrantes
Los cuadrantes se definen por dos umbrales configurables (`scoring_config.json`):
```
threshold_impact  (default: ver config)
threshold_effort  (default: ver config)

Cuadrante "Quick Wins":   impact >= threshold AND effort < threshold
Cuadrante "Major":        impact >= threshold AND effort >= threshold
Cuadrante "Fill-ins":     impact < threshold  AND effort < threshold
Cuadrante "Thankless":    impact < threshold  AND effort >= threshold
```
Clasificación via `domain.matrix.classify_quadrant()`.

### Carga del portafolio (JOIN entre DBs)
```
1. Lee projects de project_viability.db
2. Lee evaluations (is_current=1) de data/projects.db
3. LEFT JOIN por project_id → proyectos sin evaluación tienen impact_score=NULL, effort_score=NULL
4. Calcula year desde updated_at (fallback a created_date, luego año actual)
```

### Proyectos sin scores en la matriz
Proyectos sin evaluación `current` en `data/projects.db` no aparecen en el scatter (se excluyen con `dropna(subset=["impact_score", "effort_score"])`), pero sí aparecen en la tabla de abajo.

### Cambio de estado
```
update_status(project_id, new_status):
  1. UPDATE projects SET status=? WHERE id=? OR project_id=?   → project_viability.db
  2. UPDATE projects SET status=?  WHERE project_id=?           → data/projects.db (si existe columna)
```
Actualiza ambas DBs para mantener consistencia.

### Paleta de colores por estado
```python
{
    "evaluated":   "#4e79a7",
    "backlog":     "#f28e2b",
    "on_hold":     "#edc948",
    "approved":    "#59a14f",
    "in_agenda":   "#59a14f",
    "executing":   "#76b7b2",
    "implemented": "#2ca02c",
    "rejected":    "#e15759",
    "handed_off":  "#9c755f",
}
```

---

## 5. Flujo funcional

1. Inicializa schema (migraciones idempotentes en ambas DBs)
2. Carga `base_df` con JOIN de portafolio + scores
3. Si portafolio vacío → info y exit
4. Usuario aplica filtros (año, equipo, estado, texto)
5. Renderiza scatter con puntos coloreados por estado, líneas de umbral
6. Usuario selecciona proyecto del selectbox
7. Panel derecho: detalle del proyecto + selectbox de nuevo estado + botón guardar
8. Tabla filtrada completa con botones de exportación

---

## 6. Queries / lógica de datos

### Carga de scores (data/projects.db)
```sql
SELECT e.project_id, e.impact_score, e.effort_score, e.created_at AS eval_created_at
FROM evaluations e
JOIN (
    SELECT project_id, MAX(created_at) AS max_created_at
    FROM evaluations
    WHERE is_current = 1
    GROUP BY project_id
) curr ON curr.project_id = e.project_id AND curr.max_created_at = e.created_at
WHERE e.is_current = 1
```

### Carga del portafolio (project_viability.db)
```sql
SELECT
    COALESCE(project_id, id) AS project_id,
    COALESCE(name, '') AS name,
    COALESCE(owner, '') AS owner,
    COALESCE(country, '') AS country,
    COALESCE(status, 'evaluated') AS status,
    COALESCE(delivery_team, '') AS delivery_team,
    COALESCE(loop_url, '') AS loop_url,
    COALESCE(updated_at, created_date, '') AS updated_at,
    COALESCE(viability_score, 0) AS score_total
FROM projects
WHERE COALESCE(project_id, id, '') <> ''
```
Fallback por nombre de columna: soporta schema legacy (`id`, `created_date`) y nuevo (`project_id`, `updated_at`).

### Actualización de estado
```sql
-- project_viability.db
UPDATE projects SET status=?, updated_at=datetime('now') WHERE id=? OR project_id=?

-- data/projects.db (espejo)
UPDATE projects SET status=? WHERE project_id=?
```

### Índices de soporte
```sql
idx_projects_project_id  ON projects(project_id)
idx_projects_status      ON projects(status)
idx_projects_updated_at  ON projects(updated_at)
idx_ucm_projects_status  ON data/projects.db projects(status)
idx_ucm_projects_year    ON data/projects.db projects(year)
```

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.columns([1,2,2,2])` filtros | Año / Equipo / Estado / Búsqueda |
| `px.scatter` | Matriz Impact vs Effort con cuadrantes |
| `add_vline` + `add_hline` | Líneas de umbral configurables |
| `st.selectbox` (proyecto) | Selección del proyecto a detallar |
| `st.write` × 6 | Detalle: ID, nombre, estado, team, scores, loop URL |
| `st.link_button` | Abrir Loop URL |
| `st.button` (Abrir en Viabilidad) | Redirige a tab Viabilidad en modo edición |
| `st.selectbox` + `st.button` | Cambiar y guardar estado |
| `st.dataframe` | Tabla filtrada del portafolio |
| `st.download_button` × 2 | Exportar CSV y JSON |

---

## 8. Dependencias

### Otras pestañas
- **Viabilidad**: es la única pestaña que crea proyectos y evaluaciones en esta matriz. Al guardar en Viabilidad → sincronización automática a `data/projects.db`.
- **Seguimiento Operativo**: puede cambiar el estado de un proyecto (via `/end`); la matriz refleja ese cambio en la próxima carga.
- El botón "Abrir en Viabilidad" escribe `selected_project_id` y `edit_mode` en `st.session_state`, que Viabilidad lee.

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `domain.matrix.classify_quadrant` | Clasifica cada punto en su cuadrante |
| `infra.config_loader.ConfigLoader` | Lee thresholds de impacto y esfuerzo |
| `infra.db` | Path y conexión a `data/projects.db` |
| `infra.db.connection.get_sqlite_conn` | Conexión a `project_viability.db` |
| `plotly.express` | Scatter de la matriz |

### DB
- `project_viability.db` (fuente de verdad para estado y metadata)
- `data/projects.db` (scores Impact/Effort de evaluaciones)

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Proyecto sin evaluación current | Aparece en tabla, NO en scatter |
| `data/projects.db` no existe | Scores NULL para todos → scatter vacío, tabla muestra proyectos sin score |
| Filtro de año sin resultados | Scatter vacío con info, tabla vacía |
| Cambio de estado en proyecto sin columna en espejo | Actualiza solo `project_viability.db`, ignora espejo silenciosamente |
| Score de esfuerzo fuera de rango [0.8, 5.2] | Punto no visible en el scatter (fuera de rango del eje) |
| `delivery_team` vacío | Muestra como "Sin equipo" (display label) en filtro |
| Umbral no configurado en JSON | Error al cargar `threshold_impact` / `threshold_effort` → falla toda la pestaña |

---

## 10. Performance

### Situación actual
- Dos conexiones a DBs distintas en cada carga del tab.
- No hay caché en ninguna función de lectura.
- El JOIN entre DataFrames se hace en pandas (en memoria) — aceptable para portfolios pequeños (<500 proyectos).

### Mejoras necesarias
- [ ] Cachear `_load_portfolio_df()` y `_load_current_scores_df()` con `st.cache_data(ttl=60)`.
- [ ] Para portfolios grandes, hacer el JOIN directamente en SQL con una DB attachada en lugar de en pandas.

---

## 11. Validación

- `VALID_STATUSES` define los estados permitidos para cambio — si un proyecto tiene status legacy no listado, se permite pero no aparece en el selectbox de cambio.
- Consistencia esperada: para cada `project_id` en `data/projects.db.evaluations`, debe existir exactamente una fila con `is_current=1`.

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2026-01 | Versión inicial de la matriz (scatter + tabla) | Xiomara |
| 2026-02 | Filtros de año, equipo y estado | Xiomara |
| 2026-03 | Cambio de estado desde la vista + espejo en ambas DBs | Xiomara |
| 2026-04 | Botón "Abrir en Viabilidad" + exportación CSV/JSON | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Impact score** (1–5): qué tan grande es el beneficio del use case (derivado de reducción de tiempo, alcance, frecuencia, valor de negocio).
- **Effort score** (1–5): qué tan difícil es implementarlo (derivado de complejidad, integraciones, riesgo, change management).
- Ambos scores se derivan automáticamente desde los inputs de Viabilidad — no son capturados directamente en esta pestaña.

### Supuestos
- El mapeo A-H desde Viabilidad hacia Impact/Effort es una aproximación — no fue validado estadísticamente.
- Los pesos de cada criterio (A-H) son configurables en `scoring_config.json` y por defecto son iguales (1.0).

### Limitaciones
- No hay historial visual de movimientos en el scatter — solo muestra el estado actual.
- No permite mover puntos manualmente ni sobrescribir scores.

### Mejoras futuras
- Agregar animación temporal (slider de fecha) para ver cómo evolucionó el portafolio.
- Permitir captura directa de scores A-H desde esta vista (sin pasar por Viabilidad).
- Mostrar el cuadrante de cada proyecto en la tabla de detalle.
