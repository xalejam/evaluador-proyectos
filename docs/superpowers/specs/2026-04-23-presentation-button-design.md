# Botón de Generación de Presentación en Resumen Ejecutivo

## Propósito

Agregar un botón **"Generar presentación"** en el sub-tab Resumen Ejecutivo de Seguimiento Operativo que genere `Resumen_Proyectos_Ejecucion.pptx` en memoria y lo sirva para descarga inmediata, con una capa de abstracción que permita migrar fuente de datos y destino de archivo a Databricks o Azure sin cambiar la lógica de UI.

---

## Arquitectura

### Patrón: Adapter con Protocols

Dos protocolos simples definen los puntos de extensión:

- **`DataSource`** — cómo se obtienen los proyectos en ejecución
- **`FileDestination`** — qué se hace con los bytes del `.pptx` generado

Hoy ambos tienen implementaciones locales (SQLite + memoria). En la nube se agregan nuevas clases que implementan los mismos protocolos sin tocar UI ni lógica de generación.

```
UI (seguimiento_operativo.py)
  └─ llama → PresentationService(data_source, destination)
               ├─ data_source.fetch_projects()   → list[ProjectStatus]
               ├─ build_presentation(projects)   → bytes  (reutiliza script existente)
               └─ destination.save(bytes)        → bytes | str
                    bytes → st.download_button
                    str   → st.link_button  (futuro nube)
```

---

## Archivos

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Crear | `infra/presentation_ports.py` | Protocolos + implementaciones locales |
| Modificar | `ui/tabs/seguimiento_operativo.py` | Agregar botón en `_render_executive_tab()` |
| Modificar | `scripts/generate_execution_status_presentation.py` | Extraer `build_presentation_bytes(projects) -> bytes` que usa `BytesIO` en lugar de `Path` |
| Eliminar tras merge | `docs/superpowers/mockup_presentation_button.html` | Solo era mockup de diseño |

---

## Detalle: `infra/presentation_ports.py`

```python
from typing import Protocol, runtime_checkable
from pathlib import Path
from io import BytesIO

@runtime_checkable
class DataSource(Protocol):
    def fetch_projects(self) -> list: ...  # list[ProjectStatus]

@runtime_checkable
class FileDestination(Protocol):
    def save(self, data: bytes) -> bytes | str: ...
    # bytes  → UI usa st.download_button
    # str    → UI usa st.link_button (URL en nube)

class SqliteDataSource:
    def __init__(self, db_path: Path): ...
    def fetch_projects(self) -> list: ...  # delega a fetch_executing_projects(db_path)

class InMemoryDestination:
    def save(self, data: bytes) -> bytes:
        return data
```

### Nueva función en `scripts/generate_execution_status_presentation.py`

`build_presentation()` existente guarda en disco (recibe `Path`). Se agrega una función hermana que devuelve bytes:

```python
def build_presentation_bytes(projects: list[ProjectStatus]) -> bytes:
    buf = BytesIO()
    prs = _build_prs(projects)   # lógica extraída de build_presentation()
    prs.save(buf)
    return buf.getvalue()
```

`build_presentation()` existente se refactoriza para llamar `_build_prs()` internamente — sin cambio de interfaz pública.

**Stubs futuros (no implementar ahora):**
```python
# class AzureBlobDestination:
#     def save(self, data: bytes) -> str: ...  # retorna URL blob

# class DatabricksDestination:
#     def save(self, data: bytes) -> str: ...  # retorna URL DBFS
```

---

## Detalle: cambio en `_render_executive_tab()`

El botón se ubica en la misma fila que los botones de exportar CSV/JSON, alineado a la derecha. Se agrega después de `_export_buttons()` y antes del separador `---` del gráfico.

```
[ ⬇ Exportar CSV ]  [ ⬇ Exportar JSON ]          [ 📊 Generar presentación ]
```

**Flujo completo al presionar:**
1. `st.spinner("Generando Resumen_Proyectos_Ejecucion.pptx...")`
2. `SqliteDataSource(DB_PATH).fetch_projects()`
3. Si lista vacía → `st.warning("No hay proyectos en ejecución para incluir en la presentación")` → stop
4. `build_presentation_bytes(projects)` → `bytes`
5. `InMemoryDestination().save(bytes)` → `bytes`
6. `st.download_button(label="⬇ Descargar ...", data=bytes, file_name=f"Resumen_Proyectos_Ejecucion_{fecha}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")`
7. Si excepción → `st.error(str(exc))`

**Nombre del archivo descargado:** `Resumen_Proyectos_Ejecucion_YYYY-MM-DD.pptx` usando `datetime.today()`.

---

## Extensibilidad futura

Para migrar a Azure o Databricks:

1. Agregar nueva clase en `infra/presentation_ports.py` que implemente `FileDestination` (y/o `DataSource`)
2. En `_render_executive_tab()`, cambiar una línea:
   ```python
   # Hoy
   destination = InMemoryDestination()
   # Futuro
   destination = AzureBlobDestination(container="reports")
   ```
3. La UI detecta el tipo de retorno: `bytes` → `download_button`, `str` → `link_button`

No se requiere cambiar lógica de generación ni resto de la UI.

---

## Casos borde

| Caso | Comportamiento |
|------|---------------|
| Sin proyectos en ejecución | `st.warning` — no genera archivo |
| Error en generación de pptx | `st.error(str(exc))` |
| Logo `logo_DDNola.png` ausente | El script ya maneja esto con fallback (no dibuja logo) |
| Archivo muy grande (>50 proyectos) | Streamlit sirve hasta ~200MB en `download_button` — sin problema en escala actual |

---

## Lo que NO cambia

- Schema de DB
- Lógica de notas, captura, timeline
- Estilo visual de la presentación (colores, layout de slides)
- Botones de exportar CSV/JSON existentes

---

## Historial

| Fecha | Cambio |
|-------|--------|
| 2026-04-23 | Spec inicial — botón generación presentación con adapter pattern |
