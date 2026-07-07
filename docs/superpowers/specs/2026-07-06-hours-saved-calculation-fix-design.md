# Spec: Corregir fórmula de hours_saved_per_month y recalcular histórico

**Fecha:** 2026-07-06  
**Estado:** Aprobado

---

## Contexto

La fórmula de cálculo de `hours_saved_per_month` en `domain/scoring/financials.py` multiplica incorrectamente por `staff_count`, inflando los resultados. Ejemplo: un proyecto con `staff_count=200` muestra 200 veces más horas ahorradas de las que debería.

El bug solo se manifiesta cuando `staff_count > 1`. Proyectos con `staff_count=1` (AR-DDD-0001, MX-DDD-0003, MX-DDD-0006) dieron cifras correctas por coincidencia.

**Ubicación de los datos reales:** Los snapshots finales de evaluación se guardan en **Supabase (PostgreSQL)**, no en la BD local SQLite. El proyecto usa `infra/db/adapter.py`, que unifica ambos motores y selecciona el destino según la variable de entorno `DATABASE_URL`:
- Si `DATABASE_URL` está definida → conecta a Supabase (PostgreSQL, `IS_CLOUD=True`, `PLACEHOLDER="%s"`).
- Si no → usa SQLite local (`IS_CLOUD=False`, `PLACEHOLDER="?"`).

Por lo tanto, el script de recalculate DEBE correr contra Supabase (con `DATABASE_URL` apuntando a la instancia cloud) para corregir los datos reales, y DEBE usar `infra/db/adapter.py` para ser compatible con ambos motores.

---

## Objetivo

1. Corregir la fórmula eliminando el factor `staff_count` incorrecto
2. Agregar tests parametrizados que demuestren la corrección
3. Recalcular retroactivamente todos los snapshots históricos en la BD

---

## Alcance

### Dentro del scope
- Modificar línea 17 en `domain/scoring/financials.py`: quitar `* staff_count`
- Agregar tests parametrizados con `staff_count > 1` en `tests/unit/test_financials.py`
- Crear script `scripts/recalculate_evaluation_snapshots.py` para recalcular histórico
- Ejecutar recalculate y validar resultados

### Fuera del scope
- Refactorizar la estructura de `compute_financials()` (mantener firma igual)
- Cambiar otras métricas de viabilidad (solo impacta financiero)
- Auditoría histórica de decisiones tomadas con datos incorrectos

---

## Sección 1: Corrección de la fórmula

### Cambio en `domain/scoring/financials.py`

**Línea 17 — Actual (incorrecta):**
```python
hours_saved_per_month = time_saved * tasks_per_month * staff_count
```

**Línea 17 — Corregida:**
```python
hours_saved_per_month = time_saved * tasks_per_month
```

### Justificación

- `tasks_per_month` (parámetro de entrada) ya representa el volumen total del proceso/equipo
- `staff_count` es la cantidad de personas en el equipo, pero NO es un multiplicador de volumen
- El volumen de trabajo (`tasks_per_month`) es independiente del tamaño del equipo que lo ejecuta
- Ejemplo: un proceso con 60 tareas/mes sigue siendo 60 tareas/mes, independientemente de si 1 persona o 200 lo hacen

### Cascada automática

Los campos derivados se corrigen sin cambios adicionales:
- `monthly_savings = hours_saved_per_month × avg_salary_per_hour`
- `annual_savings = monthly_savings × 12`
- `payback_period_months = initial_development_cost / (net_annual_benefit / 12)`
- `roi_first_year = (net_annual_benefit - initial_development_cost) / initial_development_cost × 100`

---

## Sección 2: Cobertura de tests

### Tests parametrizados en `tests/unit/test_financials.py`

Agregar nuevos tests que demuestren:

1. **Caso HI-DDD-0002 (Macro VBA Botones):** `staff_count=1`
   ```
   0.08h/tarea × 60 tareas/mes × (85% reducción) = 4.08 horas/mes
   ```

2. **Caso LA-COPILOT-0001 (equipo grande):** `staff_count=200`
   ```
   Esperado: 4.08 horas/mes × 200 personas = 816 horas totales
   NO: 0.08 × 60 × 200 × 0.85 = 816 (por coincidencia algebraica)
   Punto: la fórmula correcta debe dar 4.08, no 816
   ```

**Estructura:**
```python
@pytest.mark.parametrize("staff_count,expected_hours_saved", [
    (1, 4.08),      # HI-DDD-0002: single person
    (5, 4.08),      # Multi-person, mismo volumen
    (200, 4.08),    # Large team, mismo volumen
])
def test_hours_saved_per_month_independent_of_staff_count(staff_count, expected_hours_saved):
    result = compute_financials(
        current_time_per_task=0.08,
        tasks_per_month=60,
        staff_count=staff_count,
        avg_salary_per_hour=100,
        time_reduction_percent=85,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=0,
    )
    assert result["hours_saved_per_month"] == pytest.approx(expected_hours_saved, rel=0.01)
```

---

## Sección 3: Recalcular histórico

### Script: `scripts/recalculate_evaluation_snapshots.py`

**Conexión:** Usa `infra/db/adapter.py` — `get_connection()`, `IS_CLOUD` y `PLACEHOLDER`. NO conecta directamente ni asume SQLite. Corre contra Supabase cuando `DATABASE_URL` está definida (caso real de producción) y contra SQLite local en su ausencia (para pruebas).

**Responsabilidades:**
1. Obtener conexión vía `get_connection()` (respeta `DATABASE_URL` → Supabase o SQLite)
2. Leer todos los snapshots de `project_evaluations` (incluyendo `evaluation_id`, `project_id`, campos financieros e `inputs_json`)
3. Parsear `inputs_json` — extraer los 8 parámetros que consume `compute_financials()`
4. Re-ejecutar `compute_financials()` con la fórmula correcta
5. Comparar los valores recalculados contra los almacenados (`hours_saved_per_month`, `monthly_savings`, `annual_savings`, `payback_period_months`, `roi_first_year`)
6. Para filas que cambiaron: ejecutar `UPDATE ... WHERE evaluation_id = {PLACEHOLDER}`
7. `conn.commit()` una sola vez al final (no por fila)
8. Generar reporte: cantidad actualizada, sin cambios, errores

**Esquema de `inputs_json` (verificado en `ui/tabs/planning.py`):** Contiene los 8 parámetros que consume `compute_financials()`, con nombres de llave idénticos a los de la firma de la función — no requiere mapeo:

| Llave en `inputs_json` | Parámetro de `compute_financials()` |
|---|---|
| `current_time_per_task` | `current_time_per_task` |
| `tasks_per_month` | `tasks_per_month` |
| `staff_count` | `staff_count` |
| `avg_salary_per_hour` | `avg_salary_per_hour` |
| `time_reduction_percent` | `time_reduction_percent` |
| `development_hours` | `development_hours` |
| `development_cost_per_hour` | `development_cost_per_hour` |
| `maintenance_monthly` | `maintenance_monthly` |

(El JSON también incluye `name`, `description`, `country`, `owner`, `implementation_complexity`, `risk_level` — irrelevantes para el recálculo financiero.)

**Manejo de `inputs_json` (compatibilidad de motores):**
- En SQLite se guarda como texto → usar `json.loads()`.
- En PostgreSQL/Supabase la columna puede devolverse ya como `dict` (jsonb) → verificar `isinstance(raw, str)` antes de `json.loads()`.
- Si a un snapshot le faltan campos de entrada en `inputs_json` (evaluaciones viejas), se cuenta como "omitido" y se reporta, sin abortar el proceso.

**Motor de conexión (informativo en el reporte):** El script imprime al inicio si está operando sobre Supabase (`IS_CLOUD=True`) o SQLite, para que la operadora confirme el destino antes de escribir.

**Invocación:**
```bash
# Contra Supabase (datos reales) — DATABASE_URL debe estar exportada
python scripts/recalculate_evaluation_snapshots.py --dry-run   # revisar sin escribir
python scripts/recalculate_evaluation_snapshots.py             # aplicar cambios
```

- `--dry-run`: Muestra qué se actualizaría sin tocar la BD (no hace `commit`)
- `--verbose`: Detalla cada cambio (before/after por fila)

**Output esperado:**
```
Motor: Supabase (PostgreSQL, IS_CLOUD=True)
Snapshots procesados: 45
  Actualizados: 8 (staff_count > 1)
  Sin cambios: 37 (staff_count = 1 o sin datos)
  Omitidos:    0 (inputs_json incompleto)
  Errores:     0

Cambios (--verbose):
  evaluation_id=123 | LA-COPILOT-0001
    hours_saved_per_month: 816.00 → 4.08
    annual_savings: 979200.00 → 4896.00
    roi_first_year: 163840.00 → -95.10
```

### Seguridad de datos antes de escribir en Supabase

- **Siempre correr `--dry-run` primero** y confirmar que el motor reportado es Supabase y que la cantidad de filas a cambiar es la esperada.
- **Backup previo:** exportar la tabla `project_evaluations` desde Supabase (dashboard o `pg_dump`) antes de la corrida real, ya que el `UPDATE` sobrescribe valores.

---

## Sección 4: Validación

### Caso de prueba HI-DDD-0002

**Parámetros (datos de prueba):**
- `current_time_per_task = 0.08h`
- `tasks_per_month = 60`
- `time_reduction_percent = 85%`
- `staff_count = 1`
- `avg_salary_per_hour = 100`
- `development_hours = 100`
- `development_cost_per_hour = 100`
- `maintenance_monthly = 0`

**Cálculo esperado (fórmula correcta):**
```
time_saved = 0.08 × (85 / 100) = 0.068h
hours_saved_per_month = 0.068 × 60 = 4.08h/mes ✓
monthly_savings = 4.08 × 100 = $408/mes
annual_savings = 408 × 12 = $4,896/año
initial_development_cost = 100 × 100 = $10,000
net_annual_benefit = 4,896 - 0 = $4,896
payback_period_months = 10,000 / (4,896 / 12) ≈ 24.6 meses
roi_first_year = (4,896 - 10,000) / 10,000 × 100 = -51% (aún en payback)
```

**Verificación final en plataforma:**
- Ejecutar tests: `pytest tests/unit/test_financials.py -v`
- Ejecutar recalculate en dry-run contra Supabase: `python scripts/recalculate_evaluation_snapshots.py --dry-run --verbose` (confirmar motor = Supabase)
- Aplicar: `python scripts/recalculate_evaluation_snapshots.py`
- Revisar snapshot de HI-DDD-0002 en Supabase: `hours_saved_per_month == 4.08`

---

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `domain/scoring/financials.py` | Línea 17: quitar `* staff_count` |
| `tests/unit/test_financials.py` | Agregar tests parametrizados |
| `scripts/recalculate_evaluation_snapshots.py` | Nuevo script |

---

## Criterios de éxito

1. ✓ `domain/scoring/financials.py` línea 17 corregida (sin `* staff_count`)
2. ✓ Tests parametrizados pasan con `staff_count ∈ {1, 5, 200}`
3. ✓ Script `recalculate_evaluation_snapshots.py` usa `infra/db/adapter.py` y ejecuta sin errores contra Supabase
4. ✓ Supabase actualizada: snapshots con `staff_count > 1` corregidos
5. ✓ HI-DDD-0002 muestra `hours_saved_per_month = 4.08` (no 8.16 ni otro valor)
6. ✓ Reporte de recalculate indica motor (Supabase) y cantidad exacta de filas actualizadas

---

## Notas de implementación

- **Retrocompatibilidad:** El cambio es puro — solo afecta a proyectos con `staff_count > 1`
- **Datos existentes:** El script de recalculate reescribe filas en Supabase; guardar backup de `project_evaluations` antes de la corrida real y usar `--dry-run` para confirmar.
- **Tests:** Todos los tests existentes seguirán pasando (usan `staff_count=1`)
- **Motor único de escritura:** Los datos reales viven en Supabase; SQLite local solo sirve para desarrollo. El script diferencia el motor vía `IS_CLOUD` y lo reporta antes de escribir.
