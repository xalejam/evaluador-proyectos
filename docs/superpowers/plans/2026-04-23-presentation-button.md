# Botón Generación de Presentación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un botón "📊 Generar presentación" en el sub-tab Resumen Ejecutivo de Seguimiento Operativo que genere `Resumen_Proyectos_Ejecucion_YYYY-MM-DD.pptx` en memoria y lo sirva para descarga inmediata, con una capa de abstracción (Adapter Protocol) que permita migrar fuente de datos y destino de archivo a Databricks o Azure sin tocar la UI.

**Architecture:** Se extrae `_build_prs()` de `build_presentation()` en el script existente y se agrega `build_presentation_bytes()` que usa `BytesIO`. Un nuevo módulo `infra/presentation_ports.py` define los protocolos `DataSource`/`FileDestination` e implementaciones locales (`SqliteDataSource`, `InMemoryDestination`) importando desde el script vía `sys.path`. La UI añade el botón justo después de `_export_buttons()` en `_render_executive_tab()`.

**Tech Stack:** Python 3, python-pptx, streamlit, sqlite3, io.BytesIO — sin dependencias nuevas.

---

## Estructura de archivos

| Acción | Archivo | Qué cambia |
|--------|---------|------------|
| Modificar | `scripts/generate_execution_status_presentation.py` | Extraer `_build_prs()`, agregar `build_presentation_bytes()` |
| Crear | `infra/presentation_ports.py` | Protocolos + implementaciones locales |
| Modificar | `ui/tabs/seguimiento_operativo.py` | Agregar botón en `_render_executive_tab()` |

---

## Task 1: Extraer `_build_prs()` y agregar `build_presentation_bytes()`

**Files:**
- Modify: `scripts/generate_execution_status_presentation.py:350-363`

El objetivo es que `prs.save()` se pueda llamar tanto con un `Path` (CLI existente) como con un `BytesIO` (UI nueva). `prs.save()` de python-pptx acepta cualquiera de los dos.

- [ ] **Step 1: Reemplazar `build_presentation()` con la versión refactorizada**

Ubicar las líneas 350–363 en `scripts/generate_execution_status_presentation.py` y reemplazarlas con:

```python
def _build_prs(projects: list[ProjectStatus]) -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    chunks = [projects[i:i + ROWS_PER_SLIDE] for i in range(0, len(projects), ROWS_PER_SLIDE)]
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    for n, chunk in enumerate(chunks, start=1):
        build_slide(prs, chunk, n, len(chunks), projects, generated_at)
    return prs


def build_presentation(projects: list[ProjectStatus], output_path: Path) -> Path:
    prs = _build_prs(projects)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path


def build_presentation_bytes(projects: list[ProjectStatus]) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    _build_prs(projects).save(buf)
    return buf.getvalue()
```

- [ ] **Step 2: Verificar que el script CLI sigue funcionando**

```bash
cd "c:/Users/ttMonroyX/OneDrive - Kantar/Documents/Project Managment/ReportesAdhoc/EvaluadorDeProyectos/Repositorio Evaluador"
python scripts/generate_execution_status_presentation.py
```

Resultado esperado: imprime la ruta del `.pptx` generado en `docs/`, sin errores. Si no hay proyectos en ejecución imprime `"No hay proyectos con status 'executing'."` — también es OK.

- [ ] **Step 3: Verificar que `build_presentation_bytes` produce bytes válidos**

```bash
python -c "
import sys
sys.path.insert(0, 'scripts')
from generate_execution_status_presentation import fetch_executing_projects, build_presentation_bytes, DB_PATH
projects = fetch_executing_projects(DB_PATH)
if projects:
    data = build_presentation_bytes(projects)
    print(f'OK: {len(data)} bytes')
    assert data[:4] == b'PK\x03\x04', 'No es un ZIP/PPTX valido'
    print('Firma ZIP correcta')
else:
    print('Sin proyectos en ejecucion — OK igualmente')
"
```

Resultado esperado: `OK: NNNNN bytes` + `Firma ZIP correcta`, o `Sin proyectos en ejecucion — OK igualmente`.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_execution_status_presentation.py
git commit -m "refactor: extract _build_prs() and add build_presentation_bytes() for in-memory generation"
```

---

## Task 2: Crear `infra/presentation_ports.py`

**Files:**
- Create: `infra/presentation_ports.py`

Este módulo define los dos protocolos de extensión y las implementaciones locales. Importa `fetch_executing_projects` y `build_presentation_bytes` del script usando `sys.path`, evitando mover la lógica de slides.

- [ ] **Step 1: Crear `infra/presentation_ports.py`**

```python
"""Adapter ports para generación de presentaciones — extensible a nube."""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from typing import Protocol, runtime_checkable

# Agrega scripts/ al path para poder importar el generador sin moverlo
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from generate_execution_status_presentation import (  # noqa: E402
    DB_PATH,
    ProjectStatus,
    build_presentation_bytes,
    fetch_executing_projects,
)

__all__ = [
    "DataSource",
    "FileDestination",
    "SqliteDataSource",
    "InMemoryDestination",
    "ProjectStatus",
]


@runtime_checkable
class DataSource(Protocol):
    def fetch_projects(self) -> list[ProjectStatus]: ...


@runtime_checkable
class FileDestination(Protocol):
    def save(self, data: bytes) -> bytes | str:
        """Retorna bytes (download_button) o str URL (link_button en nube)."""
        ...


class SqliteDataSource:
    """Fuente de datos local: lee proyectos en ejecución de SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    def fetch_projects(self) -> list[ProjectStatus]:
        return fetch_executing_projects(self._db_path)


class InMemoryDestination:
    """Destino local: devuelve los bytes para que Streamlit sirva la descarga."""

    def save(self, data: bytes) -> bytes:
        return data


# ---------------------------------------------------------------------------
# Stubs futuros — NO implementar hasta tener plataforma definida
# ---------------------------------------------------------------------------
# class AzureBlobDestination:
#     def __init__(self, container: str, blob_name: str) -> None: ...
#     def save(self, data: bytes) -> str: ...   # retorna URL blob
#
# class DatabricksDestination:
#     def __init__(self, dbfs_path: str) -> None: ...
#     def save(self, data: bytes) -> str: ...   # retorna URL DBFS
```

- [ ] **Step 2: Verificar que los protocolos e imports funcionan**

```bash
python -c "
from infra.presentation_ports import SqliteDataSource, InMemoryDestination, DataSource, FileDestination
src = SqliteDataSource()
dst = InMemoryDestination()
assert isinstance(src, DataSource), 'SqliteDataSource no satisface DataSource protocol'
assert isinstance(dst, FileDestination), 'InMemoryDestination no satisface FileDestination protocol'
projects = src.fetch_projects()
print(f'DataSource OK: {len(projects)} proyectos en ejecucion')
if projects:
    from generate_execution_status_presentation import build_presentation_bytes
    import sys; sys.path.insert(0, 'scripts')
    from generate_execution_status_presentation import build_presentation_bytes
    data = dst.save(build_presentation_bytes(projects))
    print(f'FileDestination OK: {len(data)} bytes')
"
```

Resultado esperado: `DataSource OK: N proyectos en ejecucion` + `FileDestination OK: NNNNN bytes` (o solo la primera línea si no hay proyectos).

- [ ] **Step 3: Commit**

```bash
git add infra/presentation_ports.py
git commit -m "feat: add presentation_ports with DataSource/FileDestination protocols and local implementations"
```

---

## Task 3: Agregar botón en `_render_executive_tab()`

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py:1246` (justo después de `_export_buttons()`)

El botón se coloca en una fila separada debajo de los botones de exportar CSV/JSON, alineado a la derecha. El `st.download_button` aparece en el mismo bloque (Streamlit lo renderiza en el mismo rerun).

- [ ] **Step 1: Agregar import en la sección de imports del archivo**

Localizar los imports al inicio de `ui/tabs/seguimiento_operativo.py` y agregar:

```python
from datetime import date as _date
from infra.presentation_ports import (
    SqliteDataSource,
    InMemoryDestination,
    build_presentation_bytes,
)
```

> Nota: `build_presentation_bytes` viene reexportado desde `infra/presentation_ports.py` vía su import del script. Si no está en `__all__`, importarlo directamente desde el script: `from generate_execution_status_presentation import build_presentation_bytes` (con el `sys.path` ya configurado por `presentation_ports`).

Alternativa más robusta que evita depender de `__all__`:

```python
from datetime import date as _date
from infra.presentation_ports import SqliteDataSource, InMemoryDestination
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "scripts"))
from generate_execution_status_presentation import build_presentation_bytes as _build_pptx_bytes
```

Usar **la alternativa robusta** para que el import sea explícito y no dependa de `__all__`.

- [ ] **Step 2: Insertar el bloque del botón después de `_export_buttons()`**

Localizar la línea:
```python
    _export_buttons(summary_view, prefix="resumen_ejecutivo", label_suffix=t("ops_executive_summary"))
```

Agregar inmediatamente después (antes de `st.dataframe(...)`):

```python
    # --- Botón generación de presentación ---
    _, col_pptx = st.columns([5, 1])
    with col_pptx:
        gen_btn = st.button(
            "📊 Generar presentación",
            key="btn_gen_pptx_exec",
            use_container_width=True,
        )

    if gen_btn:
        with st.spinner("Generando Resumen_Proyectos_Ejecucion.pptx..."):
            try:
                source = SqliteDataSource()
                projects = source.fetch_projects()
                if not projects:
                    st.warning("No hay proyectos en ejecución para incluir en la presentación.")
                else:
                    data = InMemoryDestination().save(_build_pptx_bytes(projects))
                    filename = f"Resumen_Proyectos_Ejecucion_{_date.today()}.pptx"
                    st.download_button(
                        label=f"⬇ Descargar {filename}",
                        data=data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key="dl_pptx_exec",
                    )
            except Exception as exc:
                st.error(f"Error al generar la presentación: {exc}")
    # --- fin botón presentación ---
```

- [ ] **Step 3: Verificar que la app arranca sin errores de import**

```bash
python -c "
import streamlit  # solo verifica que el import de la tab no rompe nada
from ui.tabs.seguimiento_operativo import render_seguimiento_operativo
print('Import OK')
"
```

Resultado esperado: `Import OK` sin traceback.

- [ ] **Step 4: Verificar manualmente en la UI**

Arrancar la app:
```bash
streamlit run app.py
```

1. Ir al tab **Seguimiento Operativo** → sub-tab **Resumen Ejecutivo**
2. Verificar que aparece el botón **"📊 Generar presentación"** alineado a la derecha
3. Presionar el botón
4. Si hay proyectos en ejecución: aparece botón de descarga → descargar y abrir el `.pptx`
5. Si no hay proyectos: aparece warning amarillo — OK
6. Los botones de exportar CSV/JSON siguen funcionando igual — verificar

- [ ] **Step 5: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add generate presentation button in Resumen Ejecutivo tab with cloud-ready adapter pattern"
```

---

## Self-Review

**Spec coverage:**
- ✅ Botón en Resumen Ejecutivo → Task 3
- ✅ Generación en memoria (no toca disco) → `build_presentation_bytes` + `BytesIO`
- ✅ `st.download_button` inmediato → Task 3 Step 2
- ✅ Warning si sin proyectos → Task 3 Step 2
- ✅ Adapter `DataSource` + `FileDestination` → Task 2
- ✅ `SqliteDataSource` y `InMemoryDestination` → Task 2
- ✅ Stubs comentados para Azure/Databricks → Task 2
- ✅ Nombre archivo con fecha → `Resumen_Proyectos_Ejecucion_{date.today()}.pptx`
- ✅ `build_presentation()` CLI sin cambio de interfaz → Task 1

**Placeholders:** Ninguno. Todos los pasos tienen código completo.

**Type consistency:** `ProjectStatus` definido en el script, importado en `presentation_ports.py`, retornado por `SqliteDataSource.fetch_projects()`, consumido por `build_presentation_bytes()`. Consistente en los 3 tasks.
