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
            if not self._base.exists():
                raise FileNotFoundError(f"Base path does not exist: {self._base}")
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
    """Aplica color a la carpeta via desktop.ini (solo Windows; falla silenciosamente en otros OS)."""
    _COLOR_INDEX = {
        FolderColor.BLUE: 4,
        FolderColor.GREEN: 3,
        FolderColor.YELLOW: 5,
    }
    try:
        import ctypes
        ini_path = folder_path / "desktop.ini"
        index = _COLOR_INDEX.get(color, 5)
        ini_path.write_text(
            f"[.ShellClassInfo]\nIconIndex={index}\n",
            encoding="utf-8",
        )
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
        pass


def load_provisioner_from_config(config_path: str = "config/folder_provisioner_config.json") -> FolderProvisioner:
    """Factory: carga config y retorna el provisioner adecuado (local por ahora)."""
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    return LocalFolderProvisioner(cfg)
