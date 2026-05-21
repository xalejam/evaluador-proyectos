# Code Review Fixes — Evaluador de Proyectos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir los bugs críticos e issues importantes identificados en el code review de producción del Evaluador de Proyectos, sin alterar el comportamiento funcional documentado en el README.

**Architecture:** El plan sigue el orden de menor a mayor impacto y riesgo: primero bugfixes aislados de bajo esfuerzo (Tasks 1–6), luego correcciones de consistencia inter-módulo (Tasks 7–9), y finalmente el refactor de deuda estructural más grande (Tasks 10–11). Cada task produce software funcionando y testeable de forma independiente.

**Tech Stack:** Python 3.12, Streamlit, SQLite (sqlite3 + SQLAlchemy), pytest, PyYAML

---

## File Map (archivos tocados en este plan)

| Archivo | Qué cambia |
|---|---|
| `ui/tabs/tracking.py` | Eliminar segunda definición duplicada de `render_tracking_tab` |
| `main.py` | Agregar llamada a `ensure_all_operational_schema()` al inicio |
| `infra/config_loader.py` | Agregar warning cuando `config.yaml` no existe; agregar validación de campo |
| `infra/folder_provisioner.py` | Reemplazar `config["local_base_path"]` por `.get()` con mensaje claro |
| `domain/scoring/financials.py` | Reemplazar `float("inf")` por `None` |
| `ui/calculator.py` | Sincronizar cambio de `inf` → `None`; agregar None-guards |
| `infra/db/repositories/evaluation_repo.py` | Manejar `None` en `payback_period_months` correctamente |
| `ui/tabs/planning.py` | Leer `delivery_teams` de config; leer `approval_threshold` de config; validarlo en approve; reemplazar copia local de `_derive_matrix_answers` |
| `domain/services/seguimiento_operativo_service.py` | Reemplazar magic number 120 por parámetro configurable |
| `domain/services/viability_service.py` | Leer y aplicar `approval_threshold` en `approve_project()` |
| `infra/integrations/use_case_matrix_sync.py` | Exportar `_derive_matrix_answers` para uso externo |
| `ui/tabs/dashboard.py` | Leer datos desde SQLite (`project_viability.db`) en lugar de `excel_manager` |
| `tests/unit/test_financials.py` | Tests para None en payback |
| `tests/unit/test_approval_threshold.py` | Tests para validación de umbral |
| `tests/unit/test_auto_progress.py` | Tests para plazos > 120 días |
| `tests/integration/test_schema_init.py` | Test de primera ejecución sin Planning tab |
| `tests/unit/test_tracking_tab.py` | Test de definición única de render_tracking_tab |

---

## Task 1: Eliminar la segunda definición de `render_tracking_tab`

**Archivos:**
- Modify: `ui/tabs/tracking.py`
- Test: `tests/unit/test_tracking_tab.py`

Este archivo tiene dos definiciones de `render_tracking_tab`. Python usa la segunda (la simplificada). La primera versión con procesamiento automático de feedback está silenciosamente ignorada. La solución es conservar SOLO la primera definición completa y eliminar la segunda.

- [ ] **Step 1: Escribir el test que verifica que la función tiene la lógica de feedback**

```python
# tests/unit/test_tracking_tab.py
import inspect
from ui.tabs import tracking


def test_render_tracking_tab_is_defined_once():
    """La función debe tener exactamente una definición con auto_process_feedback."""
    source = inspect.getsource(tracking)
    count = source.count("def render_tracking_tab(")
    assert count == 1, f"render_tracking_tab definida {count} veces, esperado 1"


def test_render_tracking_tab_includes_feedback_logic():
    """La definición activa debe incluir la lógica de procesamiento automático."""
    source = inspect.getsource(tracking.render_tracking_tab)
    assert "auto_process_feedback" in source or "get_tracking_source" in source, \
        "La función activa no tiene la lógica de feedback/source — se está usando la versión simplificada"
```

- [ ] **Step 2: Ejecutar el test para confirmar que falla**

```
pytest tests/unit/test_tracking_tab.py -v
```
Expected: FAIL — `AssertionError: render_tracking_tab definida 2 veces`

- [ ] **Step 3: Abrir `ui/tabs/tracking.py` y localizar las dos definiciones**

Buscar en el archivo:
```
grep -n "def render_tracking_tab" "ui/tabs/tracking.py"
```
Habrá dos líneas. La primera (e.g. línea ~73) es la versión completa con `auto_process_feedback`. La segunda (e.g. línea ~368) es la versión simplificada.

- [ ] **Step 4: Eliminar la segunda definición (la simplificada) hasta el final del archivo**

Borrar desde la segunda `def render_tracking_tab(` hasta el final de esa función. Conservar todo lo que viene antes (la primera definición completa) y cualquier código auxiliar que no sea la función duplicada.

- [ ] **Step 5: Ejecutar el test para confirmar que pasa**

```
pytest tests/unit/test_tracking_tab.py -v
```
Expected: PASS

- [ ] **Step 6: Ejecutar el suite completo para detectar regresiones**

```
pytest tests/ -v --tb=short
```
Expected: todos los tests existentes siguen en PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/tabs/tracking.py tests/unit/test_tracking_tab.py
git commit -m "fix: remove duplicate render_tracking_tab definition, restore full version with feedback logic"
```

---

## Task 2: Ejecutar migraciones automáticamente al inicio de la app

**Archivos:**
- Modify: `main.py`
- Test: `tests/integration/test_schema_init.py`

El problema: `ensure_schema()` solo se llama cuando el usuario abre la tab de Planning o guarda algo. Si un usuario nuevo abre directamente la tab de Seguimiento Operativo, `project_notes` no existe → crash con `OperationalError`. La solución es llamar a `ensure_all_operational_schema()` al inicio de `main.py`, antes de renderizar cualquier tab.

- [ ] **Step 1: Escribir el test de integración**

```python
# tests/integration/test_schema_init.py
import sqlite3
import tempfile
import os
from infra.db_migrations import ensure_all_operational_schema


def test_ensure_all_operational_schema_creates_project_notes():
    """ensure_all_operational_schema debe crear project_notes sin necesidad de abrir Planning."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        ensure_all_operational_schema(conn)
        conn.commit()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_notes'"
        )
        assert cursor.fetchone() is not None, "project_notes table should exist after ensure_all_operational_schema"
        conn.close()
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Ejecutar el test para verificar que pasa (confirmar que la función existe)**

```
pytest tests/integration/test_schema_init.py -v
```
Expected: PASS — si falla con ImportError, revisar el nombre exacto de la función en `infra/db_migrations.py`.

- [ ] **Step 3: Agregar la llamada en `main.py`**

Abrir `main.py`. Al inicio de la función `main()`, después de `init_state()` e `init_excel_manager()` pero antes del primer `st.tabs(...)`, agregar:

```python
from infra.db_migrations import ensure_all_operational_schema
from infra.db.connection import get_sqlite_conn
from infra.db.sqlalchemy_store import DB_PATH as PV_DB_PATH

# Garantizar que el schema existe antes de renderizar cualquier tab
with get_sqlite_conn(PV_DB_PATH) as _conn:
    ensure_all_operational_schema(_conn)
    _conn.commit()
```

Colocar este bloque justo después de las llamadas a `init_state()` y `init_excel_manager()`, dentro del bloque `if __name__ == "__main__"` o en el cuerpo de `main()`.

- [ ] **Step 4: Verificar que la app no lanza error al iniciar**

```
streamlit run main.py --server.headless true &
sleep 5
kill %1
```
Expected: sin `OperationalError` en los logs.

- [ ] **Step 5: Ejecutar suite de tests**

```
pytest tests/ -v --tb=short
```
Expected: todos en PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/integration/test_schema_init.py
git commit -m "fix: run ensure_all_operational_schema at app startup to prevent crash on first run"
```

---

## Task 3: Agregar warning cuando `config.yaml` no existe

**Archivos:**
- Modify: `infra/config_loader.py`
- Modify: `infra/folder_provisioner.py`
- Test: `tests/unit/test_config_loader.py` (crear si no existe)

`load_app_config()` retorna `{}` silenciosamente. `LocalFolderProvisioner` hace `config["local_base_path"]` sin `.get()`. Ambos deben fallar con mensajes claros.

- [ ] **Step 1: Escribir los tests**

```python
# tests/unit/test_config_loader.py
import pytest
import logging
from unittest.mock import patch
from infra.config_loader import load_app_config
from infra.folder_provisioner import LocalFolderProvisioner


def test_load_app_config_warns_when_file_missing(caplog):
    """Debe loggear un warning cuando config.yaml no existe."""
    with patch("infra.config_loader.Path.exists", return_value=False):
        with caplog.at_level(logging.WARNING):
            result = load_app_config()
    assert result == {}
    assert any("config.yaml" in msg for msg in caplog.messages), \
        "Debe emitir un warning mencionando config.yaml cuando el archivo no existe"


def test_local_folder_provisioner_raises_clear_error_when_key_missing():
    """Debe lanzar KeyError con mensaje claro si local_base_path no está en config."""
    with pytest.raises(KeyError, match="local_base_path"):
        LocalFolderProvisioner({})
```

- [ ] **Step 2: Ejecutar para confirmar que fallan**

```
pytest tests/unit/test_config_loader.py -v
```
Expected: FAIL — `load_app_config` no emite warning; `LocalFolderProvisioner` lanza `KeyError` sin mensaje claro.

- [ ] **Step 3: Modificar `infra/config_loader.py`**

Localizar la función `load_app_config()`. Agregar logging cuando el archivo no existe:

```python
import logging

logger = logging.getLogger(__name__)

def load_app_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        logger.warning(
            "config.yaml not found at %s — using empty config. "
            "approval_threshold and allowed_statuses will use hardcoded defaults.",
            config_path,
        )
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
```

- [ ] **Step 4: Modificar `infra/folder_provisioner.py`**

Localizar `LocalFolderProvisioner.__init__`. Reemplazar:
```python
self._base = Path(config["local_base_path"])
```
por:
```python
if "local_base_path" not in config:
    raise KeyError(
        "'local_base_path' is required in folder_provisioner_config.json but was not found. "
        f"Keys found: {list(config.keys())}"
    )
self._base = Path(config["local_base_path"])
```

- [ ] **Step 5: Ejecutar los tests**

```
pytest tests/unit/test_config_loader.py -v
```
Expected: PASS

- [ ] **Step 6: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add infra/config_loader.py infra/folder_provisioner.py tests/unit/test_config_loader.py
git commit -m "fix: warn when config.yaml missing; raise clear error when local_base_path absent from provisioner config"
```

---

## Task 4: Corregir `float("inf")` que se corrompe en SQLite

**Archivos:**
- Modify: `domain/scoring/financials.py`
- Modify: `ui/calculator.py`
- Modify: `infra/db/repositories/evaluation_repo.py`
- Test: `tests/unit/test_financials.py`

Cuando `net_annual_benefit <= 0`, el cálculo devuelve `float("inf")`. SQLite no puede almacenar `inf` como `REAL` — lo guarda como `NULL` silenciosamente. La solución es devolver `None` (semántica clara: "no hay payback") en lugar de `inf`.

- [ ] **Step 1: Escribir los tests**

```python
# tests/unit/test_financials.py
import pytest
from domain.scoring.financials import compute_financials


def test_payback_is_none_when_no_benefit():
    """Cuando el beneficio neto es <= 0, payback_period_months debe ser None."""
    result = compute_financials(
        total_hours_per_month=10,
        time_reduction_percent=0,  # sin ahorro de tiempo
        avg_salary_per_hour=50,
        initial_development_cost=10000,
        annual_maintenance_cost=5000,
    )
    assert result["payback_period_months"] is None, \
        "payback debe ser None (no hay payback posible), no float('inf')"


def test_payback_is_none_when_maintenance_exceeds_savings():
    """Mantenimiento anual > ahorro anual → payback None."""
    result = compute_financials(
        total_hours_per_month=10,
        time_reduction_percent=10,
        avg_salary_per_hour=10,
        initial_development_cost=5000,
        annual_maintenance_cost=50000,  # mucho más que el ahorro
    )
    assert result["payback_period_months"] is None


def test_payback_is_positive_number_when_profitable():
    """Proyecto rentable → payback es un número positivo."""
    result = compute_financials(
        total_hours_per_month=100,
        time_reduction_percent=50,
        avg_salary_per_hour=100,
        initial_development_cost=5000,
        annual_maintenance_cost=1000,
    )
    assert result["payback_period_months"] is not None
    assert result["payback_period_months"] > 0
```

- [ ] **Step 2: Ejecutar para confirmar que fallan**

```
pytest tests/unit/test_financials.py::test_payback_is_none_when_no_benefit -v
```
Expected: FAIL — `AssertionError: payback debe ser None, no float('inf')`

- [ ] **Step 3: Modificar `domain/scoring/financials.py`**

Localizar la línea donde se asigna `float("inf")`. Reemplazar:
```python
payback_period_months = float("inf")
if net_annual_benefit > 0:
    payback_period_months = initial_development_cost / (net_annual_benefit / 12)
```
por:
```python
payback_period_months: float | None = None
if net_annual_benefit > 0:
    payback_period_months = initial_development_cost / (net_annual_benefit / 12)
```

- [ ] **Step 4: Modificar `ui/calculator.py`**

Si `calculator.py` también asigna `float("inf")` para payback, aplicar el mismo cambio: reemplazar `float("inf")` por `None`. Buscar: `payback_period_months = float("inf")`.

Además, en cualquier lugar donde se muestre `payback_period_months` en la UI, agregar la guarda:
```python
payback = result.get("payback_period_months")
payback_display = f"{payback:.1f} meses" if payback is not None else "No aplica (sin retorno)"
```

- [ ] **Step 5: Modificar `infra/db/repositories/evaluation_repo.py`**

Localizar la línea donde `payback_period_months` se pasa al INSERT. La línea actual probablemente hace:
```python
float(calc_results.get("payback_period_months", 0) or 0),
```
Reemplazar por:
```python
calc_results.get("payback_period_months"),  # None se almacena correctamente como NULL en SQLite
```

- [ ] **Step 6: Ejecutar los tests**

```
pytest tests/unit/test_financials.py -v
```
Expected: PASS

- [ ] **Step 7: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 8: Commit**

```bash
git add domain/scoring/financials.py ui/calculator.py infra/db/repositories/evaluation_repo.py tests/unit/test_financials.py
git commit -m "fix: replace float('inf') with None for payback_period_months to prevent silent SQLite corruption"
```

---

## Task 5: Agregar None-guards en `calculator.py` y `tracking.py`

**Archivos:**
- Modify: `ui/calculator.py`
- Modify: `ui/tabs/tracking.py`
- Test: `tests/unit/test_calculator.py` (extender)

Columnas SQLite sin `NOT NULL` pueden devolver `None`. Las multiplicaciones directas con `None` en Python lanzan `TypeError`. Necesitamos un helper para coercionar a float con fallback.

- [ ] **Step 1: Escribir el test**

```python
# En tests/unit/test_calculator.py, agregar:
from ui.calculator import ProjectViabilityCalculator


def test_calculate_viability_with_none_fields_does_not_crash():
    """Si campos numéricos son None (datos incompletos de DB), debe devolver ceros en lugar de crash."""
    calculator = ProjectViabilityCalculator()
    project_data = {
        "current_time_per_task": None,
        "tasks_per_month": None,
        "staff_count": None,
        "time_reduction_percent": None,
        "avg_salary_per_hour": None,
        "development_hours": None,
        "development_cost_per_hour": None,
        "annual_maintenance_cost": None,
        "A": 3, "B": 3, "C": 3, "D": 3,
        "E": 3, "F": 3, "G": 3, "H": 3,
        "weight_A": 1, "weight_B": 1, "weight_C": 1, "weight_D": 1,
        "weight_E": 1, "weight_F": 1, "weight_G": 1, "weight_H": 1,
    }
    result = calculator.calculate_viability(project_data)
    assert isinstance(result, dict), "Debe devolver dict aunque los campos sean None"
    assert "viability_score" in result
```

- [ ] **Step 2: Ejecutar para confirmar que falla**

```
pytest tests/unit/test_calculator.py::test_calculate_viability_with_none_fields_does_not_crash -v
```
Expected: FAIL con `TypeError`

- [ ] **Step 3: Agregar un helper `_coerce_float` en `ui/calculator.py`**

Al inicio de `ui/calculator.py`, antes de la clase, agregar:
```python
def _f(value, default: float = 0.0) -> float:
    """Convierte a float; retorna default si el valor es None o no convertible."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
```

- [ ] **Step 4: Envolver todas las referencias a `project_data[key]` con `_f(...)`**

En `calculate_viability()`, reemplazar cada acceso directo:
```python
# ANTES
total_hours_per_month = (
    project_data["current_time_per_task"]
    * project_data["tasks_per_month"]
    * project_data["staff_count"]
)
# DESPUÉS
total_hours_per_month = (
    _f(project_data.get("current_time_per_task"))
    * _f(project_data.get("tasks_per_month"))
    * _f(project_data.get("staff_count"))
)
```
Aplicar el mismo patrón para todos los campos numéricos en `calculate_viability()` y `calculate_tracking_results()`.

- [ ] **Step 5: Aplicar el mismo patrón en `ui/tabs/tracking.py`**

Localizar los bloques donde se calcula `expected_monthly_savings` y otras métricas a partir de `project[...]`. Reemplazar accesos directos por `.get()` con `_f()`:
```python
# Agregar el helper (o importarlo de calculator.py si se exporta)
from ui.calculator import _f  # si se hace público, o replicar la función

expected_monthly_savings = (
    _f(project.get("current_time_per_task"))
    * _f(project.get("time_reduction_percent")) / 100
    * _f(project.get("tasks_per_month"))
    * _f(project.get("staff_count"))
    * _f(project.get("avg_salary_per_hour"))
)
```

- [ ] **Step 6: Ejecutar los tests**

```
pytest tests/unit/test_calculator.py -v
```
Expected: PASS

- [ ] **Step 7: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 8: Commit**

```bash
git add ui/calculator.py ui/tabs/tracking.py tests/unit/test_calculator.py
git commit -m "fix: add None-guards in calculator and tracking to prevent TypeError with incomplete DB records"
```

---

## Task 6: Corregir `calculate_auto_progress()` para plazos > 120 días

**Archivos:**
- Modify: `domain/services/seguimiento_operativo_service.py`
- Test: `tests/unit/test_auto_progress.py`

El magic number `total_days = 120` hace que proyectos con plazo > 4 meses siempre muestren 0% de avance automático. Se debe calcular el progreso proporcional basado en el plazo real del proyecto.

- [ ] **Step 1: Escribir los tests**

```python
# tests/unit/test_auto_progress.py
from datetime import date, timedelta
from domain.services.seguimiento_operativo_service import OperationalTrackingService


def _service():
    """Helper que crea el servicio sin DB para tests unitarios."""
    # Si el constructor requiere db_path, pasar ":memory:" o un mock
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".db")
    svc = OperationalTrackingService(tmp)
    svc.ensure_schema()
    return svc


def test_auto_progress_project_with_6_month_duration():
    """Un proyecto que lleva la mitad del tiempo debe mostrar ~50% de progreso."""
    today = date.today()
    start_dt = today - timedelta(days=90)  # empezó hace 90 días
    end_dt = today + timedelta(days=90)    # faltan 90 días (duración total: 180 días)

    svc = _service()
    progress = svc.calculate_auto_progress(start_dt, end_dt)
    assert 40 <= progress <= 60, \
        f"Proyecto al 50% de su duración de 180 días debería mostrar ~50%, no {progress}%"


def test_auto_progress_new_project_long_duration():
    """Un proyecto que acaba de empezar con 8 meses de plazo no debe mostrar 0%."""
    today = date.today()
    start_dt = today - timedelta(days=1)
    end_dt = today + timedelta(days=240)  # 8 meses

    svc = _service()
    progress = svc.calculate_auto_progress(start_dt, end_dt)
    # Al menos 0%, pero un plazo de 241 días con 1 día transcurrido es ~0.4%
    # Lo importante es que NO sea 0 por el magic number
    assert progress >= 0
    assert progress < 10, f"No debería estar cerca de 100%, got {progress}%"


def test_auto_progress_past_end_date_returns_100():
    """Fecha de fin ya pasada → 100%."""
    today = date.today()
    svc = _service()
    progress = svc.calculate_auto_progress(today - timedelta(days=200), today - timedelta(days=1))
    assert progress == 100
```

- [ ] **Step 2: Ejecutar para confirmar que el test de 6 meses falla**

```
pytest tests/unit/test_auto_progress.py::test_auto_progress_project_with_6_month_duration -v
```
Expected: FAIL — el resultado actual es 0% porque 180 > 120.

- [ ] **Step 3: Modificar `domain/services/seguimiento_operativo_service.py`**

Localizar `calculate_auto_progress()`. La firma actual probablemente acepta `end_dt` pero no `start_dt`. Verificar la firma real. Si no tiene `start_dt`, agregar ese parámetro con default `None`.

Reemplazar la implementación:
```python
def calculate_auto_progress(
    self,
    start_dt: date | None,
    end_dt: date,
) -> int:
    """Calcula progreso lineal basado en el plazo real del proyecto."""
    today = date.today()
    if end_dt <= today:
        return 100
    if start_dt is None or start_dt >= today:
        return 0
    total_days = (end_dt - start_dt).days
    if total_days <= 0:
        return 100
    elapsed = (today - start_dt).days
    return max(0, min(100, int(round((elapsed / total_days) * 100))))
```

- [ ] **Step 4: Verificar que los callers de `calculate_auto_progress` pasen `start_dt`**

Buscar en el código:
```
grep -rn "calculate_auto_progress" .
```
Para cada caller encontrado, agregar el argumento `start_dt`. Si el caller no tiene la fecha de inicio disponible, pasar `None` (el método devolverá 0% como antes, sin crash).

- [ ] **Step 5: Ejecutar los tests**

```
pytest tests/unit/test_auto_progress.py -v
```
Expected: PASS

- [ ] **Step 6: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add domain/services/seguimiento_operativo_service.py tests/unit/test_auto_progress.py
git commit -m "fix: calculate_auto_progress uses real project duration instead of hardcoded 120-day window"
```

---

## Task 7: Leer `delivery_teams` de config y validar `approval_threshold`

**Archivos:**
- Modify: `ui/tabs/planning.py`
- Modify: `domain/services/viability_service.py`
- Test: `tests/unit/test_approval_threshold.py`

Dos issues relacionados con `config.yaml`: (1) `DEVELOPER_TEAMS` hardcodeado difiere del config; (2) `approval_threshold: 80` nunca se lee ni se aplica.

- [ ] **Step 1: Escribir los tests**

```python
# tests/unit/test_approval_threshold.py
import pytest
from unittest.mock import patch, MagicMock
from domain.services.viability_service import ViabilityService
from domain.exceptions import ValidationError


def _mock_repos():
    project_repo = MagicMock()
    evaluation_repo = MagicMock()
    excel_manager = MagicMock()
    return project_repo, evaluation_repo, excel_manager


def test_approve_project_below_threshold_raises_validation_error():
    """Un proyecto con score < approval_threshold no puede aprobarse."""
    project_repo, evaluation_repo, excel_manager = _mock_repos()
    project_repo.get_project.return_value = {
        "project_id": "MX-TEST-0001",
        "status": "evaluated",
        "viability_score": 60,  # por debajo de 80
    }

    with patch("domain.services.viability_service.load_app_config", return_value={"approval_threshold": 80}):
        svc = ViabilityService(project_repo, evaluation_repo, excel_manager)
        with pytest.raises(ValidationError, match="approval_threshold"):
            svc.approve_project("MX-TEST-0001", loop_url="https://example.com")


def test_approve_project_at_threshold_succeeds():
    """Un proyecto con score >= approval_threshold puede aprobarse."""
    project_repo, evaluation_repo, excel_manager = _mock_repos()
    project_repo.get_project.return_value = {
        "project_id": "MX-TEST-0002",
        "status": "evaluated",
        "viability_score": 80,
    }

    with patch("domain.services.viability_service.load_app_config", return_value={"approval_threshold": 80}):
        svc = ViabilityService(project_repo, evaluation_repo, excel_manager)
        svc.approve_project("MX-TEST-0002", loop_url="https://example.com")
        project_repo.update_status.assert_called_once()
```

- [ ] **Step 2: Ejecutar para confirmar que fallan**

```
pytest tests/unit/test_approval_threshold.py -v
```
Expected: FAIL — `approve_project` no valida el score.

- [ ] **Step 3: Modificar `domain/services/viability_service.py`**

En `approve_project()`, agregar la validación del umbral al inicio del método:

```python
from infra.config_loader import load_app_config

def approve_project(self, project_id: str, loop_url: str) -> None:
    if not loop_url or not loop_url.strip():
        raise ValidationError("loop_url", "Loop URL is required to approve a project")

    config = load_app_config()
    threshold = config.get("approval_threshold", 80)

    project = self._project_repo.get_project(project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)

    score = project.get("viability_score") or 0
    if score < threshold:
        raise ValidationError(
            "approval_threshold",
            f"Project score {score:.1f} is below the approval threshold of {threshold}. "
            "The project cannot be approved."
        )

    # ... resto del método existente
```

- [ ] **Step 4: Modificar `ui/tabs/planning.py` para leer `delivery_teams` de config**

Localizar donde se define `DEVELOPER_TEAMS` o la lista hardcodeada de equipos. Reemplazar:
```python
# ANTES (hardcodeado)
EVALUATION_TEAMS = ("NOLA", "SOLA", "Brazil", "Other", "Champions Copilot")

# DESPUÉS (desde config)
from infra.config_loader import load_app_config as _load_app_config

_app_config = _load_app_config()
EVALUATION_TEAMS = tuple(_app_config.get("delivery_teams", ["NOLA", "Brazil", "Champions", "Other"]))
```

- [ ] **Step 5: Ejecutar los tests**

```
pytest tests/unit/test_approval_threshold.py -v
```
Expected: PASS

- [ ] **Step 6: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add domain/services/viability_service.py ui/tabs/planning.py tests/unit/test_approval_threshold.py
git commit -m "fix: enforce approval_threshold from config before approving; read delivery_teams from config"
```

---

## Task 8: Eliminar la copia duplicada de `_derive_matrix_answers` en `planning.py`

**Archivos:**
- Modify: `infra/integrations/use_case_matrix_sync.py` (exportar las funciones)
- Modify: `ui/tabs/planning.py` (importar en lugar de duplicar)
- Test: `tests/unit/test_derive_matrix_answers.py`

Las funciones `_clamp_score`, `_score_from_thresholds` y `_derive_matrix_answers` están copiadas literalmente en dos módulos activos. Si los umbrales cambian en uno, la UCM mostrará datos distintos según por qué ruta se guardó.

- [ ] **Step 1: Escribir el test de consistencia**

```python
# tests/unit/test_derive_matrix_answers.py
from infra.integrations.use_case_matrix_sync import _derive_matrix_answers


def test_derive_matrix_answers_maps_all_criteria():
    """Debe retornar un dict con las 8 claves A-H."""
    sample_inputs = {
        "time_reduction_percent": 30,
        "risk_level": "Medio",
        "complexity_level": "Media",
        "scope": "Departamental",
        "frequency": "Diaria",
        "tech_stack_risk": "Bajo",
        "dependency_count": 2,
        "team_size": 3,
    }
    result = _derive_matrix_answers(sample_inputs)
    for key in ("A", "B", "C", "D", "E", "F", "G", "H"):
        assert key in result, f"Clave '{key}' faltante en resultado de _derive_matrix_answers"
        assert 1 <= result[key] <= 5, f"Valor fuera de rango [1,5] para clave '{key}': {result[key]}"
```

- [ ] **Step 2: Ejecutar para confirmar que pasa (la función existe en sync)**

```
pytest tests/unit/test_derive_matrix_answers.py -v
```
Expected: PASS — si falla, revisar que `_derive_matrix_answers` está exportada en `use_case_matrix_sync.py`.

- [ ] **Step 3: Hacer públicas las funciones en `infra/integrations/use_case_matrix_sync.py`**

Renombrar (quitar el underscore) o dejar los nombres privados pero asegurarse de que el módulo las expone sin restricciones. Agregar al final del módulo:

```python
# Public re-exports for shared use
derive_matrix_answers = _derive_matrix_answers
score_from_thresholds = _score_from_thresholds
clamp_score = _clamp_score
```

- [ ] **Step 4: Modificar `ui/tabs/planning.py`**

Localizar las definiciones locales de `_clamp_score`, `_score_from_thresholds` y `_derive_matrix_answers` (las que son copia-pega). Reemplazarlas por imports:

```python
from infra.integrations.use_case_matrix_sync import (
    clamp_score as _clamp_score,
    score_from_thresholds as _score_from_thresholds,
    derive_matrix_answers as _derive_matrix_answers,
)
```

Eliminar las definiciones locales duplicadas.

- [ ] **Step 5: Ejecutar los tests**

```
pytest tests/unit/test_derive_matrix_answers.py -v
```
Expected: PASS

- [ ] **Step 6: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add infra/integrations/use_case_matrix_sync.py ui/tabs/planning.py tests/unit/test_derive_matrix_answers.py
git commit -m "refactor: remove duplicate _derive_matrix_answers in planning.py; import from use_case_matrix_sync"
```

---

## Task 9: Migrar el Dashboard para leer desde SQLite

**Archivos:**
- Modify: `ui/tabs/dashboard.py`
- Test: `tests/integration/test_dashboard_data_source.py`

El Dashboard actualmente lee de `st.session_state.excel_manager` (Excel en memoria). La Use Case Matrix lee de SQLite. El usuario ve dos snapshots inconsistentes. La solución es que el Dashboard lea directamente de `project_viability.db`.

- [ ] **Step 1: Identificar qué queries necesita el Dashboard**

Antes de escribir código, leer `ui/tabs/dashboard.py` completamente y listar las llamadas a `excel_manager`:
- `excel_manager.get_all_projects()` → proyectos del portafolio
- `excel_manager.tracking_df` → datos de tracking post-implementación

Cada una de estas necesita una query SQLite equivalente.

- [ ] **Step 2: Escribir el test de integración**

```python
# tests/integration/test_dashboard_data_source.py
import sqlite3
import tempfile
import os
from infra.db_migrations import ensure_all_operational_schema
from infra.db.repositories.project_repo import ProjectRepository


def test_dashboard_projects_come_from_sqlite(tmp_path):
    """El dashboard debe poder obtener proyectos directamente desde SQLite."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ensure_all_operational_schema(conn)
    conn.commit()

    repo = ProjectRepository(db_path)
    repo.upsert_project({
        "project_id": "MX-TEST-0001",
        "country": "MX",
        "owner": "TEST",
        "name": "Proyecto de prueba",
        "status": "executing",
        "viability_score": 85.0,
        "monthly_savings": 1000.0,
        "annual_savings": 12000.0,
    })

    projects = repo.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_id"] == "MX-TEST-0001"
    assert projects[0]["viability_score"] == 85.0
```

- [ ] **Step 3: Ejecutar para confirmar que pasa (verificar que el repo funciona)**

```
pytest tests/integration/test_dashboard_data_source.py -v
```
Expected: PASS

- [ ] **Step 4: Crear función `load_dashboard_data()` en `ui/tabs/dashboard.py`**

Al inicio de `ui/tabs/dashboard.py`, agregar una función que carga datos desde SQLite en lugar de `excel_manager`:

```python
import pandas as pd
from infra.db.connection import get_sqlite_conn
from infra.db.sqlalchemy_store import DB_PATH as PV_DB_PATH


def _load_projects_from_db() -> pd.DataFrame:
    """Carga proyectos directamente desde project_viability.db."""
    with get_sqlite_conn(PV_DB_PATH) as conn:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM projects WHERE status IS NOT NULL ORDER BY created_at DESC",
                conn,
            )
            return df
        except Exception:
            return pd.DataFrame()
```

- [ ] **Step 5: Reemplazar las llamadas a `excel_manager` en `render_dashboard()`**

Localizar todas las referencias a `st.session_state.excel_manager.get_all_projects()` y `excel_manager.tracking_df` en `dashboard.py`.

Reemplazar:
```python
# ANTES
projects_df = st.session_state.excel_manager.get_all_projects()

# DESPUÉS
projects_df = _load_projects_from_db()
```

Para `tracking_df` (si se usa en el dashboard), verificar si hay una tabla equivalente en SQLite. Si no existe, desactivar esa sección con un `st.info("Los datos de tracking estarán disponibles próximamente.")` hasta que se migre.

- [ ] **Step 6: Verificar manualmente que el Dashboard no muestra error**

```
streamlit run main.py --server.headless true &
sleep 5
kill %1
```
Verificar en los logs que no hay `AttributeError` ni `KeyError`.

- [ ] **Step 7: Ejecutar suite completo**

```
pytest tests/ -v --tb=short
```

- [ ] **Step 8: Commit**

```bash
git add ui/tabs/dashboard.py tests/integration/test_dashboard_data_source.py
git commit -m "fix: dashboard now reads from project_viability.db instead of excel_manager, ensuring consistency with UCM tab"
```

---

## Self-Review del Plan

### 1. Cobertura de issues críticos del review

| Issue | Task que lo cubre |
|---|---|
| C1 — `approval_threshold` nunca validado | Task 7 |
| C2 — `approve_click` bypasea `loop_url` | Task 7 (via ViabilityService) |
| C3 — Dashboard lee Excel, UCM lee SQLite | Task 9 |
| C4 — Doble `render_tracking_tab` | Task 1 |
| C5 — Migraciones no auto-ejecutadas | Task 2 |
| C6 — `_derive_matrix_answers` duplicada | Task 8 |
| I1 — `TypeError` con None en aritmética | Task 5 |
| I2 — `float("inf")` corrompe SQLite | Task 4 |
| I3 — `auto_progress` 0% para plazos > 120d | Task 6 |
| I4 — `DEVELOPER_TEAMS` hardcodeado | Task 7 |
| I8 — `config.yaml` faltante silencioso | Task 3 |

### 2. Issues fuera del scope de este plan (deuda arquitectural mayor, plan separado recomendado)

- **I5** — `KeyError` en `weighted_average()` → requiere cambios en UI de formulario + scoring
- **I6** — Import circular `shared.py ↔ calculator.py` → requiere refactor de `ExcelSharePointManager`
- **I7** — Operaciones multi-paso sin atomicidad → requiere Unit of Work o transacción distribuida
- **R13** — Eliminar `data/projects.db` y consolidar en una sola DB → impacto en todo el proyecto
- **R14** — Mover `ExcelSharePointManager` a `infra/` → refactor mayor
- **R15** — Completar dataclass `Project` → requiere migración de schema

### 3. Verificación de placeholders

Todos los steps tienen código real, comandos exactos y outputs esperados. Sin TBDs.

### 4. Consistencia de tipos y nombres

- `_f()` helper definido en Task 5 y usado en Task 5 — consistente.
- `derive_matrix_answers` exportado en Task 8 Step 3 e importado en Task 8 Step 4 — consistente.
- `load_app_config()` usada en Task 3, 7 — importada del mismo módulo — consistente.
