# File: /postbot/utils/paths.py
"""
Reliable cross-platform cleanup utilities for PostBot v3.
Ensures old postbot_* runs are rotated with forced deletion for Windows.
"""

from __future__ import annotations
from pathlib import Path
import shutil
import os
import stat
import logging
from bots.postbot.utils.config import load_config

logger = logging.getLogger(__name__)


def _force_delete(path: Path):
    """Handle readonly or locked directories."""
    def onerror(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception as e:
            logger.warning("Force delete failed for %s: %s", p, e)
    shutil.rmtree(path, onerror=onerror)


def list_run_dirs(base_dir: Path) -> list[Path]:
    """Return all postbot_* directories."""
    if not base_dir.exists():
        return []
    return [p for p in base_dir.iterdir() if p.is_dir() and p.name.startswith("postbot_")]


def rotate_old_runs(base_dir: Path) -> None:
    """Keep only the most recent N run dirs (lexical order)."""
    cfg = load_config()
    keep = int(cfg.get("keep_runs", 20))
    runs = list_run_dirs(base_dir)
    if len(runs) <= keep:
        logger.info("No cleanup needed (%d <= %d)", len(runs), keep)
        return

    runs_sorted = sorted(runs, key=lambda p: p.name)
    to_remove = runs_sorted[: len(runs_sorted) - keep]
    for d in to_remove:
        if d.exists():
            _force_delete(d)
            if d.exists():
                try:
                    d.rmdir()
                except Exception as e:
                    logger.warning("Could not remove %s: %s", d, e)
            logger.info("🧹 Deleted old run: %s", d)
    logger.info("Cleanup complete. Kept %d of %d.", keep, len(runs))
