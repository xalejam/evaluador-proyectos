# Plan 1: Desacoplar Dominio de Streamlit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar las dependencias de `streamlit` y `ui/` desde los servicios de dominio para que el dominio sea testeable e independiente de la capa de presentación.

**Architecture:** `viability_service.py` actualmente accede a `st.session_state.calculator` y `st.session_state.excel_manager`. Se extraen esas dependencias como parámetros explícitos. `feedback_service.py` importa desde `ui/tabs/` — se mueve `FeedbackProcessor` a `domain/` o `infra/`. Ningún cambio en la UI salvo pasar los objetos como argumentos.

**Tech Stack:** Python stdlib, pytest, sin nuevas dependencias.

---

## Estructura de archivos

| Archivo | Acción | Cambio |
|---|---|---|
| `domain/services/viability_service.py` | Modificar | Eliminar `import streamlit`; recibir `calculator` y `excel_manager` como parámetros |
| `domain/services/feedback_service.py` | Modificar | Eliminar import desde `ui/tabs/`; mover `FeedbackProcessor` o importar desde `infra/` |
| `infra/feedback_processor.py` | Crear | Mover la clase `FeedbackProcessor` desde `ui/tabs/feedback_processor.py` |
| `ui/tabs/feedback_processor.py` | Modificar | Re-exportar desde `infra/` para no romper imports existentes |
| `ui/tabs/planning.py` | Modificar | Pasar `calculator` y `excel_manager` explícitamente a `viability_service` |
| `tests/unit/test_viability_service.py` | Crear | Tests unitarios sin Streamlit |

---

## Task 1: Desacoplar `viability_service.py` de `st.session_state`

**Files:**
- Modify: `domain/services/viability_service.py`
- Test: `tests/unit/test_viability_service.py`

### 1a — Leer el archivo actual primero
- [ ] **Step 1: Leer `domain/services/viability_service.py` completo**

Lee el archivo para entender las firmas actuales antes de modificar.

### 1b — Escribir tests que definan la interfaz objetivo

- [ ] **Step 2: Crear `tests/unit/test_viability_service.py`**

```python
# tests/unit/test_viability_service.py
"""Tests para viability_service sin dependencia de Streamlit."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.services.viability_service import evaluate_and_save


class FakeCalculator:
    def calculate_viability(self, inputs: dict) -> dict:
        return {
            "viability_score": 75,
            "priority": "Alta",
            "monthly_savings": 1000.0,
            "annual_savings": 12000.0,
            "payback_period_months": 6,
            "roi_first_year": 120.0,
            "hours_saved_per_month": 40.0,
            "initial_development_cost": 5000.0,
            "recommendation": "Recomendado",
        }


class FakeExcelManager:
    def __init__(self):
        self._projects = {}

    def project_exists(self, project_id: str) -> bool:
        return project_id in self._projects

    def save_project(self, data: dict) -> str:
        pid = data.get("project_id", "MX-TEST-0001")
        self._projects[pid] = data
        return pid

    def get_project(self, project_id: str) -> dict:
        return self._projects.get(project_id, {})


def test_evaluate_and_save_returns_project_id(tmp_path):
    calc = FakeCalculator()
    mgr = FakeExcelManager()
    inputs = {
        "name": "Test Project",
        "country": "MX",
        "owner": "TEST",
        "time_reduction_percent": 50,
        "risk_level": 2,
        "implementation_complexity": 3,
        "current_time_per_task": 2.0,
        "tasks_per_month": 20,
        "staff_count": 3,
        "avg_salary_per_hour": 25.0,
        "development_hours": 100,
        "development_cost_per_hour": 50.0,
        "maintenance_monthly": 200.0,
        "status": "approved",
    }
    result = evaluate_and_save(inputs=inputs, calculator=calc, excel_manager=mgr)
    assert result["project_id"] is not None
    assert result["viability_score"] == 75


def test_evaluate_and_save_does_not_import_streamlit():
    import domain.services.viability_service as vsm
    import ast, inspect
    source = inspect.getsource(vsm)
    assert "import streamlit" not in source
    assert "st.session_state" not in source
```

- [ ] **Step 3: Ejecutar tests para verificar que fallan**

```
.venv\Scripts\pytest tests/unit/test_viability_service.py -v
```

Expected: `ImportError` o `AssertionError` — el módulo aún importa streamlit.

### 1c — Implementar

- [ ] **Step 4: Reemplazar `domain/services/viability_service.py`**

Lee el archivo actual. Elimina `import streamlit as st` y `st.session_state.*`. Cambia todas las funciones que usaban `st.session_state.calculator` y `st.session_state.excel_manager` para recibir esos objetos como parámetros. Expón una función pública `evaluate_and_save(inputs, calculator, excel_manager)` que devuelva un dict con `project_id` y los resultados calculados.

Ejemplo de la función refactorizada:

```python
# domain/services/viability_service.py
"""Servicio de evaluación y guardado de proyectos. Sin dependencias de UI."""
from typing import Any, Protocol


class Calculator(Protocol):
    def calculate_viability(self, inputs: dict) -> dict: ...


class ExcelManager(Protocol):
    def project_exists(self, project_id: str) -> bool: ...
    def save_project(self, data: dict) -> str: ...
    def get_project(self, project_id: str) -> dict: ...


def evaluate_and_save(
    inputs: dict,
    calculator: Calculator,
    excel_manager: ExcelManager,
) -> dict:
    """Calcula viabilidad y persiste el proyecto. Retorna dict con project_id + resultados."""
    results = calculator.calculate_viability(inputs)
    merged = {**inputs, **results}
    project_id = excel_manager.save_project(merged)
    return {"project_id": project_id, **results}
```

> **Nota**: Lee el archivo actual completo antes de escribir la versión final — puede tener más funciones que el ejemplo anterior. El objetivo es eliminar `streamlit` sin perder funcionalidad.

- [ ] **Step 5: Ejecutar tests**

```
.venv\Scripts\pytest tests/unit/test_viability_service.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add domain/services/viability_service.py tests/unit/test_viability_service.py
git commit -m "refactor: decouple viability_service from streamlit session_state"
```

---

## Task 2: Desacoplar `feedback_service.py` de `ui/tabs/`

**Files:**
- Create: `infra/feedback_processor.py`
- Modify: `ui/tabs/feedback_processor.py`
- Modify: `domain/services/feedback_service.py`

- [ ] **Step 1: Leer `ui/tabs/feedback_processor.py`**

Lee el archivo para entender qué exporta `FeedbackProcessor`.

- [ ] **Step 2: Crear `infra/feedback_processor.py`**

Copia la clase `FeedbackProcessor` desde `ui/tabs/feedback_processor.py` a `infra/feedback_processor.py`. No modifiques la lógica — solo mueve la clase.

```python
# infra/feedback_processor.py
"""FeedbackProcessor movido desde ui/tabs/ para romper dependencia domain→ui."""
# [pegar aquí la clase FeedbackProcessor completa desde ui/tabs/feedback_processor.py]
```

- [ ] **Step 3: Hacer que `ui/tabs/feedback_processor.py` re-exporte desde `infra/`**

Al final del archivo `ui/tabs/feedback_processor.py`, **conserva todo el código existente** pero agrega al inicio:

```python
# Re-exporta para compatibilidad con imports existentes
from infra.feedback_processor import FeedbackProcessor  # noqa: F401
```

Si la clase ya está definida en ese archivo, elimina la definición original y deja solo el re-export.

- [ ] **Step 4: Corregir `domain/services/feedback_service.py`**

Cambiar:
```python
from ui.tabs.feedback_processor import FeedbackProcessor
```
Por:
```python
from infra.feedback_processor import FeedbackProcessor
```

- [ ] **Step 5: Verificar que no se rompieron imports**

```
python -c "from domain.services.feedback_service import *; print('OK')"
python -c "from ui.tabs.feedback_processor import FeedbackProcessor; print('OK')"
```

Expected: `OK` en ambos.

- [ ] **Step 6: Commit**

```bash
git add infra/feedback_processor.py ui/tabs/feedback_processor.py domain/services/feedback_service.py
git commit -m "refactor: move FeedbackProcessor to infra/ to fix domain→ui dependency inversion"
```

---

## Task 3: Actualizar `ui/tabs/planning.py` para pasar dependencias explícitamente

**Files:**
- Modify: `ui/tabs/planning.py` (en el punto donde se llama a `viability_service`)

- [ ] **Step 1: Buscar todas las llamadas a `viability_service` en `planning.py`**

```
grep -n "viability_service\|evaluate_and_save" ui/tabs/planning.py
```

- [ ] **Step 2: Actualizar cada llamada para pasar `calculator` y `excel_manager`**

Donde antes era (si quedaron llamadas del estilo viejo):
```python
result = evaluate_and_save(inputs)
```

Cambiar a:
```python
result = evaluate_and_save(
    inputs=inputs,
    calculator=st.session_state.calculator,
    excel_manager=st.session_state.excel_manager,
)
```

- [ ] **Step 3: Verificar imports en `planning.py`**

```
python -c "import sys; sys.path.insert(0,'.'); from ui.tabs.planning import render_planning_tab; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Ejecutar todos los tests**

```
.venv\Scripts\pytest tests/ -v
```

Expected: todos PASS (sin regresiones).

- [ ] **Step 5: Commit**

```bash
git add ui/tabs/planning.py
git commit -m "refactor: pass calculator and excel_manager explicitly to viability_service"
```

---

## Self-Review

### Cobertura de problemas A1 y A2 del reporte arquitectural

| Problema | Task |
|---|---|
| A1: `viability_service.py` importa streamlit | Task 1 |
| A2: `feedback_service.py` importa desde `ui/tabs/` | Task 2 |
| Llamadas en `planning.py` actualizadas | Task 3 |

### Verificación final de independencia del dominio

Después de completar el plan, verificar:
```
grep -r "import streamlit" domain/
grep -r "from ui\." domain/
```
Expected: sin resultados.
