"""Carga de configuracion para scoring y reglas de ID."""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - opcional en runtime actual
    yaml = None


logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/scoring_config.json")
DEFAULT_APP_CONFIG_PATH = Path("config/config.yaml")


class ConfigLoader:
    """Loader de configuracion JSON editable."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH

    def load(self) -> dict:
        """Retorna diccionario de configuracion."""
        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)


def load_app_config(config_path: Path | None = None) -> dict[str, Any]:
    """Carga config central YAML para reglas de negocio transversales."""
    path = config_path or DEFAULT_APP_CONFIG_PATH
    if not path.exists():
        logger.warning(
            "config.yaml not found at %s — using empty config. approval_threshold and allowed_statuses will use hardcoded defaults.",
            path,
        )
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML no está instalado. Instala dependencias de desarrollo.")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        return {}
    return data
