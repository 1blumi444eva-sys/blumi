# File: /postbot/utils/logger.py
"""
JSON logger utility for PostBot v3.
"""

from __future__ import annotations
import json
import logging
import sys
from bots.postbot.utils.config import load_config


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
        }
        return json.dumps(data, ensure_ascii=False)


def get_logger(name: str = "postbot") -> logging.Logger:
    cfg = load_config()
    log_json = cfg.get("log_json", True)
    level_name = cfg.get("log_level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter() if log_json else logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
