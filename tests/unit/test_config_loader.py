import pytest
import logging
from unittest.mock import patch
from infra.config_loader import load_app_config
from infra.folder_provisioner import LocalFolderProvisioner


def test_load_app_config_warns_when_file_missing(caplog):
    with patch("infra.config_loader.Path.exists", return_value=False):
        with caplog.at_level(logging.WARNING):
            result = load_app_config()
    assert result == {}
    assert any("config.yaml" in msg for msg in caplog.messages), \
        "Debe emitir un warning mencionando config.yaml cuando el archivo no existe"


def test_local_folder_provisioner_raises_clear_error_when_key_missing():
    with pytest.raises(KeyError, match="local_base_path"):
        LocalFolderProvisioner({})
