# Modelo de Datos

## Base 1: `project_viability.db`

Usada por el flujo de Planificacion/Tracking en `shared.py`.

### Tabla `projects`

Campos clave:
- `id` (PK)
- `name`, `description`
- `country`, `owner`
- `created_date`, `status`, `last_tracking_update`
- inputs de planificacion:
  - `current_time_per_task`, `tasks_per_month`, `staff_count`, `avg_salary_per_hour`
  - `time_reduction_percent`, `development_hours`, `development_cost_per_hour`
  - `maintenance_monthly`, `implementation_complexity`, `risk_level`
- outputs:
  - `viability_score`, `priority`, `recommendation`
  - `monthly_savings`, `annual_savings`, `payback_period_months`, `roi_first_year`
  - `initial_development_cost`, `hours_saved_per_month`
  - `actual_monthly_savings`, `actual_annual_savings`

### Tabla `tracking`

Campos clave:
- `id` (PK)
- `project_id` (FK logica a `projects.id`)
- `tracking_date`
- `months_tracked`
- `actual_time_per_task`, `actual_tasks_per_month`
- `adoption_rate`, `user_satisfaction_score`
- `unexpected_benefits`, `challenges_faced`, `lessons_learned`
- `performance_score`, `efficiency_ratio`, `actual_time_reduction_percent`
- `actual_monthly_savings`, `actual_annual_savings`

## Base 2: `data/projects.db`

Usada por Use Case Matrix con SQLAlchemy.

### Tabla `projects`

- `project_id` (PK)
- `country`
- `owner`
- `name`
- `created_at`
- `updated_at`

### Tabla `evaluations`

- `eval_id` (PK autoincrement)
- `project_id` (FK -> `projects.project_id`)
- `answers_json` (A-H)
- `weights_json` (A-H)
- `impact_score`
- `effort_score`
- `is_current` (bool)
- `created_at`

## Reglas importantes

1. **ID de proyecto**  
   Formato configurable por `config/scoring_config.json`:
   - default: `{country}-{owner}-{sequence}`
   - default sequence: 4 digitos (`n_digits=4`)
   - ejemplo: `MX-CARLOS-0007`

2. **Current unica en matriz**  
   Por cada `project_id`, solo una evaluacion debe tener `is_current=true`.
   - al guardar nueva evaluacion:
     - todas las current previas pasan a `false`
     - la nueva entra con `true`

3. **Sincronizacion desde Planificacion**  
   Guardar/editar en Planificacion actualiza la evaluacion current en Use Case Matrix.
