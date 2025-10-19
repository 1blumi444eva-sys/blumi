# File: /postbot/utils/metadata.py
"""
Append-safe metadata manager for PostBot v3 (Windows-safe version).
"""

from __future__ import annotations
import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any
from bots.postbot.utils.logger import get_logger


logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "history"
METADATA_FILE = HISTORY_DIR / "metadata_v3.json"


def _ensure_file() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if not METADATA_FILE.exists():
        with open(METADATA_FILE, "w", encoding="utf-8") as fh:
            json.dump({"runs": []}, fh, indent=2)


def append_run(entry: Dict[str, Any]) -> None:
    """Append a run entry atomically (Windows-safe)."""
    _ensure_file()
    entry["timestamp"] = datetime.now(UTC).isoformat()

    with open(METADATA_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        data = {"runs": []}
    data.setdefault("runs", []).append(entry)

    # Create temporary file, write, then close before rename
    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, encoding="utf-8", dir=HISTORY_DIR
    )
    try:
        json.dump(data, tmp, indent=2)
        tmp.flush()
    finally:
        tmp.close()  # crucial on Windows
    Path(tmp.name).replace(METADATA_FILE)
    logger.info(f"Metadata appended for run: {entry.get('run_id', 'unknown')}")
