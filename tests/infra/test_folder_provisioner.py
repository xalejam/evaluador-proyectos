# tests/infra/test_folder_provisioner.py
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.folder_provisioner import (
    FolderColor,
    detect_color,
    LocalFolderProvisioner,
    FolderProvisionResult,
)

CONFIG = {
    "local_base_path": "",
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
