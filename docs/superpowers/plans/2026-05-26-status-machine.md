# Status Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la lógica de transiciones de status dispersa y el marcador mágico `/end` por una máquina de estados centralizada con botones explícitos de cierre y reapertura de proyectos.

**Architecture:** Se crea `infra/status_machine.py` como única fuente de verdad para las transiciones permitidas. El UI (`ui/tabs/seguimiento_operativo.py`) importa `can_transition` para controlar qué botones renderizar. Se eliminan el string mágico `/end` y la constante `END_MARKER`. Se añaden dos botones con confirmación: "Cerrar proyecto" (executing → implemented) y "Reabrir proyecto" (implemented → executing).

**Tech Stack:** Python 3.11, Streamlit, pytest, psycopg2 / sqlite3 (dual-path via adapter)

---

## File Map

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Crear  | `infra/status_machine.py` | `ALLOWED_TRANSITIONS`, `can_transition()`, `allowed_targets()` |
| Crear  | `tests/unit/test_status_machine.py` | Tests unitarios del grafo de transiciones |
| Modificar | `ui/tabs/seguimiento_operativo.py` | Remover `END_MARKER`, agregar botones Close/Reopen, importar `can_transition` |

---

## Task 1: Crear `infra/status_machine.py`

**Files:**
- Create: `infra/status_machine.py`
- Create: `tests/unit/test_status_machine.py`

- [ ] **Step 1.1: Escribir los tests primero**

```python
# tests/unit/test_status_machine.py
import pytest
from infra.status_machine import ALLOWED_TRANSITIONS, allowed_targets, can_transition


def test_approved_to_executing_allowed():
    assert can_transition("approved", "executing") is True


def test_in_agenda_to_executing_allowed():
    assert can_transition("in_agenda", "executing") is True


def test_executing_to_implemented_allowed():
    assert can_transition("executing", "implemented") is True


def test_implemented_to_executing_allowed_reopen():
    """Implemented projects must be re-openable."""
    assert can_transition("implemented", "executing") is True


def test_executing_to_approved_not_allowed():
    assert can_transition("executing", "approved") is False


def test_implemented_to_approved_not_allowed():
    assert can_transition("implemented", "approved") is False


def test_handed_off_has_no_targets():
    assert can_transition("handed_off", "executing") is False
    assert allowed_targets("handed_off") == []


def test_unknown_status_returns_false():
    assert can_transition("nonexistent", "executing") is False


def test_case_insensitive_current():
    assert can_transition("APPROVED", "executing") is True
    assert can_transition("Executing", "implemented") is True


def test_allowed_targets_executing_contains_expected():
    targets = allowed_targets("executing")
    assert "implemented" in targets
    assert "on_hold" in targets
    assert "approved" not in targets


def test_all_transition_targets_are_known_statuses():
    """Every transition target must itself be a key in ALLOWED_TRANSITIONS."""
    known = set(ALLOWED_TRANSITIONS.keys())
    for src, targets in ALLOWED_TRANSITIONS.items():
        for tgt in targets:
            assert tgt in known, (
                f"Transition {src!r} → {tgt!r}: "
                f"target {tgt!r} is not a key in ALLOWED_TRANSITIONS"
            )
```

- [ ] **Step 1.2: Ejecutar tests — deben fallar**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: `ModuleNotFoundError: No module named 'infra.status_machine'`

- [ ] **Step 1.3: Implementar `infra/status_machine.py`**

```python
"""Status machine for project lifecycle.

Single source of truth for which status transitions are allowed.
"""
from __future__ import annotations

# Maps each status to the list of statuses it can legally transition to.
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "evaluated":   ["approved", "rejected", "on_hold"],
    "approved":    ["executing", "on_hold", "rejected"],
    "in_agenda":   ["executing", "on_hold", "rejected"],
    "executing":   ["implemented", "on_hold"],
    "on_hold":     ["executing", "rejected"],
    "implemented": ["executing"],   # reopen after delivery
    "rejected":    ["approved"],    # rescue / reconsider
    "backlog":     ["approved", "rejected"],
    "handed_off":  [],              # terminal — no transitions out
}


def can_transition(current: str, target: str) -> bool:
    """Return True if transitioning from current to target is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current.lower(), [])


def allowed_targets(current: str) -> list[str]:
    """Return list of valid target statuses from the given current status."""
    return list(ALLOWED_TRANSITIONS.get(current.lower(), []))
```

- [ ] **Step 1.4: Ejecutar tests — deben pasar**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: 11 passed

- [ ] **Step 1.5: Lint**

```
python -m ruff check infra/status_machine.py tests/unit/test_status_machine.py
python -m ruff format infra/status_machine.py tests/unit/test_status_machine.py
```

Resultado esperado: `All checks passed!`

- [ ] **Step 1.6: Commit**

```
git add infra/status_machine.py tests/unit/test_status_machine.py
git commit -m "feat(status): add StatusMachine — centralized transition graph"
```

---

## Task 2: Eliminar `/end`, agregar botón "Cerrar proyecto"

**Contexto:** El string mágico `/end` en el campo General cierra el proyecto silenciosamente. Se reemplaza por un botón explícito con confirmación, visible solo cuando el status es `executing`.

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

- [ ] **Step 2.1: Escribir tests para la función de renderizado del botón**

Los tests de Streamlit UI no se pueden ejecutar sin el servidor. En cambio, testeamos la lógica de validación de transición que el botón usa:

```python
# Agregar a tests/unit/test_status_machine.py

def test_executing_can_close():
    """Prerequisite for rendering the close button."""
    assert can_transition("executing", "implemented") is True


def test_approved_cannot_close_directly():
    """Close button must NOT appear for projects not yet executing."""
    assert can_transition("approved", "implemented") is False


def test_implemented_cannot_close_again():
    """Close button must NOT appear for already-implemented projects."""
    assert can_transition("implemented", "implemented") is False
```

- [ ] **Step 2.2: Ejecutar tests — deben pasar sin cambios de código**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: 14 passed

- [ ] **Step 2.3: Editar `ui/tabs/seguimiento_operativo.py` — remover END_MARKER**

Localizar y eliminar la línea (aprox. línea 50):

```python
# ANTES — eliminar esta línea:
END_MARKER = "/end"
```

La constante `POST_CLOSURE_TYPE = "soporte_post_entrega"` en la línea siguiente **no se toca**.

- [ ] **Step 2.4: Agregar import de `can_transition` en seguimiento_operativo.py**

En el bloque de imports al inicio del archivo (junto a los otros imports de `infra`), agregar:

```python
# Encontrar esta línea existente:
from infra.db.adapter import PLACEHOLDER, db_read_dataframe

# Agregar debajo:
from infra.status_machine import can_transition
```

- [ ] **Step 2.5: Remover la lógica `/end` del bloque `if submitted:`**

Localizar (aprox. línea 1503) y reemplazar:

```python
# ANTES:
status_after: str | None = None
general_text = str(general or "").lower()
if END_MARKER in general_text:
    status_after = "implemented"
elif str(selected_project.status or "").lower() in START_EXECUTION_STATUSES:
    status_after = "executing"
if status_after:
    update_project_status(conn, selected_project.project_id, status_after)
```

```python
# DESPUÉS:
status_after: str | None = None
if str(selected_project.status or "").lower() in START_EXECUTION_STATUSES:
    status_after = "executing"
if status_after:
    update_project_status(conn, selected_project.project_id, status_after)
```

- [ ] **Step 2.6: Agregar botón "Cerrar proyecto" después del bloque `if submitted:`**

Localizar la línea `st.markdown("---")` que aparece justo después del bloque `if submitted:` y agregar antes de ella:

```python
# Botón explícito para cerrar proyecto (executing → implemented)
if can_transition(str(selected_project.status or ""), "implemented"):
    st.markdown("---")
    st.markdown("**Cierre de proyecto**")
    confirm_close_key = f"ops_confirm_close_{selected_project.project_id}"
    if st.button(
        "🔒 Cerrar proyecto",
        key=f"ops_close_{selected_project.project_id}",
        help="Marca el proyecto como Implementado. Acción reversible.",
    ):
        st.session_state[confirm_close_key] = True

    if st.session_state.get(confirm_close_key):
        st.warning(
            "⚠️ ¿Confirmas el cierre del proyecto? "
            "El status cambiará a **Implementado**. Puedes reabrirlo después si es necesario."
        )
        c1, c2 = st.columns(2)
        if c1.button(
            "Sí, cerrar",
            key=f"ops_close_yes_{selected_project.project_id}",
            type="primary",
        ):
            try:
                update_project_status(conn, selected_project.project_id, "implemented")
                st.session_state.pop(confirm_close_key, None)
                st.success("✅ Proyecto cerrado correctamente.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al cerrar proyecto: {exc}")
        if c2.button("Cancelar", key=f"ops_close_no_{selected_project.project_id}"):
            st.session_state.pop(confirm_close_key, None)
            st.rerun()
```

- [ ] **Step 2.7: Lint y formato**

```
python -m ruff check ui/tabs/seguimiento_operativo.py
python -m ruff format ui/tabs/seguimiento_operativo.py
```

Resultado esperado: `All checks passed!`

- [ ] **Step 2.8: Ejecutar suite completa**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: 14 passed

- [ ] **Step 2.9: Commit**

```
git add ui/tabs/seguimiento_operativo.py tests/unit/test_status_machine.py
git commit -m "feat(ops): replace /end magic string with explicit close button"
```

---

## Task 3: Agregar botón "Reabrir proyecto"

**Contexto:** Proyectos `implemented` que reciben trabajo nuevo deben poder volver a `executing` de forma controlada, sin tocar la sección de post-cierre.

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

- [ ] **Step 3.1: Escribir tests para la lógica de reapertura**

```python
# Agregar a tests/unit/test_status_machine.py

def test_implemented_can_reopen():
    """Prerequisite for rendering the reopen button."""
    assert can_transition("implemented", "executing") is True


def test_executing_cannot_reopen():
    """Reopen button must NOT appear for already-executing projects."""
    assert can_transition("executing", "executing") is False


def test_on_hold_can_resume():
    """on_hold → executing is a valid transition."""
    assert can_transition("on_hold", "executing") is True
```

- [ ] **Step 3.2: Ejecutar tests — deben pasar sin cambios de código**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: 17 passed

- [ ] **Step 3.3: Agregar botón "Reabrir proyecto" en `_render_capture_tab`**

Localizar el bloque de columnas de información del proyecto (aprox. línea 1264):

```python
info1, info2, info3 = st.columns([1, 1, 2])
```

Justo **después** de ese bloque de columnas (después de que se renderizan `info1`, `info2`, `info3`), agregar:

```python
# Botón de reapertura — visible solo para proyectos implementados
if can_transition(str(selected_project.status or ""), "executing") and \
        str(selected_project.status or "").lower() == "implemented":
    confirm_reopen_key = f"ops_confirm_reopen_{selected_project.project_id}"
    st.info(
        "Este proyecto está **Implementado**. "
        "Si hay trabajo nuevo, puedes reabrirlo para seguir registrando avance."
    )
    if st.button(
        "🔓 Reabrir proyecto",
        key=f"ops_reopen_{selected_project.project_id}",
        help="Vuelve el proyecto a En Ejecución.",
    ):
        st.session_state[confirm_reopen_key] = True

    if st.session_state.get(confirm_reopen_key):
        st.warning(
            "⚠️ ¿Confirmas reapertura? "
            "El status volverá a **En ejecución** y podrás registrar nuevas notas normalmente."
        )
        c1, c2 = st.columns(2)
        if c1.button(
            "Sí, reabrir",
            key=f"ops_reopen_yes_{selected_project.project_id}",
            type="primary",
        ):
            try:
                update_project_status(conn, selected_project.project_id, "executing")
                st.session_state.pop(confirm_reopen_key, None)
                st.success("✅ Proyecto reabierto. Ya puedes registrar nuevas notas.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al reabrir proyecto: {exc}")
        if c2.button("Cancelar", key=f"ops_reopen_no_{selected_project.project_id}"):
            st.session_state.pop(confirm_reopen_key, None)
            st.rerun()
```

- [ ] **Step 3.4: Lint y formato**

```
python -m ruff check ui/tabs/seguimiento_operativo.py
python -m ruff format ui/tabs/seguimiento_operativo.py
```

Resultado esperado: `All checks passed!`

- [ ] **Step 3.5: Ejecutar suite completa**

```
pytest tests/unit/test_status_machine.py -v
```

Resultado esperado: 17 passed

- [ ] **Step 3.6: Commit**

```
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat(ops): add Reabrir proyecto button for implemented → executing"
```

---

## Task 4: Push y verificación final

- [ ] **Step 4.1: Suite completa de tests**

```
pytest tests/ -v --tb=short
```

Resultado esperado: todos los tests previos + los 17 nuevos pasan.

- [ ] **Step 4.2: Push a ambos remotes**

```
git push origin main
git push github main
```

- [ ] **Step 4.3: Verificar en Streamlit Community Cloud**

En el app desplegado:
1. Seleccionar un proyecto en status `executing` → debe verse el botón 🔒 "Cerrar proyecto"
2. Cerrar el proyecto → status cambia a "Implementado"
3. Seleccionar ese mismo proyecto → debe verse el botón 🔓 "Reabrir proyecto"
4. Reabrir → status vuelve a "En ejecución"
5. Escribir una nota sin `/end` y guardar → NO debe cerrar el proyecto

---

## Self-Review

**Spec coverage:**
- ✅ `ALLOWED_TRANSITIONS` centralizado — Task 1
- ✅ Eliminar `/end` magic string — Task 2, Steps 2.3–2.5
- ✅ Botón "Cerrar proyecto" con confirmación — Task 2, Step 2.6
- ✅ Botón "Reabrir proyecto" con confirmación — Task 3
- ✅ `can_transition()` como guard para renderizar botones — Tasks 2 y 3
- ✅ Auto-advance approved → executing se mantiene — no se toca esa lógica

**Placeholder scan:** ninguno encontrado — todo el código está completo.

**Type consistency:** `can_transition(str, str) -> bool` y `update_project_status(conn, str, str) -> None` usados de forma consistente en Tasks 2 y 3.
