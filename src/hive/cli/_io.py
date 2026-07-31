"""Shared CLI I/O helpers.

emit_json() lives here so any CLI command can emit parseable JSON
output (single-line, no ANSI codes) without depending on the lock
CLI module. Lock-specific helpers stay in _lock.py.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO


def emit_json(data: dict[str, Any], stream: TextIO | None = None) -> None:
    """Write a single-line JSON object to ``stream`` (default: stdout).

    This bypasses Rich so the output is parseable by ``json.loads()``
    without stripping ANSI color codes.
    """
    stream = stream or sys.stdout
    stream.write(json.dumps(data, default=str, separators=(",", ":")))
    stream.write("\n")