"""Runtime configuration loading."""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_CONFIG = {
    "log_dir": "logs",
    "temp_dir": "temp",
    "log_level": "INFO",
    "overwrite": False,
    "ser_endian_mode": "legacy",
}


def load_config(path: Path) -> dict:
    """Load and validate runtime configuration.

    Parameters
    ----------
    path : pathlib.Path
        Configuration JSON path.

    Returns
    -------
    dict
        Configuration merged with defaults.
    """
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("config.jsonのルートはJSONオブジェクトである必要があります。")
    return {**DEFAULT_CONFIG, **data}
