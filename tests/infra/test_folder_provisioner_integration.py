# tests/infra/test_folder_provisioner_integration.py
"""Verifica que la config real carga correctamente y el provisioner funciona con tmp_path."""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.folder_provisioner import load_provisioner_from_config, FolderColor


def test_load_from_real_config_and_provision(tmp_path):
    config_path = Path("config/folder_provisioner_config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["local_base_path"] = str(tmp_path)

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
