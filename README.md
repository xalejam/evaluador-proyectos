# Plataforma de Gestión de Proyectos (Streamlit)

Aplicación Streamlit para evaluar viabilidad, priorizar portafolio, registrar bitácora operativa y dar seguimiento post-implementación.

## Ejecución

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run start.py
```

Entry point preservado:
- `start.py` -> `main.py`
- comando recomendado: `streamlit run start.py`

## Arquitectura (refactor incremental)

### Capas

- `ui/`: tabs Streamlit, componentes de presentación y estado de sesión.
  - `ui/tabs/viabilidad_tab.py`
  - `ui/tabs/seguimiento_operativo_tab.py`
  - `ui/tabs/post_impl_tab.py`
  - `ui/tabs/dashboard_tab.py`
  - `ui/tabs/use_case_matrix_tab.py`
  - `ui/tabs/feedback_tab.py`
  - `ui/tabs/sql_tab.py`
  - `ui/state.py`
- `domain/`: lógica de negocio pura y servicios.
  - `domain/scoring/score_engine.py`
  - `domain/scoring/financials.py`
  - `domain/scoring/thresholds.py`
  - `domain/services/viability_service.py`
  - `domain/services/seguimiento_operativo_service.py`
  - `domain/services/feedback_service.py`
- `infra/`: persistencia, migraciones, repositorios e integraciones.
  - `infra/db/connection.py`
  - `infra/db/migrations.py`
  - `infra/db/repositories/project_repo.py`
  - `infra/db/repositories/evaluation_repo.py`
  - `infra/db/repositories/notes_repo.py`
  - `infra/integrations/use_case_matrix_sync.py`
  - `infra/db/sqlalchemy_store.py` (DB de `data/projects.db` para Use Case Matrix)

## Flujo funcional

### Viabilidad

1. **Evaluar**: calcula score + finanzas y muestra resultados (sin persistir).
2. **Guardar evaluación**: persiste proyecto + snapshot en `project_evaluations`.
3. **Aprobar**: persiste como `approved` (requiere Loop URL) + snapshot.
4. Sync a Use Case Matrix ocurre solo al guardar/aprobar (no al evaluar).

### Seguimiento Operativo

- Notas inmutables (`project_notes`).
- Captura rápida con 4 textareas (`general`, `proximo_paso`, `bloqueador`, `riesgo`).
- Resumen ejecutivo con últimas notas por proyecto.

## Persistencia

### `project_viability.db` (source of truth principal)

- `projects`
- `project_notes`
- `project_evaluations`

Migraciones idempotentes centralizadas en:
- `infra/db/migrations.py`

### `data/projects.db` (Use Case Matrix)

- `projects`
- `evaluations`

## Configuración

- `config/scoring_config.json`: configuración legacy de scoring matriz.
- `config/config.yaml`: configuración central de negocio:
  - `approval_threshold`
  - `allowed_statuses`
  - `allowed_note_types`
  - `delivery_teams`
  - `project_id_pattern`

## Tooling y calidad

Dependencias de desarrollo:

```powershell
pip install -r requirements-dev.txt
```

Comandos:

```powershell
pytest
ruff check .
black --check .
```

## Tests incluidos

- `tests/unit/test_scoring_engine.py`
  - scoring ponderado
  - componentes de viabilidad
  - cálculo financiero
- `tests/integration/test_migrations.py`
  - migraciones idempotentes
  - creación de tabla `project_evaluations`
- `tests/integration/test_repositories.py`
  - inserción/consulta de notas
  - inserción/consulta de snapshots de evaluación

## Extender la plataforma

### Nueva tab

1. Crear módulo en `ui/tabs/nueva_tab.py`.
2. Exponer función `render_*`.
3. Importar y registrar en `main.py`.
4. Si requiere persistencia, agregar repositorio/servicio en `infra/db/repositories` y `domain/services`.

### Nueva regla de score

1. Implementar en `domain/scoring/score_engine.py` o `domain/scoring/thresholds.py`.
2. Ajustar servicio que la consume (`domain/services/viability_service.py`).
3. Agregar tests unitarios en `tests/unit`.

## Notas de compatibilidad

- El refactor es incremental: se mantienen wrappers/tablas legacy para no romper runtime.
- `main.py` ya consume tabs desde `ui/tabs/*`.
- En la raíz del repo se mantiene un entrypoint único y claro:
  `start.py` -> `main.py`.
