"""Structured logging initialization from YAML configuration."""

import logging
import logging.config
from pathlib import Path

import yaml

_LOGGING_CONFIG_PATH = Path(__file__).resolve().parents[1].parent / "logging_config.yaml"


def setup_logging(config_path: Path | None = None) -> None:
    """Load and apply the YAML logging configuration.

    Falls back to basic config if the YAML file is missing.
    """
    path = config_path or _LOGGING_CONFIG_PATH
    if path.exists():
        _apply_yaml_config(path)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning("Logging config not found at %s, using basicConfig", path)


def _apply_yaml_config(path: Path) -> None:
    """Parse a YAML file and apply it as the logging configuration."""
    with path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    _ensure_log_directory(config)
    logging.config.dictConfig(config)


def _ensure_log_directory(config: dict) -> None:
    """Create log file directories if they don't exist."""
    handlers = config.get("handlers", {})
    for handler in handlers.values():
        filename = handler.get("filename")
        if filename:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
