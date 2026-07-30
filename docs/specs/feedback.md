# Feedback (Procesador de Encuestas)

## 1. Propósito

Procesa encuestas post-implementación en formato Excel, convierte respuestas en datos de tracking, agrega múltiples respuestas por proyecto y actualiza seguimiento automáticamente.

## 2. Inputs

### Fuentes de datos
- Archivo Excel subido por el usuario (`.xlsx` / `.xls`) con respuestas.
- `st.session_state.excel_manager` para proyectos y tracking existente.

### Estructura del Excel de encuesta (columnas requeridas)
| Columna | Tipo | Regla |
|---|---|---|
| `ID DEL PROYECTO a evaluar` (o `ID DEL PROYECTO`) | texto | Debe existir en proyectos |
| `¿Qué tan satisfecho/a estás con la nueva herramienta?` | número | Rango 1-10 |
| `¿Con qué frecuencia utilizas esta herramienta?` | opción única | `Diario`, `Semanal`, `Mensual`, `Ocasional` |
| `¿Qué porcentaje de tiempo te ahorra comparado con el proceso anterior?` | número | Rango 0-100, acepta `12.5` y `12,5` |
| `¿Qué tan probable es que recomiendes esta herramienta a un compañero?` | número | Rango 0-10 |
| `¿Qué beneficios adicionales has notado?` (o variante con `(opcional)`) | texto | Opcional |
| `¿Qué problemas o dificultades has enfrentado?` (o variante con `(opcional)`) | texto | Opcional |
| `Procesado` | texto | Vacio/`No` se procesa; `Si` marcado como procesado |

## 3. Transformaciones clave

- Normalizacion de columnas: trim de espacios y reemplazo de non-breaking spaces.
- Normalizacion numerica: elimina `%`, acepta coma o punto decimal.
- `time_reduction_percent`: se usa directo desde encuesta (0-100).
- Agregacion por proyecto:
  - `user_satisfaction_score`: promedio.
  - `time_reduction_percent`: promedio.
  - `nps_score`: promedio.
  - `usage_frequency`: moda (valor mas frecuente).
  - `nps_promoters`, `nps_passives`, `nps_detractors`: conteos.
  - `unexpected_benefits`, `challenges_faced`: concatenacion unica con ` | `.

## 4. Merge con tracking existente

Si ya existe tracking para el proyecto:
- Satisfaccion: promedio entre ultimo tracking y nuevo agregado.
- Tiempo ahorrado: toma el valor nuevo agregado.
- NPS: promedio simple entre ultimo tracking y nuevo agregado cuando ambos existen.
- Frecuencia: toma la frecuencia nueva consolidada.
- Textos cualitativos: combina evitando duplicados.

## 5. Outputs

- Actualizacion de tabla `tracking` con campos existentes + nuevos:
  - `survey_time_saved_percent`
  - `usage_frequency`
  - `nps_score`
  - `nps_promoters`
  - `nps_passives`
  - `nps_detractors`
- Historial en tab de feedback con satisfaccion, adopcion, NPS y frecuencia.
- Marcado de `Procesado` en archivo local cuando el input es ruta de archivo.

## 6. Ejemplo rapido

Entrada encuesta:
- `time_saved_percent = 12,5`
- `satisfaction = 9`
- `nps = 8`

Resultado interno:
- `time_reduction_percent = 12.5`
- `user_satisfaction_score = 9`
- `nps_score = 8`

## 7. Validaciones

- Fila se descarta si:
  - satisfaccion fuera de 1-10,
  - tiempo ahorrado fuera de 0-100,
  - frecuencia fuera del enum,
  - NPS fuera de 0-10.
- Si faltan columnas requeridas, no se procesa el archivo.
