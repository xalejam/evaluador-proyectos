# SharePoint Folder Provisioning on Approval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al hacer clic en "Aprobar (pasar a agenda)", crear automáticamente una carpeta de proyecto con subcarpetas en la ruta local de SharePoint, con color de carpeta según las palabras clave en nombre/descripción del proyecto.

**Architecture:** Se crea un módulo `infra/folder_provisioner.py` con interfaz abstracta (`FolderProvisioner`) y una implementación local (`LocalFolderProvisioner`). La UI en `planning.py` llama al provisioner después del `save_project` exitoso. Cuando se migre a la nube, solo se agrega `SharePointFolderProvisioner` implementando la misma interfaz, sin tocar la UI.

**Tech Stack:** Python stdlib (`pathlib`, `ctypes`/`os`), pytest, Streamlit (solo para el hook en planning.py).

---

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `infra/folder_provisioner.py` | Crear | Interfaz abstracta + implementación local + lógica de color |
| `tests/infra/test_folder_provisioner.py` | Crear | Tests unitarios del provisioner |
| `ui/tabs/planning.py` | Modificar línea ~634 | Llamar al provisioner tras approve exitoso |
| `ui/tabs/shared.py` | Modificar | Agregar claves i18n para mensajes del provisioner |
| `config/folder_provisioner_config.json` | Crear | Ruta base y keywords, separado del código |

---

## Task 1: Configuración externalizada

**Files:**
- Create: `config/folder_provisioner_config.json`

- [ ] **Step 1: Crear el archivo de configuración**

```json
{
  "local_base_path": "C:/Users/ttMonroyX/Kantar/DDP Developers - Proyectos",
  "subfolders": [
    "0_documentación",
    "1_Inputs",
    "2_Outputs",
    "3_Repositorio",
    "4_Evidencias"
  ],
  "color_rules": {
    "blue": ["agente", "agent", "ia", "ai", "inteligencia artificial", "ml", "machine learning", "bot", "llm", "gpt", "copilot", "openai", "anthropic"],
    "green": ["vba", "macro", "excel vba", "visual basic"]
  },
  "color_default": "yellow"
}
```

- [ ] **Step 2: Commit**

```bash
git add config/folder_provisioner_config.json
git commit -m "config: add folder provisioner config with color rules and subfolders"
```

---

## Task 2: Módulo `infra/folder_provisioner.py`

**Files:**
- Create: `infra/folder_provisioner.py`
- Test: `tests/infra/test_folder_provisioner.py`

### 2a — Escribir tests primero

- [ ] **Step 1: Crear el archivo de tests**

```python
# tests/infra/test_folder_provisioner.py
import json
import os
import sys
from pathlib import Path
import pytest

# Asegurar que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.folder_provisioner import (
    FolderColor,
    detect_color,
    LocalFolderProvisioner,
    FolderProvisionResult,
)

CONFIG = {
    "local_base_path": "",  # se sobreescribe en tests
    "subfolders": ["0_documentación", "1_Inputs", "2_Outputs", "3_Repositorio", "4_Evidencias"],
    "color_rules": {
        "blue": ["agente", "agent", "ia", "ai", "bot", "llm"],
        "green": ["vba", "macro"],
    },
    "color_default": "yellow",
}


class TestDetectColor:
    def test_agent_keyword_in_name_returns_blue(self):
        assert detect_color("Agente Titulador", "", CONFIG) == FolderColor.BLUE

    def test_ia_keyword_in_description_returns_blue(self):
        assert detect_color("Reporte mensual", "automatizar con IA generativa", CONFIG) == FolderColor.BLUE

    def test_vba_keyword_in_name_returns_green(self):
        assert detect_color("Macro VBA de cierre", "", CONFIG) == FolderColor.GREEN

    def test_vba_keyword_in_description_returns_green(self):
        assert detect_color("Herramienta", "desarrollado en vba para excel", CONFIG) == FolderColor.GREEN

    def test_no_keyword_returns_yellow(self):
        assert detect_color("Dashboard de ventas", "reporte de seguimiento mensual", CONFIG) == FolderColor.YELLOW

    def test_case_insensitive(self):
        assert detect_color("AGENTE clasificador", "", CONFIG) == FolderColor.BLUE

    def test_blue_takes_priority_over_green(self):
        # si por alguna razón contiene ambos, azul gana
        assert detect_color("Agente VBA", "", CONFIG) == FolderColor.BLUE


class TestLocalFolderProvisioner:
    def test_creates_project_folder_and_subfolders(self, tmp_path):
        cfg = {**CONFIG, "local_base_path": str(tmp_path)}
        provisioner = LocalFolderProvisioner(cfg)
        result = provisioner.provision("LA-DDD-0001", "Agente Titulador", "automatiza con ia")

        assert result.success is True
        project_folder = tmp_path / "LA-DDD-0001 Agente Titulador"
        assert project_folder.exists()
        for sub in CONFIG["subfolders"]:
            assert (project_folder / sub).exists()

    def test_returns_folder_path_in_result(self, tmp_path):
        cfg = {**CONFIG, "local_base_path": str(tmp_path)}
        provisioner = LocalFolderProvisioner(cfg)
        result = provisioner.provision("LA-DDD-0002", "Reporte VBA", "macro excel")

        assert "LA-DDD-0002 Reporte VBA" in result.folder_path

    def test_returns_correct_color_in_result(self, tmp_path):
        cfg = {**CONFIG, "local_base_path": str(tmp_path)}
        provisioner = LocalFolderProvisioner(cfg)

        result_blue = provisioner.provision("LA-DDD-0003", "Agente X", "ia")
        assert result_blue.color == FolderColor.BLUE

        result_green = provisioner.provision("LA-DDD-0004", "Macro cierre", "vba")
        assert result_green.color == FolderColor.GREEN

        result_yellow = provisioner.provision("LA-DDD-0005", "Dashboard", "powerbi")
        assert result_yellow.color == FolderColor.YELLOW

    def test_idempotent_if_folder_already_exists(self, tmp_path):
        cfg = {**CONFIG, "local_base_path": str(tmp_path)}
        provisioner = LocalFolderProvisioner(cfg)
        provisioner.provision("LA-DDD-0006", "Proyecto existente", "")
        result = provisioner.provision("LA-DDD-0006", "Proyecto existente", "")
        assert result.success is True

    def test_failure_when_base_path_not_accessible(self):
        cfg = {**CONFIG, "local_base_path": "/ruta/que/no/existe/jamás/xyz123"}
        provisioner = LocalFolderProvisioner(cfg)
        result = provisioner.provision("LA-DDD-0007", "Test", "")
        assert result.success is False
        assert result.error is not None
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```
pytest tests/infra/test_folder_provisioner.py -v
```

Expected: ERROR/ImportError — el módulo no existe aún.

### 2b — Implementar el módulo

- [ ] **Step 3: Crear `infra/folder_provisioner.py`**

```python
"""Provisioning de carpetas de proyecto en almacenamiento local (fase 1).

Interfaz abstracta FolderProvisioner para que en fase 2 se agregue
SharePointFolderProvisioner sin modificar la UI ni la lógica de color.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class FolderColor(str, Enum):
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


@dataclass
class FolderProvisionResult:
    success: bool
    folder_path: str
    color: FolderColor
    error: Optional[str] = None


def detect_color(name: str, description: str, config: dict) -> FolderColor:
    """Detecta el color de carpeta según palabras clave en nombre y descripción."""
    text = f"{name} {description}".lower()
    rules: dict = config.get("color_rules", {})
    # azul tiene prioridad sobre verde
    for keyword in rules.get("blue", []):
        if keyword in text:
            return FolderColor.BLUE
    for keyword in rules.get("green", []):
        if keyword in text:
            return FolderColor.GREEN
    return FolderColor.YELLOW


class FolderProvisioner(ABC):
    """Interfaz abstracta para aprovisionar carpetas de proyecto."""

    @abstractmethod
    def provision(
        self, project_id: str, project_name: str, description: str
    ) -> FolderProvisionResult:
        """Crea la carpeta del proyecto y sus subcarpetas."""


class LocalFolderProvisioner(FolderProvisioner):
    """Implementación local: crea carpetas en el sistema de archivos."""

    def __init__(self, config: dict) -> None:
        self._base = Path(config["local_base_path"])
        self._subfolders: list[str] = config.get("subfolders", [])
        self._config = config

    def provision(
        self, project_id: str, project_name: str, description: str
    ) -> FolderProvisionResult:
        folder_name = f"{project_id} {project_name}"
        color = detect_color(project_name, description, self._config)
        target = self._base / folder_name
        try:
            target.mkdir(parents=True, exist_ok=True)
            for sub in self._subfolders:
                (target / sub).mkdir(exist_ok=True)
            _apply_folder_color(target, color)
            return FolderProvisionResult(
                success=True, folder_path=str(target), color=color
            )
        except Exception as exc:
            return FolderProvisionResult(
                success=False, folder_path=str(target), color=color, error=str(exc)
            )


def _apply_folder_color(folder_path: Path, color: FolderColor) -> None:
    """Aplica color a la carpeta (solo Windows, via COM/shell; falla silenciosamente en otros OS)."""
    # Los colores de carpeta en Windows/SharePoint se controlan por el archivo desktop.ini
    # con la propiedad IconIndex o via shell32. En carpetas de OneDrive/SharePoint
    # el color se setea escribiendo un atributo en desktop.ini.
    _COLOR_INDEX = {
        FolderColor.BLUE: 4,    # azul
        FolderColor.GREEN: 3,   # verde
        FolderColor.YELLOW: 5,  # amarillo
    }
    try:
        import ctypes
        ini_path = folder_path / "desktop.ini"
        index = _COLOR_INDEX.get(color, 5)
        ini_path.write_text(
            f"[.ShellClassInfo]\nIconIndex={index}\n",
            encoding="utf-8",
        )
        # Marcar desktop.ini como Hidden+System y la carpeta como ReadOnly+System
        # para que Windows lo tome como carpeta personalizada
        FILE_ATTRIBUTE_HIDDEN = 0x2
        FILE_ATTRIBUTE_SYSTEM = 0x4
        FILE_ATTRIBUTE_READONLY = 0x1
        ctypes.windll.kernel32.SetFileAttributesW(
            str(ini_path), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        )
        ctypes.windll.kernel32.SetFileAttributesW(
            str(folder_path), FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_SYSTEM
        )
    except Exception:
        pass  # falla silenciosamente en Linux/macOS o si no hay permisos


def load_provisioner_from_config(config_path: str = "config/folder_provisioner_config.json") -> FolderProvisioner:
    """Factory: carga config y retorna el provisioner adecuado (local por ahora)."""
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    return LocalFolderProvisioner(cfg)
```

- [ ] **Step 4: Ejecutar tests**

```
pytest tests/infra/test_folder_provisioner.py -v
```

Expected: todos PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add infra/folder_provisioner.py tests/infra/test_folder_provisioner.py
git commit -m "feat: add folder provisioner module with local implementation and color detection"
```

---

## Task 3: Hook en `planning.py` al aprobar

**Files:**
- Modify: `ui/tabs/planning.py` (línea ~625, justo después de `sync_to_use_case_matrix`)

El bloque de aprobación exitosa actualmente es (líneas ~625–635):

```python
sync_to_use_case_matrix(project_id, calc_inputs, persisted_results)
st.session_state.selected_project_id = project_id
...
msg = t("project_approved_sent_to_agenda") if approve_click else t("evaluation_saved_msg")
st.success(f"{msg} ID: {project_id}")
```

- [ ] **Step 1: Agregar import al inicio de planning.py** (junto con los otros imports, líneas ~1-15)

Buscar el bloque de imports al inicio del archivo y agregar:

```python
from infra.folder_provisioner import load_provisioner_from_config
```

- [ ] **Step 2: Reemplazar el bloque de mensaje de éxito para incluir el provisioning**

Localizar exactamente este fragmento en `planning.py` (dentro del bloque `if approve_click:`, después del try exitoso):

```python
                    sync_to_use_case_matrix(project_id, calc_inputs, persisted_results)
                    st.session_state.selected_project_id = project_id
                    st.session_state.latest_results = persisted_results
                    st.session_state.temp_calculation = {
                        "project_data": calc_inputs,
                        "results": persisted_results,
                        "is_temporary": False,
                    }
                    msg = t("project_approved_sent_to_agenda") if approve_click else t("evaluation_saved_msg")
                    st.success(f"{msg} ID: {project_id}")
                    st.rerun()
```

Reemplazar por:

```python
                    sync_to_use_case_matrix(project_id, calc_inputs, persisted_results)
                    st.session_state.selected_project_id = project_id
                    st.session_state.latest_results = persisted_results
                    st.session_state.temp_calculation = {
                        "project_data": calc_inputs,
                        "results": persisted_results,
                        "is_temporary": False,
                    }
                    msg = t("project_approved_sent_to_agenda") if approve_click else t("evaluation_saved_msg")
                    st.success(f"{msg} ID: {project_id}")

                    if approve_click:
                        try:
                            provisioner = load_provisioner_from_config()
                            prov_result = provisioner.provision(
                                project_id=project_id,
                                project_name=calc_inputs.get("name", ""),
                                description=calc_inputs.get("description", ""),
                            )
                            if prov_result.success:
                                st.info(
                                    t("folder_provisioned_ok").format(
                                        path=prov_result.folder_path,
                                        color=prov_result.color.value,
                                    )
                                )
                            else:
                                st.warning(
                                    t("folder_provisioned_warning").format(
                                        error=prov_result.error
                                    )
                                )
                        except Exception as prov_exc:
                            st.warning(t("folder_provisioned_warning").format(error=str(prov_exc)))

                    st.rerun()
```

- [ ] **Step 3: Verificar que no se rompieron imports**

```
python -c "from ui.tabs.planning import render_planning_tab; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ui/tabs/planning.py
git commit -m "feat: trigger folder provisioning on project approval"
```

---

## Task 4: Strings i18n en `shared.py`

**Files:**
- Modify: `ui/tabs/shared.py`

El archivo tiene diccionarios por idioma (`es`, `pt`, `en`). Agregar las nuevas claves en cada uno.

- [ ] **Step 1: Agregar claves en el bloque español**

Buscar la clave `'project_approved_sent_to_agenda'` en el bloque `es` (línea ~197) y agregar DESPUÉS:

```python
        'folder_provisioned_ok': '📁 Carpeta creada: {path} (color: {color})',
        'folder_provisioned_warning': '⚠️ Proyecto aprobado pero no se pudo crear la carpeta: {error}',
```

- [ ] **Step 2: Agregar claves en el bloque portugués**

Buscar `'project_approved_sent_to_agenda'` en el bloque `pt` (línea ~681) y agregar DESPUÉS:

```python
        'folder_provisioned_ok': '📁 Pasta criada: {path} (cor: {color})',
        'folder_provisioned_warning': '⚠️ Projeto aprovado mas não foi possível criar a pasta: {error}',
```

- [ ] **Step 3: Agregar claves en el bloque inglés** (buscar la misma clave en el bloque `en`)

```python
        'folder_provisioned_ok': '📁 Folder created: {path} (color: {color})',
        'folder_provisioned_warning': '⚠️ Project approved but folder could not be created: {error}',
```

- [ ] **Step 4: Verificar que las claves existen**

```python
python -c "
from ui.tabs.shared import t
import streamlit as st
# simular idioma español
print(t('folder_provisioned_ok').format(path='/test', color='blue'))
print(t('folder_provisioned_warning').format(error='test error'))
"
```

Expected (con idioma default `es`):
```
📁 Carpeta creada: /test (color: blue)
⚠️ Proyecto aprobado pero no se pudo crear la carpeta: test error
```

- [ ] **Step 5: Commit**

```bash
git add ui/tabs/shared.py
git commit -m "i18n: add folder provisioner status messages in es/pt/en"
```

---

## Task 5: Test de integración end-to-end del hook

**Files:**
- Create: `tests/infra/test_folder_provisioner_integration.py`

- [ ] **Step 1: Crear el test de integración**

```python
# tests/infra/test_folder_provisioner_integration.py
"""Verifica que la config real carga correctamente y el provisioner funciona con tmp_path."""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.folder_provisioner import load_provisioner_from_config, FolderColor


def test_load_from_real_config_and_provision(tmp_path):
    # Cargar config real pero sobreescribir la ruta base
    config_path = Path("config/folder_provisioner_config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["local_base_path"] = str(tmp_path)

    # Guardar config temporal
    tmp_config = tmp_path / "test_config.json"
    with open(tmp_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    provisioner = load_provisioner_from_config(str(tmp_config))
    result = provisioner.provision("LA-DDD-0099", "Agente de Prueba", "usa ia generativa")

    assert result.success is True
    assert result.color == FolderColor.BLUE
    project_folder = tmp_path / "LA-DDD-0099 Agente de Prueba"
    assert project_folder.exists()
    for sub in cfg["subfolders"]:
        assert (project_folder / sub).exists(), f"Falta subcarpeta: {sub}"


def test_vba_project_gets_green_folder(tmp_path):
    config_path = Path("config/folder_provisioner_config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["local_base_path"] = str(tmp_path)
    tmp_config = tmp_path / "test_config.json"
    with open(tmp_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    provisioner = load_provisioner_from_config(str(tmp_config))
    result = provisioner.provision("LA-DDD-0100", "Cierre mensual VBA", "macro de excel vba")
    assert result.color == FolderColor.GREEN


def test_generic_project_gets_yellow_folder(tmp_path):
    config_path = Path("config/folder_provisioner_config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["local_base_path"] = str(tmp_path)
    tmp_config = tmp_path / "test_config.json"
    with open(tmp_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    provisioner = load_provisioner_from_config(str(tmp_config))
    result = provisioner.provision("LA-DDD-0101", "Dashboard PowerBI", "reporte de ventas mensual")
    assert result.color == FolderColor.YELLOW
```

- [ ] **Step 2: Ejecutar todos los tests**

```
pytest tests/infra/ -v
```

Expected: todos PASS (10 tests).

- [ ] **Step 3: Commit final**

```bash
git add tests/infra/test_folder_provisioner_integration.py
git commit -m "test: add integration tests for folder provisioner with real config"
```

---

## Self-Review

### Cobertura de spec

| Requisito | Task |
|---|---|
| Crear carpeta `ID + nombre` al aprobar | Task 3 |
| Color azul para agente/IA | Task 2 (detect_color) |
| Color verde para VBA | Task 2 (detect_color) |
| Color amarillo por default | Task 2 (detect_color) |
| 5 subcarpetas (`0_documentación`…`4_Evidencias`) | Task 1 + 2 |
| Detección por palabras clave en nombre/descripción | Task 2 |
| Modular para migración a SharePoint cloud | `FolderProvisioner` ABC en Task 2 |
| No romper flujo si falla el provisioning | Task 3 (try/except con warning, no error) |
| Config externalizada | Task 1 |

### Notas de migración a la nube (fase 2)

Para migrar a SharePoint Online solo se necesita:
1. Agregar `SharePointFolderProvisioner(FolderProvisioner)` en `infra/folder_provisioner.py`
2. Cambiar `load_provisioner_from_config()` para retornar la nueva clase según un flag en config (ej. `"mode": "sharepoint"`)
3. Cero cambios en `planning.py` ni en los tests existentes
