"""Structured logging for HIVE.

Provides a JSON formatter compatible with python-json-logger, plus a
`get_logger` helper that ensures consistent setup across modules.
"""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_DEFAULT_LEVEL = os.environ.get("HIVE_LOG_LEVEL", "INFO").upper()


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with structured format.

    Idempotent: subsequent calls only update the level.
    """
    lvl = (level or _DEFAULT_LEVEL).upper()
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
    root.setLevel(lvl)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Calls setup_logging on first use."""
    setup_logging()
    return logging.getLogger(name)
