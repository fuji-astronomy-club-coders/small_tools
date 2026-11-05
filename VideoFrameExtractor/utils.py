"""Shared utility functions."""
from __future__ import annotations

import logging
from pathlib import Path


def ensure_project_dirs(project_root: Path, config: dict) -> None:
    """Create required runtime directories.

    Parameters
    ----------
    project_root : pathlib.Path
        Project root directory.
    config : dict
        Runtime configuration.
    """
    for key in ("log_dir", "temp_dir"):
        (project_root / config[key]).mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """Configure console and rotating file logging.

    Parameters
    ----------
    log_dir : pathlib.Path
        Directory where the log file is stored.
    level : str, default="INFO"
        Logging level name.
    """
    from logging.handlers import RotatingFileHandler

    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if root.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_dir / "extractor.log", maxBytes=5 * 1024 * 1024,
        backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(file_handler)
    root.addHandler(console)
