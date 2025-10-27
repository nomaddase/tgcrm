"""Utilities for configuring structured logging."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

_DEFAULT_LOG_LEVEL = "INFO"


class JsonLogFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack"] = self.formatStack(record.stack_info)
        extra = getattr(record, "extra", None)  # type: ignore[attr-defined]
        if isinstance(extra, dict):
            log_record.update(extra)

        return json.dumps(log_record, ensure_ascii=False)


def configure_logging(default_level: str | None = None) -> None:
    """Configure root logging handler using JSON formatter."""

    level_name = os.getenv("LOG_LEVEL", default_level or _DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


__all__ = ["configure_logging", "JsonLogFormatter"]
