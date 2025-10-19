# File: /postbot/utils/config.py
"""
Load system and style configuration for PostBot v3.
Centralized entry point for reading /config/style.json
and retrieving theme presets.
"""

from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "style.json"

_DEFAULTS: Dict[str, Any] = {
    "themes": {
        "modern": {"font": "Inter", "color": "#FFFFFF", "bg": "#000000"},
    },
    "default_theme": "modern",
    "keep_runs": 20,
    "timeout_seconds": 120,
}


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """Return cached system config dict, falling back to defaults."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        merged = {**_DEFAULTS, **cfg}
        merged["themes"] = {**_DEFAULTS["themes"], **cfg.get("themes", {})}
        return merged
    except Exception as e:
        logger.warning("Failed to load config %s, using defaults: %s", CONFIG_PATH, e)
        return _DEFAULTS.copy()


def load_theme(name: str | None = None) -> Dict[str, Any]:
    """Return theme dict by name, fallback to default."""
    cfg = load_config()
    theme_name = name or cfg.get("default_theme", "modern")
    theme = cfg.get("themes", {}).get(theme_name)
    if not theme:
        logger.warning("Theme '%s' not found, fallback to default.", theme_name)
        theme = cfg["themes"][cfg["default_theme"]]
    return theme.copy()
