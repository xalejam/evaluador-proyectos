# Viabilidad

## 1. Propósito

Captura y evalúa la viabilidad de nuevos proyectos de automatización/reporte. Calcula un score 0–100, métricas financieras proyectadas y permite guardar o aprobar el proyecto hacia el pipeline.

**Usuarios:** Project managers que proponen proyectos (Worldpanel Developers).

---

## 2. Inputs

### Fuentes de datos
- `project_viability.db` → tabla `projects` (proyectos existentes, para modo edición)
- `st.session_state.excel_manager` → fuente legacy (ExcelSharePointManager)
- `config/scoring_config.json` → lista de países, pesos, thresholds

### Parámetros del usuario
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Nombre del proyecto | text_input | Requerido |
| País | selectbox | ISO2 (MX, BR, CO…) + regionales (LATAM, NOLA…) |
| Owner | text_input | Siglas del responsable, auto-uppercase |
| Tiempo por tarea (hrs) | number_input | Situación actual |
| Tareas por mes | number_input | Volumen actual |
| Número de personas | number_input | Personal afectado |
| Reducción de tiempo % | slider 0-100 | Estimado de mejora |
| Horas de desarrollo | number_input | (Opcional) |
| Costo/hora de desarrollo | selectbox + number_input | Escala de salarios o personalizado |
| Mantenimiento mensual | number_input | Costo recurrente post-lanzamiento |
| Complejidad | selectbox 1-5 | 1=mínimo, 5=máximo |
| Riesgo técnico | selectbox 1-5 | 1=mínimo, 5=máximo |
| Developer team | selectbox | NOLA / SOLA / Brazil / Champions Copilot / Other |
| Status al guardar | selectbox | evaluated / backlog / on_hold / rejected / handed_off |
| Autor (action owner) | text_input | Quién ejecuta la acción |

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Gauge de viabilidad (0–100) | `st.plotly_chart` | Panel derecho |
| Priority, Score, ROI, Ahorro mensual/anual | `st.metric` | Panel derecho |
| Recomendación textual | `st.info` | Panel derecho |
| Snapshot en `project_evaluations` | INSERT en DB | Al guardar/aprobar |
| Proyecto en `projects` | INSERT/UPDATE en DB | Al guardar/aprobar |
| Evaluación sincronizada en Use Case Matrix | upsert en `data/projects.db` | Automático al guardar |

---

## 4. Lógica de negocio

### Cálculo del viability_score (0–100)
```
score = impact_points(time_reduction_percent)
      + risk_points(risk_level)
      + complexity_points(implementation_complexity)

impact_points:
  time_reduction >= 70  → 35
  time_reduction >= 50  → 30
  time_reduction >= 30  → 25
  time_reduction >= 15  → 20
  time_reduction >= 5   → 15
  else                  → max(0, time_reduction * 0.5)

risk_points:
  {1: 30, 2: 24, 3: 18, 4: 12, 5: 6}

complexity_points:
  {1: 35, 2: 28, 3: 21, 4: 14, 5: 7}
```

### Métricas financieras
```
hours_saved_per_month   = time_per_task * time_reduction% * tasks_per_month * staff_count
monthly_savings         = hours_saved_per_month * avg_salary_per_hour
annual_savings          = monthly_savings * 12
initial_dev_cost        = development_hours * development_cost_per_hour
payback_period_months   = initial_dev_cost / (monthly_savings - maintenance_monthly)
                          → None si denominador <= 0
roi_first_year          = (annual_savings - initial_dev_cost - maintenance_monthly*12)
                          / initial_dev_cost * 100
                          → None si initial_dev_cost = 0
```

### Botones de acción
| Botón | Acción | Status resultante |
|-------|--------|------------------|
| Calcular | Solo muestra resultados en UI, no persiste | — |
| Guardar Evaluación | Persiste + snapshot + sync a matriz | Elegido por usuario |
| Aprobar → Agenda | Persiste + snapshot; fuerza `approved` salvo si ya estaba en executing/implemented/handed_off | `approved` |

### Generación de project_id
```
format: {COUNTRY}-{OWNER}-{NNNN}
example: MX-CARLOS-0007
```
Generado por `ProjectViabilityCalculator.create_project()` en `shared.py`.

### Sincronización automática a Use Case Matrix
Al guardar/aprobar → `sync_to_use_case_matrix()`:
- Deriva answers A-H a partir de inputs (mapeo por umbrales)
- Calcula `impact_score` / `effort_score`
- Upsert de proyecto y evaluación `current` en `data/projects.db`

### Derivación de respuestas A-H (para Use Case Matrix)
```
A (ahorro tiempo):     time_reduction_percent → thresholds [5, 15, 30, 50]
B (alcance):           staff_count → thresholds [1, 2, 4, 7]
C (frecuencia):        tasks_per_month → thresholds [5, 20, 50, 100]
D (valor negocio):     annual_savings → thresholds [1000, 5000, 20000, 100000]
E (complejidad):       implementation_complexity (1-5 directo)
F (integraciones):     development_hours → thresholds [20, 80, 160, 320]
G (dependencias):      risk_level (1-5 directo)
H (change mgmt):       staff_count → thresholds [2, 5, 10, 20]
```

---

## 5. Flujo funcional

1. Al abrir tab: ejecuta migraciones idempotentes (`ensure_projects_schema`, `ensure_evaluations_schema`)
2. Barra superior muestra: Project ID, status actual, score actual, Loop URL
3. Modo **nuevo**: formulario en blanco
4. Modo **edición**: botón "Buscar/Editar" → selectbox de proyectos existentes → botón "Editar" carga datos
5. Usuario llena formulario (columna izquierda)
6. Click **Calcular** → calcula y muestra resultados en columna derecha (temporal, no persiste)
7. Click **Guardar** o **Aprobar**:
   - Calcula (con o sin resultados previos)
   - Persiste en DB + inserta snapshot en `project_evaluations`
   - Sincroniza a Use Case Matrix
   - Muestra éxito con Project ID
8. Columna derecha: gauge + métricas + recomendación

---

## 6. Queries / lógica de datos

### Tablas escritas
```sql
-- projects (insert o update)
UPDATE projects SET status=?, updated_at=datetime('now'), project_id=?, loop_url=?, developer_team=?
WHERE id = ?

-- project_evaluations (snapshot inmutable)
INSERT INTO project_evaluations (
    project_id, created_by, action, status_after,
    score_total, score_impact, score_risk, score_complexity,
    monthly_savings, annual_savings, payback_period_months, roi_first_year,
    hours_saved_per_month, inputs_json
) VALUES (...)
```

### Tablas leídas
```sql
-- Lista de proyectos para modo edición
SELECT * FROM projects  -- via excel_manager.get_all_projects()

-- Promedio de tarifa horaria (para default del formulario)
AVG(avg_salary_per_hour) FROM projects
```

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.columns([2,1,1,2])` barra superior | ID, status, score, loop link |
| `st.columns(3)` botones de modo | Nuevo / Buscar-Editar / Cancelar |
| `st.selectbox` (edición) | Selección de proyecto a editar |
| `st.text_input` | Nombre, owner |
| `st.selectbox` | País |
| `st.number_input` × 4 | time, tasks, staff, development_hours |
| `st.slider` | Reducción de tiempo % |
| `st.expander` | Detalles opcionales (descripción, costos, complexity, risk) |
| `st.selectbox` | Status al guardar, developer_team |
| `st.columns(3)` botones | Calcular / Guardar / Aprobar |
| `go.Indicator` gauge | Score de viabilidad |
| `st.metric` × 6 | Priority, Score, Time reduction, Savings, ROI |
| `st.info` | Recomendación textual |

---

## 8. Dependencias

### Otras pestañas
- **Use Case Matrix**: sincronización automática al guardar/aprobar
- **Dashboard**: lee proyectos guardados aquí para mostrar KPIs

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `domain.scoring.calculate_scores` | Calcula impact_score / effort_score para matriz |
| `infra.config_loader.ConfigLoader` | Lee countries, weights, thresholds de config JSON |
| `infra.repositories.ProjectRepository` | Upsert en `data/projects.db` |
| `infra.repositories.EvaluationRepository` | `save_current()` en evaluations |
| `infra.db.connection.get_sqlite_conn` | Conexión a `project_viability.db` |
| `ui.tabs.shared.ProjectViabilityCalculator` | Cálculos financieros y persistencia legacy |
| `ui.tabs.shared.ExcelSharePointManager` | Acceso a proyectos via session_state |

### DB
- `project_viability.db` (fuente principal)
- `data/projects.db` (espejo para Use Case Matrix)

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Nombre o owner vacío | Bloqueo con `st.error` |
| Calcular sin guardar → navegar otra tab | Resultados se pierden (`temp_calculation` en session_state) |
| Guardar sin calcular primero | Recalcula automáticamente antes de persistir |
| `maintenance_monthly >= monthly_savings` | `payback_period_months = None` (denominador ≤ 0) |
| `development_hours = 0` | `roi_first_year = None` (división por cero) |
| Project ID ya existente en modo nuevo | [VERIFICAR] `excel_manager` determina si crea o actualiza |
| Aprobar proyecto ya en `executing` | Respeta el estado actual, no regresa a `approved` |
| Config sin países definidos | Usa lista base hardcodeada de 14 países |

---

## 10. Performance

### Situación actual
- `calculate_average_hourly_rate()` carga todos los proyectos en cada render del tab.
- `sync_to_use_case_matrix()` ejecuta upserts síncronos al guardar — puede percibirse lento si la DB está en red.
- No hay `st.cache_data` en lecturas de proyectos.

### Mejoras necesarias
- [ ] Cachear `calculate_average_hourly_rate()` con `st.cache_data(ttl=300)`.
- [ ] Ejecutar `sync_to_use_case_matrix()` de forma asíncrona o en background thread para no bloquear el guardado.

---

## 11. Validación

### Checks actuales
- `project_name != ""` → bloqueo
- `project_owner != ""` → bloqueo
- Sin validación de formato del owner (ej. caracteres especiales)

### Ejemplos esperados
```
Input:  time_reduction=50%, risk=2, complexity=3
Output: score = 30 + 24 + 21 = 75/100 → prioridad "Alta"

Input:  time_reduction=10%, risk=4, complexity=4
Output: score = 20 + 12 + 14 = 46/100 → prioridad "Media"
```

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2025-Q4 | Versión inicial | Xiomara |
| 2026-01 | Separación de botones Calcular / Guardar | Xiomara |
| 2026-02 | Sincronización automática a Use Case Matrix | Xiomara |
| 2026-03 | Agrega `project_evaluations` snapshot + developer_team | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Proyectadas / estimadas**: todos los outputs son proyecciones basadas en inputs del usuario, no datos reales.
- El `viability_score` es una heurística de 3 factores (impacto, riesgo, complejidad), no un modelo estadístico.

### Supuestos
- La `avg_salary_per_hour` se toma como promedio del portafolio existente. Para proyectos nuevos sin referencia, se usa $25/hr como default.
- El `time_reduction_percent` es estimado por el proponente — no hay validación externa.
- La ventana de ROI es siempre el primer año.

### Limitaciones
- El score máximo teórico es 35 + 30 + 35 = 100, pero requiere reducción ≥70%, riesgo=1, complejidad=1 simultáneamente.
- No considera externalidades (cambio organizacional, capacitación, licencias de software).

### Mejoras futuras
- Agregar campo de `adoption_rate` estimada en el formulario de planificación para usarla en proyecciones de ahorro real.
- Permitir configurar la función de scoring por país/región desde `scoring_config.json`.
- Agregar validación de formato de `project_owner` (solo alfanumérico, sin espacios).
