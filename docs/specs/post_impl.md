# Impact KPIs (Post-Implementación)

## 1. Propósito

Registra y evalúa el desempeño real de proyectos ya implementados, comparando resultados esperados vs. reales. Puede poblar datos automáticamente desde un archivo Excel de encuestas o de forma manual.

**Usuarios:** Project managers evaluando el impacto real de proyectos cerrados (status = `implemented`).

---

## 2. Inputs

### Fuentes de datos
- `st.session_state.excel_manager` → proyectos con status `implemented` y sus datos de tracking previos
- `encuesta_feedback.xlsx` → archivo local con respuestas de encuesta (path hardcodeado)

### Parámetros del usuario (formulario manual)
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Proyecto | selectbox | Solo proyectos con status `implemented` |
| Meses tracked | number_input | Cuántos meses lleva implementado |
| Tiempo real por tarea (hrs) | number_input | Tiempo actual con la solución |
| Tareas reales por mes | number_input | Volumen actual |
| Tasa de adopción % | slider 0-100 | % usuarios que adoptaron la solución |
| Satisfacción del usuario | slider 1-10 | Score de satisfacción |
| Beneficios inesperados | text_area | Texto libre |
| Desafíos encontrados | text_area | Texto libre |
| Lecciones aprendidas | text_area | Texto libre |

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Gauge de performance real | `go.Indicator` | Panel derecho |
| Métricas: efficiency_ratio, adoption_rate, actual_savings, satisfaction | `st.metric` | Panel derecho |
| Comparativo esperado vs. real | `st.metric` × 4 | Panel derecho |
| Análisis cualitativo | `st.expander` | Panel derecho |
| Recomendaciones automáticas | `st.info` | Panel derecho |
| Tracking guardado | INSERT en `tracking` (via excel_manager) | Al guardar |
| Mensaje de proyectos actualizados desde encuesta | `st.success` / `st.info` | Inicio del tab |

---

## 4. Lógica de negocio

### Métricas calculadas por `ProjectViabilityCalculator.add_tracking()`
```
actual_time_reduction_percent = (original_time - actual_time) / original_time * 100

actual_monthly_savings = (original_time - actual_time) * actual_tasks_per_month
                         * staff_count * avg_salary_per_hour

efficiency_ratio = actual_monthly_savings / expected_monthly_savings
                   → esperado = original_time * time_reduction% * tasks * staff * rate

performance_score = [VERIFICAR en shared.py: combinación de efficiency + adoption + satisfaction]
```

### Procesamiento automático de encuesta
Al abrir la pestaña, busca `encuesta_feedback.xlsx` en el directorio raíz:
```
SI archivo no existe    → info "no encontrado"
SI faltan columnas      → info "columnas inválidas"
SI hay respuestas nuevas → procesa y actualiza tracking automáticamente
SI todo procesado       → info "sin respuestas nuevas"
```

### Clasificación de fuente de tracking
```
SI satisfaction > 0 AND tiene textos de beneficios/problemas → "automático (encuesta)"
SI satisfaction > 0 OR actual_time_per_task > 0             → "manual"
ELSE                                                          → "sin datos"
```

### Interpretación del efficiency_ratio
```
>= 1.2  → "Superó significativamente las expectativas"
>= 1.0  → "Cumplió expectativas"
>= 0.7  → "Cerca de expectativas"
< 0.7   → "Por debajo de expectativas"
```

### Recomendaciones automáticas
```
efficiency >= 1.2          → "Replicar metodología"
efficiency < 0.8           → "Revisar metodología"
adoption_rate < 70         → "Reforzar capacitación / change management"
satisfaction < 7           → "Involucrar más a usuarios"
performance >= 90          → "Expandir alcance"
```

---

## 5. Flujo funcional

1. Al abrir tab: intenta procesar `encuesta_feedback.xlsx` automáticamente (spinner)
2. Muestra resultado del procesamiento (proyectos actualizados o mensaje informativo)
3. Filtra proyectos con `status = 'implemented'`; si ninguno → warning y exit
4. Selectbox de proyecto (muestra fuente de datos: manual / encuesta / sin datos)
5. Muestra estado del tracking del proyecto seleccionado
6. **Columna izquierda**: formulario de datos reales + botón guardar
7. **Columna derecha**: gauge + métricas + comparativo + análisis cualitativo + recomendaciones
8. Si no hay tracking → muestra info del proyecto proyectado

---

## 6. Queries / lógica de datos

### Lectura
```python
# Todos los proyectos implemented
excel_manager.get_all_projects()  # filtra status == "implemented"

# Tracking previo
excel_manager.get_project_tracking(project_id)  # retorna lista ordenada por fecha
```

### Escritura
```python
calculator.add_tracking(project_id, tracking_data)
# Inserta en tabla `tracking` con campos calculados (performance_score, efficiency_ratio, etc.)
```

### Archivo de encuesta (si existe)
```python
pd.read_excel("encuesta_feedback.xlsx")
# Columnas requeridas: 'ID DEL PROYECTO', satisfacción (1-10), tiempo ahorrado (1-10)
```

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.spinner` | Procesamiento automático de encuesta al abrir |
| `st.success` / `st.info` | Resultado del auto-procesamiento |
| `st.expander` | Detalle de proyectos actualizados automáticamente |
| `st.selectbox` | Selección de proyecto implemented |
| `st.number_input` × 3 | Meses, tiempo real, tareas reales |
| `st.slider` × 2 | Adopción (0-100), satisfacción (1-10) |
| `st.text_area` × 3 | Beneficios, desafíos, lecciones |
| `st.button` | Guardar tracking |
| `go.Indicator` gauge | Performance real |
| `st.metric` × 6+ | Efficiency, adoption, savings, satisfaction, esperado vs real |
| `st.expander` × 3 | Beneficios, desafíos, lecciones (solo lectura) |

---

## 8. Dependencias

### Otras pestañas
- **Viabilidad**: los proyectos que aparecen aquí tienen datos base (time_per_task, tasks, staff, rate) guardados allá.
- **Feedback**: comparte `FeedbackProcessor` — el procesamiento de encuestas es idéntico en ambas pestañas.
- **Dashboard**: usa los datos de tracking guardados aquí para métricas de portfolio.

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `ui.tabs.shared.ExcelSharePointManager` | Lectura de proyectos y trackings |
| `ui.tabs.shared.ProjectViabilityCalculator` | Cálculo de métricas y persistencia de tracking |
| `ui.tabs.feedback_processor.FeedbackProcessor` | Procesamiento automático de encuesta Excel |
| `pandas` | Lectura del Excel de encuesta |
| `plotly.graph_objects` | Gauge de performance |

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Ningún proyecto con status `implemented` | Warning y exit temprano |
| `encuesta_feedback.xlsx` no existe | Info silenciosa, continúa flujo manual |
| Excel con columnas faltantes | Info con nombre de columnas faltantes, no procesa |
| `actual_time_per_task = 0` | Puede resultar en `time_reduction = 100%` — válido si es total automatización |
| `expected_monthly_savings = 0` | `efficiency_ratio = inf` → [VERIFICAR comportamiento en shared.py] |
| Tracking guardado automáticamente + usuario edita manualmente | Se crea nuevo registro (no sobreescribe el auto) |
| Múltiples respuestas de encuesta para un proyecto | Se promedian satisfacción y tiempo; beneficios/problemas se concatenan |

---

## 10. Performance

### Situación actual
- `auto_process_feedback()` se ejecuta en cada render del tab (cada vez que el usuario abre o interactúa con la pestaña).
- Lee el archivo Excel completo cada vez.
- No hay caché.

### Mejoras necesarias
- [ ] Agregar flag en `st.session_state` para no reprocesar la encuesta en cada render — solo al abrir el tab por primera vez o al hacer click explícito en un botón "Actualizar desde encuesta".
- [ ] Hacer el path de `encuesta_feedback.xlsx` configurable desde `config/scoring_config.json` o desde la UI.
- [ ] Cachear `get_all_projects()` con `st.cache_data(ttl=60)`.

---

## 11. Validación

### Checks actuales
- Satisfacción del Excel debe estar en [1, 10] — filas fuera de rango se descartan.
- Tiempo ahorrado del Excel debe estar en [1, 10] — conversión a porcentaje 0-100%.
- No hay validación explícita de `actual_time_per_task` (puede ser 0 o mayor al original).

### Ejemplo esperado
```
Proyecto: MX-XIO-0001
  original_time_per_task = 2.0 hrs
  actual_time_per_task   = 0.5 hrs
  tasks_per_month        = 50
  staff_count            = 3
  avg_salary_per_hour    = 25

actual_time_reduction = (2.0-0.5)/2.0*100 = 75%
actual_monthly_savings = 1.5 * 50 * 3 * 25 = $5,625
expected_monthly_savings = 2.0 * 0.70 * 50 * 3 * 25 = $5,250
efficiency_ratio = 5625/5250 = 1.07 → "Cumplió expectativas"
```

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2025-Q4 | Versión inicial tracking manual | Xiomara |
| 2026-01 | Agrega procesamiento automático de encuesta Excel | Xiomara |
| 2026-02 | Agrega detección de fuente (manual/auto) y recomendaciones | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Descriptivas / realizadas**: datos reales capturados post-implementación.
- `efficiency_ratio` es la métrica central: mide qué tan bien se cumplió la proyección original.

### Supuestos
- `staff_count` y `avg_salary_per_hour` se toman del registro original de Viabilidad (no se actualizan aquí).
- `adoption_rate = 85%` es el default cuando viene de encuesta — no se captura directamente en el cuestionario.
- El tracking más reciente (`trackings[-1]`) es el utilizado para comparación — no hay versionado explícito.

### Limitaciones
- No hay serie de tiempo de tracking — solo se muestra el más reciente.
- No hay separación entre tracking manual y de encuesta en la tabla `tracking` — ambos usan el mismo esquema.

### Mejoras futuras
- Mostrar serie temporal de `performance_score` a lo largo de los meses tracked.
- Capturar `adoption_rate` directamente en la encuesta en lugar de usar default 85%.
- Separar visualmente en la UI los registros provenientes de encuesta vs. manuales.
- Conectar con el flujo de email post-cierre (ver spec de Seguimiento Operativo — sección 13).
