# Feedback (Procesador de Encuestas)

## 1. Propósito

Procesa encuestas de satisfacción post-implementación en formato Excel, convierte las respuestas al formato de tracking de la plataforma, agrega múltiples respuestas por proyecto y actualiza el seguimiento automáticamente.

**Usuarios:** Project managers o analistas que reciben respuestas de encuestas de usuarios finales.

---

## 2. Inputs

### Fuentes de datos
- Archivo Excel subido por el usuario (`.xlsx` / `.xls`) con respuestas de encuesta
- `st.session_state.excel_manager` → proyectos y trackings existentes (para merge)

### Estructura del Excel de encuesta (columnas requeridas)
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `ID DEL PROYECTO` | str | Project ID (ej. `MX-XIO-0001`) |
| `¿Qué tan satisfecho/a estás con la nueva herramienta?` | int 1-10 | Score de satisfacción |
| `¿Qué porcentaje de tiempo te ahorra comparado con el proceso anterior?` | int 1-10 | Escala 1-10 que se convierte a % |
| `¿Qué beneficios adicionales has notado? (opcional)` | str | Texto libre |
| `¿Qué problemas o dificultades has enfrentado? (opcional)` | str | Texto libre |
| `Procesado` | str | Columna de control: vacío/`No` = no procesado; `Sí` = ya procesado |

### Parámetros del usuario
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Archivo Excel | file_uploader | `.xlsx` / `.xls` |
| Botón "Procesar" | button | Dispara el procesamiento |

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Métricas de procesamiento | `st.metric` × 3 | Tras procesar (total, procesadas, proyectos actualizados) |
| Detalle por proyecto | `st.expander` | Respuestas, satisfacción, tiempo ahorrado |
| Tracking actualizado | INSERT en tabla `tracking` | Via `calculator.add_tracking()` |
| Excel original con columna `Procesado` marcada | Escritura en disco (si es ruta de archivo) | Solo en procesamiento automático |
| Historial de proyectos con tracking | `st.dataframe` | Sub-tab Historial |
| Preview de conversiones | `st.dataframe` × 2 | Sub-tab Previsualización |

---

## 4. Lógica de negocio

### Conversión de escala de tiempo ahorrado
```
tiempo_ahorrado_cuestionario: escala 1-10
time_reduction_percent = (score - 1) / 9 * 100

Ejemplos:
  1  → 0.0%
  3  → 22.2%
  7  → 66.7%
  10 → 100.0%
```

### Filtrado de respuestas no procesadas
```
columna "Procesado" está vacía
OR columna "Procesado" == ""
OR columna "Procesado" == "No"
→ se incluye para procesamiento

"Sí" → se excluye (ya procesado)
```

### Aggregación por proyecto
```
Para cada project_id único en respuestas no procesadas:
  user_satisfaction_score = mean(satisfacción)        → round(1 decimal)
  time_reduction_percent  = mean(tiempo_reducción%)   → round(1 decimal)
  unexpected_benefits     = join único de textos con " | "
  challenges_faced        = join único de textos con " | "
  adoption_rate           = 85  (valor fijo por defecto)
```

### Merge con tracking existente
```
SI NO existe tracking previo:
  → usa datos nuevos directamente

SI EXISTE tracking previo (usa el último):
  satisfaction_final = (existing + new) / 2
  time_reduction     = new  (más actualizado)
  benefits           = combine_texts(existing, new)   → elimina duplicados
  problems           = combine_texts(existing, new)
  otros campos       = mantiene valores del tracking existente
```

### Cálculo de tiempo real para tracking
```
actual_time_per_task = original_time * (1 - time_reduction_percent / 100)
```
Donde `original_time = project['current_time_per_task']` del registro de Viabilidad.

### Marcado de procesadas
Solo si el input es una ruta de archivo (procesamiento automático desde tracking.py):
```
Columna "Procesado" → "Sí" para todas las filas del proyecto procesado
Sobrescribe el Excel original en disco
```

---

## 5. Flujo funcional

La pestaña tiene **3 sub-tabs**:

### Sub-tab 1 — Cargar y Procesar
1. Usuario sube archivo Excel
2. Preview en expander (primeras filas + total de respuestas)
3. Click "Procesar":
   - Carga y valida columnas requeridas
   - Filtra respuestas no procesadas
   - Agrega por proyecto
   - Para cada proyecto: merge con tracking existente → `add_tracking()`
   - Muestra métricas: total respuestas / procesadas / proyectos actualizados
   - Lista de proyectos actualizados con expanders

### Sub-tab 2 — Previsualización del cuestionario
- Muestra estructura esperada del Excel
- Tablas de conversión: satisfacción (1-10 → 1-10 directo) y tiempo ahorrado (1-10 → 0-100%)

### Sub-tab 3 — Historial
- Lista todos los proyectos que tienen al menos un tracking guardado
- Muestra: ID, nombre, satisfacción, adopción, fecha de última actualización

---

## 6. Queries / lógica de datos

```python
# Lectura de proyectos y tracking
excel_manager.get_all_projects()
excel_manager.get_project_tracking(project_id)
excel_manager.get_project(project_id)

# Escritura de tracking
calculator.add_tracking(project_id, tracking_data)

# Lectura del Excel de encuesta
pd.read_excel(uploaded_file_or_path)
```

No hay queries SQL directas en este módulo — todo pasa por `excel_manager` y `calculator`.

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.tabs` (3) | Cargar / Previsualización / Historial |
| `st.file_uploader` | Subir Excel de encuesta |
| `st.expander` | Preview del Excel |
| `st.button` | Disparar procesamiento |
| `st.spinner` | Procesando... |
| `st.metric` × 3 | Total respuestas, procesadas, proyectos actualizados |
| `st.expander` por proyecto | Detalle de respuestas, satisfacción, tiempo ahorrado |
| `st.dataframe` × 2 | Tablas de conversión en sub-tab 2 |
| `st.dataframe` | Historial en sub-tab 3 |

---

## 8. Dependencias

### Otras pestañas
- **Impact KPIs (Post-impl)**: usa el mismo `FeedbackProcessor` para el procesamiento automático al abrir la pestaña.
- Los datos guardados aquí son visibles en **Dashboard** (tracking_df) y **Post-impl**.

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `ui.tabs.shared.ExcelSharePointManager` | Proyectos y trackings |
| `ui.tabs.shared.ProjectViabilityCalculator` | `add_tracking()` |
| `pandas` | Lectura/procesamiento del Excel |
| `numpy` | Operaciones numéricas en procesamiento |

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Columnas del Excel en encoding incorrecto | Los nombres de columna tienen `Â¿` en lugar de `¿` — [BUG CONOCIDO] si el Excel no está en UTF-8 |
| Satisfacción fuera de [1, 10] | Fila descartada silenciosamente (`df.between(1,10)`) |
| Tiempo ahorrado fuera de [1, 10] | Fila descartada silenciosamente |
| Project ID no existe en sistema | Retorna `False` con mensaje "Proyecto X no encontrado" |
| Todas las respuestas ya procesadas | info "sin respuestas nuevas" |
| Columna "Procesado" no existe en Excel | Se crea con valores vacíos |
| Múltiples respuestas del mismo proyecto con beneficios repetidos | Se eliminan duplicados en `_combine_texts()` |
| `adoption_rate` fijo en 85 | No capturado en encuesta — es un supuesto hardcodeado |

---

## 10. Performance

### Situación actual
- Procesamiento completamente síncrono.
- Carga el Excel completo en memoria.
- N llamadas a `add_tracking()` (una por proyecto único en el Excel).

### Mejoras necesarias
- [ ] Mostrar barra de progreso si hay muchos proyectos a procesar.
- [ ] Validar encoding del Excel al cargar y mostrar advertencia si hay columnas con caracteres mal codificados.

---

## 11. Validación

### Checks actuales
- Columnas requeridas: `ID DEL PROYECTO`, satisfacción, tiempo_ahorrado% — si falta alguna → error y no procesa.
- Valores numéricos fuera de rango [1, 10] → fila descartada (sin aviso al usuario).

### Ejemplos esperados
```
Input Excel:
  project_id  | satisfacción | tiempo (1-10)
  MX-XIO-0001 |     8        |     7

Output:
  satisfaction = 8/10
  time_reduction_percent = (7-1)/9*100 = 66.7%
  actual_time_per_task = original_time * (1 - 0.667)
```

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2026-01 | Versión inicial: upload + procesamiento | Xiomara |
| 2026-02 | Agrega merge con tracking existente | Xiomara |
| 2026-03 | Agrega sub-tabs (Cargar / Preview / Historial) | Xiomara |

---

## 13. Definición analítica

### Tipo de métricas
- **Capturadas desde usuarios finales**: satisfacción y tiempo ahorrado vienen directamente de los respondientes.
- La conversión de escala 1-10 → % es lineal y normalizada al rango [0, 100%].

### Supuestos
- Una respuesta por usuario por proyecto — si hay múltiples respuestas del mismo usuario, se promedian igual que las de distintos usuarios.
- `adoption_rate = 85%` es fijo — no refleja la adopción real del proyecto.
- El promedio simple de satisfacción entre respuestas existentes y nuevas puede distorsionar si el número de respuestas es muy diferente entre ambas.

### Limitaciones
- Sin captura de `adoption_rate` real en la encuesta.
- Sin versionado de procesamiento — no hay log de cuándo se procesó ni cuántas veces.
- El marcado de "Procesado" en el Excel solo funciona cuando es un archivo en disco (no un upload de Streamlit en memoria).

### Mejoras futuras
- Agregar pregunta de `adoption_rate` al cuestionario.
- Loggear cada procesamiento en una tabla de auditoría (`feedback_processing_log`).
- Permitir deshacer un procesamiento (marcar como "no procesado" desde la UI).
- Conectar con el flujo de email post-cierre para enviar automáticamente el link al formulario (ver spec de Seguimiento Operativo — sección 13).
