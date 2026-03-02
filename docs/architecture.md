# Arquitectura

## Vista general

La aplicacion esta construida en Streamlit y combina dos bloques:

1. **Flujo de viabilidad/tracking (legacy evolucionado)**  
   - UI: `planning.py`, `tracking.py`, `dashboard.py`, `feedback_processor.py`
   - Orquestacion: `main.py`
   - Logica y persistencia principal: `shared.py`
   - DB: `project_viability.db`

2. **Use Case Matrix (modular/SOLID)**  
   - UI: `ui/use_case_matrix.py`
   - Dominio: `domain/scoring.py`, `domain/matrix.py`, `domain/models.py`
   - Infra: `infra/db.py`, `infra/repositories.py`, `infra/config_loader.py`
   - DB: `data/projects.db`

## Flujo de datos

### Planificacion

- Usuario captura datos en `planning.py`.
- `ProjectViabilityCalculator` (`shared.py`) calcula score de viabilidad y metricas financieras.
- Se guarda/actualiza en `project_viability.db`.
- Se sincroniza automaticamente hacia Use Case Matrix:
  - upsert de metadata de proyecto en `data/projects.db`
  - insercion de evaluacion `current` (marcando la anterior como `is_current=false`).

### Use Case Matrix

- `ui/use_case_matrix.py` consume repositorios (`infra/repositories.py`).
- Guarda historial en `evaluations` y mantiene una sola evaluacion `current` por proyecto.
- Muestra scatter y resumen con valores actuales.

## Decisiones de arquitectura

- Se mantuvo `shared.py` por compatibilidad con el flujo original.
- Se agrego capa modular para la matriz (dominio e infraestructura separados).
- Se usa configuracion externa en `config/scoring_config.json` para evitar hardcode.

## Riesgo tecnico actual

- **Dual DB**: hay dos fuentes de verdad parciales (`project_viability.db` y `data/projects.db`).
- Mitigacion actual: sincronizacion desde Planificacion hacia matriz en cada guardar/editar.
- Recomendacion futura: consolidar en una sola DB con migracion controlada.
