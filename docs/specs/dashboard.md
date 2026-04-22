# Dashboard

## 1. Propósito

Vista general del portafolio de proyectos. Consolida KPIs, distribuciones, análisis de factores y comparativo esperado vs. real cuando hay tracking disponible. Es la única pestaña de solo lectura de alto nivel.

**Usuarios:** Líderes y PMs que necesitan visibilidad del estado general del portafolio.

---

## 2. Inputs

### Fuentes de datos
- `st.session_state.excel_manager.get_all_projects()` → todos los proyectos (sin filtro de status)
- `st.session_state.excel_manager.tracking_df` → DataFrame de tracking para métricas post-impl

### Parámetros del usuario
Ninguno — el dashboard es completamente automático y no tiene filtros de usuario en la versión actual.

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| KPIs generales | `st.metric` × 4 | Fila superior |
| Histograma de viability scores | `px.histogram` | Columna izquierda |
| Pie de distribución de prioridades | `px.pie` | Columna derecha |
| Scatter ROI vs Score (si ≥2 proyectos) | `px.scatter` | Centro |
| Barras de complejidad y riesgo | `px.bar` × 2 | Fila inferior |
| Tabla estilizada de todos los proyectos | `st.dataframe` | Abajo de gráficos |
| Métricas de tracking (si existe) | `st.metric` × 4 | Sección adicional |
| Scatter score inicial vs performance real | `px.scatter` | Con línea de referencia |
| Insights automáticos | `st.info` | Final |
| Exportación a Excel | `st.download_button` | Final |

---

## 4. Lógica de negocio

### KPIs generales
```
total_projects  = len(projects)
avg_viability   = mean(viability_score for p in projects)
total_savings   = sum(annual_savings for p in projects)
high_priority   = count(p where priority == t('priority_high'))
```

### Métricas de tracking (cuando `tracking_df` no está vacío)
```
avg_performance = mean(performance_score)
avg_efficiency  = mean(efficiency_ratio)
avg_adoption    = mean(adoption_rate)
avg_satisfaction = mean(user_satisfaction_score)
```

### Gráfico scatter score_inicial vs performance_real
- X: `viability_score` (al momento de evaluación)
- Y: `performance_score` (tracking real)
- Tamaño del punto: `efficiency_ratio`
- Línea roja diagonal (referencia 1:1): puntos encima → superó expectativas

### Insights automáticos
```
SI high_score_projects / total > 50%  → "Portafolio sólido"
SI high_complexity / total > 30%      → "Alto porcentaje de proyectos complejos — revisar recursos"
SI hay proyectos con ROI > 100%       → "Excelente ROI: N proyectos con ROI > 100%"
SI successful_implementations / len(tracking) > 70% → "Implementaciones exitosas"
```
Donde:
- `high_score_projects`: `viability_score >= 80`
- `high_complexity`: `implementation_complexity >= 4`
- `successful_implementations`: `performance_score >= 80`

### Colores por prioridad
```python
{
    priority_high:        '#00CC96',
    priority_medium_high: '#00B8D4',
    priority_medium:      '#FFA726',
    priority_low:         '#FF6B6B'
}
```

---

## 5. Flujo funcional

1. Carga todos los proyectos — si ninguno → warning y exit
2. Calcula KPIs generales (4 métricas superiores)
3. Renderiza gráficos principales en 2 columnas (histograma + pie)
4. Scatter ROI vs Score (si `len(projects) > 1`)
5. Análisis de factores: barras de complejidad y riesgo
6. Tabla detallada con filas coloreadas por prioridad
7. Si `len(tracking_df) > 0`: métricas de tracking + scatter inicial vs real
8. Insights automáticos
9. Botón de exportación a Excel

---

## 6. Queries / lógica de datos

```python
# Lectura principal — via ExcelSharePointManager
projects = excel_manager.get_all_projects()
# → lista de dicts con todos los campos de `projects`

tracking_df = excel_manager.tracking_df
# → DataFrame de tabla `tracking`

# Construcción del scatter post-impl
for tracking in tracking_df.iterrows():
    project = excel_manager.get_project(tracking['project_id'])
```

No hay queries SQL directas — todo pasa por `excel_manager`.

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.metric` × 4 | Total proyectos, score promedio, ahorro total, alta prioridad |
| `px.histogram` | Distribución de scores |
| `px.pie` | Distribución de prioridades |
| `px.scatter` | ROI vs Score, Score inicial vs Performance real |
| `px.bar` × 2 | Distribución de complejidad y riesgo |
| `st.dataframe` (styled) | Tabla con filas coloreadas por prioridad |
| `st.metric` × 4 | Métricas de tracking (performance, efficiency, adoption, satisfaction) |
| `st.info` × N | Insights automáticos |
| `st.button` + `st.download_button` | Exportación a Excel |

---

## 8. Dependencias

### Otras pestañas
- **Viabilidad**: crea los proyectos que aparecen aquí.
- **Impact KPIs**: crea los trackings que alimentan la sección de métricas reales.
- No hay estado compartido de Streamlit — solo lectura via `excel_manager`.

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `ui.tabs.shared.ExcelSharePointManager` | Fuente única de datos |
| `plotly.express` | Todos los gráficos |
| `pandas` | Procesamiento de DataFrames |

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Sin proyectos | Warning "no hay proyectos" + exit |
| Solo 1 proyecto | Scatter ROI vs Score no se muestra (`len > 1`) |
| `annual_savings = 0` para todos | `total_savings = $0` — válido |
| `tracking_df` vacío | Sección de tracking no se renderiza |
| Solo 1 tracking | Scatter inicial vs real no se muestra (`len > 1`) |
| `efficiency_ratio = 0` | Puntos de tamaño 0 en scatter — invisibles |
| Proyectos sin `priority` definida | Color fallback (`''`) — puede romper `highlight_priority` |

---

## 10. Performance

### Situación actual
- `excel_manager.get_all_projects()` se llama en cada render del tab.
- El loop `for tracking in tracking_df.iterrows()` hace N llamadas a `get_project()` — una por tracking.
- No hay `st.cache_data`.

### Mejoras necesarias
- [ ] Cachear `get_all_projects()` con `st.cache_data(ttl=60)`.
- [ ] Reemplazar el loop N de `get_project()` por un JOIN en la capa de datos → un solo query.
- [ ] Agregar filtros básicos (por año, país, equipo) para portfolios grandes.

---

## 11. Validación

- No hay validación de inputs (es solo lectura).
- Consistencia esperada: suma de `annual_savings` debe coincidir con suma individual de proyectos en Viabilidad.

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2025-Q4 | Versión inicial | Xiomara |
| 2026-01 | Agrega análisis de factores (complejidad/riesgo) | Xiomara |
| 2026-02 | Agrega scatter score inicial vs performance real | Xiomara |
| 2026-03 | Agrega insights automáticos y exportación | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Descriptivas de portafolio**: agrega el estado del conjunto de proyectos en un momento dado.
- `avg_viability` es un promedio simple — no pondera por tamaño ni por status.

### Supuestos
- Todos los proyectos tienen igual peso en los promedios (no hay ponderación por ahorro estimado o criticidad).
- `total_savings` suma proyecciones (`annual_savings`), no ahorros realizados — puede sobreestimar el impacto real.

### Limitaciones
- No hay filtros de fecha ni status — incluye proyectos rechazados, on_hold, etc. en los promedios.
- El insight de "portafolio sólido" usa umbral fijo (50% con score ≥80) no configurable.

### Mejoras futuras
- Agregar filtros de status, año y equipo directamente en el dashboard.
- Separar claramente "ahorros proyectados" vs "ahorros realizados" en KPIs.
- Hacer los umbrales de insights configurables en `scoring_config.json`.
