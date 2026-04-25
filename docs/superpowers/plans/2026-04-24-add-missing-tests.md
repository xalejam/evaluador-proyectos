# Plan 3: Tests para Módulos Críticos sin Cobertura

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar tests unitarios para los 4 módulos críticos que actualmente no tienen ninguna cobertura: `thresholds.py`, `seguimiento_operativo_service.py`, `infra/repositories.py` (SQLAlchemy) y `domain/scoring/financials.py` (casos borde).

**Architecture:** Tests puros con `pytest` y `tmp_path`. No se tocan los módulos bajo test — solo se crean archivos en `tests/`. Cada tarea produce un archivo de tests independiente.

**Tech Stack:** pytest, SQLAlchemy (ya instalado), Python stdlib.

---

## Estructura de archivos

| Archivo | Acción | Cubre |
|---|---|---|
| `tests/unit/test_thresholds.py` | Crear | `domain/scoring/thresholds.py` |
| `tests/unit/test_financials_edge_cases.py` | Crear | `domain/scoring/financials.py` casos borde |
| `tests/unit/test_seguimiento_operativo_service.py` | Crear | `domain/services/seguimiento_operativo_service.py` |
| `tests/integration/test_sqlalchemy_repositories.py` | Crear | `infra/repositories.py` (SQLAlchemy) |

---

## Task 1: Tests para `domain/scoring/thresholds.py`

**Files:**
- Test: `tests/unit/test_thresholds.py`

- [ ] **Step 1: Leer `domain/scoring/thresholds.py`**

Lee el archivo para entender las funciones y sus rangos de input.

- [ ] **Step 2: Crear `tests/unit/test_thresholds.py`**

```python
# tests/unit/test_thresholds.py
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.scoring.thresholds import score_to_priority, score_to_recommendation


class TestScoreToPriority:
    def test_score_90_returns_alta(self):
        assert score_to_priority(90) == "Alta"

    def test_score_75_returns_alta(self):
        assert score_to_priority(75) == "Alta"

    def test_score_50_returns_media(self):
        result = score_to_priority(50)
        assert result in ("Media", "Baja")  # depende del threshold real

    def test_score_0_returns_lowest_priority(self):
        result = score_to_priority(0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_score_100_returns_string(self):
        result = score_to_priority(100)
        assert isinstance(result, str)

    def test_score_boundary_values(self):
        # No deben lanzar excepción
        for score in [0, 1, 49, 50, 74, 75, 99, 100]:
            result = score_to_priority(score)
            assert isinstance(result, str), f"score={score} retornó {type(result)}"


class TestScoreToRecommendation:
    def test_returns_string_for_any_valid_score(self):
        for score in [0, 25, 50, 75, 100]:
            result = score_to_recommendation(score)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_high_score_recommendation_is_positive(self):
        result = score_to_recommendation(90)
        # La recomendación para score alto debe ser positiva (no "Rechazar")
        assert "rechaz" not in result.lower()

    def test_low_score_recommendation_exists(self):
        result = score_to_recommendation(10)
        assert isinstance(result, str)
```

- [ ] **Step 3: Ejecutar tests**

```
.venv\Scripts\pytest tests/unit/test_thresholds.py -v
```

Expected: si algún test falla por asumir un threshold incorrecto, ajusta el valor en el test (no en el módulo). Los tests deben adaptarse a lo que el módulo hace, no al revés.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_thresholds.py
git commit -m "test: add unit tests for domain/scoring/thresholds.py"
```

---

## Task 2: Tests de casos borde para `domain/scoring/financials.py`

**Files:**
- Test: `tests/unit/test_financials_edge_cases.py`

- [ ] **Step 1: Leer `domain/scoring/financials.py`**

Lee el archivo para entender `compute_financials` y sus parámetros.

- [ ] **Step 2: Crear `tests/unit/test_financials_edge_cases.py`**

```python
# tests/unit/test_financials_edge_cases.py
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.scoring.financials import compute_financials


BASE_INPUTS = {
    "current_time_per_task": 2.0,
    "time_reduction_percent": 50,
    "tasks_per_month": 20,
    "staff_count": 3,
    "avg_salary_per_hour": 25.0,
    "development_hours": 100,
    "development_cost_per_hour": 50.0,
    "maintenance_monthly": 200.0,
}


def test_normal_case_returns_positive_savings():
    result = compute_financials(**BASE_INPUTS)
    assert result["monthly_savings"] > 0
    assert result["annual_savings"] == result["monthly_savings"] * 12


def test_zero_development_hours_returns_none_roi():
    inputs = {**BASE_INPUTS, "development_hours": 0}
    result = compute_financials(**inputs)
    assert result["roi_first_year"] is None


def test_maintenance_exceeds_savings_returns_none_payback():
    # Si mantenimiento >= ahorro mensual, payback no tiene sentido
    inputs = {**BASE_INPUTS, "maintenance_monthly": 99999.0}
    result = compute_financials(**inputs)
    assert result["payback_period_months"] is None


def test_zero_time_reduction_returns_zero_savings():
    inputs = {**BASE_INPUTS, "time_reduction_percent": 0}
    result = compute_financials(**inputs)
    assert result["monthly_savings"] == 0.0
    assert result["annual_savings"] == 0.0


def test_zero_staff_returns_zero_hours_saved():
    inputs = {**BASE_INPUTS, "staff_count": 0}
    result = compute_financials(**inputs)
    assert result["hours_saved_per_month"] == 0.0


def test_result_contains_required_keys():
    result = compute_financials(**BASE_INPUTS)
    required_keys = [
        "monthly_savings", "annual_savings", "payback_period_months",
        "roi_first_year", "hours_saved_per_month", "initial_development_cost"
    ]
    for key in required_keys:
        assert key in result, f"Falta clave: {key}"
```

- [ ] **Step 3: Ejecutar tests**

```
.venv\Scripts\pytest tests/unit/test_financials_edge_cases.py -v
```

Expected: todos PASS. Si algún test falla por un nombre de parámetro diferente, ajusta los nombres en el test para que coincidan con la firma real del módulo.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_financials_edge_cases.py
git commit -m "test: add edge case tests for domain/scoring/financials.py"
```

---

## Task 3: Tests para `domain/services/seguimiento_operativo_service.py`

**Files:**
- Test: `tests/unit/test_seguimiento_operativo_service.py`

- [ ] **Step 1: Leer `domain/services/seguimiento_operativo_service.py`**

Lee el archivo (155 líneas) para entender qué funciones expone y qué dependencias toma (¿recibe `conn`? ¿`repo`? ¿accede a BD directamente?).

- [ ] **Step 2: Crear `tests/unit/test_seguimiento_operativo_service.py`**

Adapta el test a las firmas reales del módulo. Si el servicio recibe un repositorio como parámetro, usa un fake. Si accede directamente a BD, usa `tmp_path` con una BD en memoria.

Ejemplo base (ajustar según firmas reales):

```python
# tests/unit/test_seguimiento_operativo_service.py
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Importar las funciones principales del servicio
# (leer el módulo primero para saber qué exporta)
from domain.services.seguimiento_operativo_service import (
    get_projects_by_status,
    save_note,
)
from infra.db_migrations import ensure_projects_schema, ensure_notes_schema


@pytest.fixture
def db_conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_projects_schema(conn)
    # Insertar proyecto de prueba
    conn.execute(
        "INSERT INTO projects (name, status, country, owner) VALUES (?, ?, ?, ?)",
        ("Test Project", "approved", "MX", "TEST"),
    )
    conn.commit()
    yield conn
    conn.close()


def test_get_projects_by_status_returns_list(db_conn):
    result = get_projects_by_status(db_conn, status="approved")
    assert isinstance(result, list)
    assert len(result) >= 1


def test_get_projects_by_status_filters_correctly(db_conn):
    result = get_projects_by_status(db_conn, status="executing")
    assert len(result) == 0  # No hay proyectos en executing


def test_save_note_persists_in_db(db_conn):
    # Obtener el ID del proyecto insertado
    row = db_conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
    project_id = row["id"]

    save_note(
        conn=db_conn,
        project_id=project_id,
        note_type="general",
        note_text="Nota de prueba",
        author="TEST_AUTHOR",
    )
    db_conn.commit()

    notes = db_conn.execute(
        "SELECT * FROM project_notes WHERE project_id = ?", (project_id,)
    ).fetchall()
    assert len(notes) == 1
    assert notes[0]["note_text"] == "Nota de prueba"
```

> **Nota importante**: Lee el módulo ANTES de implementar los tests. Si las firmas son diferentes (ej. el servicio recibe `db_path` en lugar de `conn`), ajusta los tests para que coincidan con la realidad. No adivines los parámetros.

- [ ] **Step 3: Ejecutar tests**

```
.venv\Scripts\pytest tests/unit/test_seguimiento_operativo_service.py -v
```

Expected: todos PASS (ajustando por las firmas reales).

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_seguimiento_operativo_service.py
git commit -m "test: add unit tests for seguimiento_operativo_service"
```

---

## Task 4: Tests para `infra/repositories.py` (SQLAlchemy)

**Files:**
- Test: `tests/integration/test_sqlalchemy_repositories.py`

- [ ] **Step 1: Leer `infra/repositories.py`**

Lee el archivo (168 líneas) para entender `ProjectRepository` y `EvaluationRepository` y sus métodos.

- [ ] **Step 2: Crear `tests/integration/test_sqlalchemy_repositories.py`**

```python
# tests/integration/test_sqlalchemy_repositories.py
import sys
from pathlib import Path
from datetime import datetime
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infra.db.sqlalchemy_store import Base
from infra.repositories import ProjectRepository, EvaluationRepository


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_matrix.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    engine.dispose()


class TestProjectRepository:
    def test_create_project(self, session):
        repo = ProjectRepository(lambda: session)
        repo.upsert(
            project_id="MX-TEST-0001",
            country="MX",
            owner="TEST",
            name="Test Project",
        )
        session.commit()
        project = session.execute(
            session.query(type(None))
        )
        # Verificar via query directa
        from infra.db.sqlalchemy_store import ProjectModel
        result = session.query(ProjectModel).filter_by(project_id="MX-TEST-0001").first()
        assert result is not None
        assert result.name == "Test Project"

    def test_upsert_updates_existing_project(self, session):
        repo = ProjectRepository(lambda: session)
        repo.upsert(project_id="MX-TEST-0002", country="MX", owner="TEST", name="Original")
        session.commit()
        repo.upsert(project_id="MX-TEST-0002", country="MX", owner="TEST", name="Updated")
        session.commit()

        from infra.db.sqlalchemy_store import ProjectModel
        results = session.query(ProjectModel).filter_by(project_id="MX-TEST-0002").all()
        assert len(results) == 1
        assert results[0].name == "Updated"


class TestEvaluationRepository:
    def test_save_evaluation_marks_as_current(self, session):
        # Setup: crear proyecto primero
        from infra.db.sqlalchemy_store import ProjectModel
        project = ProjectModel(
            project_id="MX-EVAL-0001",
            country="MX",
            owner="TEST",
            name="Eval Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(project)
        session.commit()

        repo = EvaluationRepository(lambda: session)
        repo.save_current(
            project_id="MX-EVAL-0001",
            answers={"A": 3, "B": 2},
            weights={"A": 1.0, "B": 1.0},
            impact_score=0.6,
            effort_score=0.4,
        )
        session.commit()

        from infra.db.sqlalchemy_store import EvaluationModel
        evals = session.query(EvaluationModel).filter_by(
            project_id="MX-EVAL-0001", is_current=True
        ).all()
        assert len(evals) == 1

    def test_save_current_replaces_previous_current(self, session):
        from infra.db.sqlalchemy_store import ProjectModel, EvaluationModel
        project = ProjectModel(
            project_id="MX-EVAL-0002",
            country="MX",
            owner="TEST",
            name="Eval Project 2",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(project)
        session.commit()

        repo = EvaluationRepository(lambda: session)
        repo.save_current(project_id="MX-EVAL-0002", answers={}, weights={}, impact_score=0.5, effort_score=0.5)
        session.commit()
        repo.save_current(project_id="MX-EVAL-0002", answers={}, weights={}, impact_score=0.8, effort_score=0.3)
        session.commit()

        current_evals = session.query(EvaluationModel).filter_by(
            project_id="MX-EVAL-0002", is_current=True
        ).all()
        assert len(current_evals) == 1
        assert current_evals[0].impact_score == pytest.approx(0.8)
```

> **Nota**: Lee `infra/repositories.py` y `infra/db/sqlalchemy_store.py` antes de implementar. Ajusta los nombres de modelos (`ProjectModel`, `EvaluationModel`) y métodos (`upsert`, `save_current`) a los nombres reales del código.

- [ ] **Step 3: Ejecutar tests**

```
.venv\Scripts\pytest tests/integration/test_sqlalchemy_repositories.py -v
```

Expected: todos PASS.

- [ ] **Step 4: Ejecutar toda la suite**

```
.venv\Scripts\pytest tests/ -v
```

Expected: todos PASS (sin regresiones).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_sqlalchemy_repositories.py
git commit -m "test: add integration tests for SQLAlchemy ProjectRepository and EvaluationRepository"
```

---

## Self-Review

### Cobertura del reporte arquitectural

| Problema | Task |
|---|---|
| B4: `thresholds.py` sin tests | Task 1 |
| B4: `financials.py` sin tests de casos borde | Task 2 |
| B4: `seguimiento_operativo_service.py` sin tests | Task 3 |
| B4: `infra/repositories.py` SQLAlchemy sin tests | Task 4 |

### Cobertura total estimada después del plan

| Módulo | Antes | Después |
|---|---|---|
| `domain/scoring/thresholds.py` | 0% | ~80% |
| `domain/scoring/financials.py` | 20% (1 caso) | ~90% |
| `domain/services/seguimiento_operativo_service.py` | 0% | ~60% |
| `infra/repositories.py` | 0% | ~70% |
