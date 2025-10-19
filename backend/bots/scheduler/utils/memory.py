# File: /postbot/utils/memory.py
"""
Persistent per-topic voice/tone memory.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
import threading

ROOT = Path(__file__).resolve().parents[1]
MEM_FILE = ROOT / "history" / "voice_memory.json"
_LOCK = threading.Lock()

_DEFAULT = {"voice": "en-US-JennyNeural", "tone": "neutral"}


def _ensure_file() -> None:
    MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEM_FILE.exists():
        with open(MEM_FILE, "w", encoding="utf-8") as fh:
            json.dump({}, fh)


def load_memory() -> Dict[str, Any]:
    _ensure_file()
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_memory(data: Dict[str, Any]) -> None:
    _ensure_file()
    with _LOCK:
        with open(MEM_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)


def get_voice_tone(topic: str) -> Dict[str, Any]:
    data = load_memory()
    return data.get(topic.lower(), _DEFAULT.copy())


def set_voice_tone(topic: str, voice: str, tone: str) -> None:
    data = load_memory()
    data[topic.lower()] = {"voice": voice, "tone": tone}
    save_memory(data)
