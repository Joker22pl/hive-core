"""HIVE Core ↔ HIVE-IO protocol model.

Implements the JSON Lines protocol described in
`hive-core/docs/io-protocol.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = "0.1.0"


# ---------- Channels ----------

POWER_CHANNELS = (
    "power_esp32_1",
    "power_esp32_2",
    "power_pico_1",
    "power_pico_2",
    "power_sensor_1",
    "power_aux_1",
    "power_host_1",
)

BOOT_CHANNELS = ("boot_esp32_1", "boot_esp32_2", "boot_pico_1")
RESET_CHANNELS = ("reset_esp32_1", "reset_esp32_2", "reset_pico_1")


PowerChannel = Literal[
    "power_esp32_1",
    "power_esp32_2",
    "power_pico_1",
    "power_pico_2",
    "power_sensor_1",
    "power_aux_1",
    "power_host_1",
]
BootChannel = Literal["boot_esp32_1", "boot_esp32_2", "boot_pico_1"]
ResetChannel = Literal["reset_esp32_1", "reset_esp32_2", "reset_pico_1"]


# ---------- Commands ----------


class Request(BaseModel):
    """A request from HIVE Core to HIVE-IO."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: str = PROTOCOL_VERSION
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:8]}")
    command: str
    params: dict[str, Any] = Field(default_factory=dict)

    def to_jsonl(self) -> str:
        """Serialize as a single JSON Lines message."""
        return self.model_dump_json() + "\n"


class Response(BaseModel):
    """A response from HIVE-IO."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: str = PROTOCOL_VERSION
    request_id: str
    result: Literal["ok", "error"]
    observed_state: Any | None = None
    error_class: str | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    """Shorthand for an error response from HIVE-IO."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: str = PROTOCOL_VERSION
    request_id: str
    result: Literal["error"] = "error"
    error_class: str
    message: str
    observed_state: Any | None = None


class AsyncEvent(BaseModel):
    """Unsolicited event from HIVE-IO to HIVE Core."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: str = PROTOCOL_VERSION
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex[:8]}")
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


def validate_protocol_version(message_version: str) -> None:
    """Raise if `message_version` is incompatible with PROTOCOL_VERSION.

    Rules:
    - MAJOR must match (SemVer "MAJOR.MINOR.PATCH")
    - PATCH may differ
    - MINOR: client must support message's MINOR (here: equal or lower)
    """

    def parse(v: str) -> tuple[int, int, int]:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"protocol_version must be MAJOR.MINOR.PATCH, got {v!r}")
        return int(parts[0]), int(parts[1]), int(parts[2])

    msg_major, msg_minor, _ = parse(message_version)
    cur_major, cur_minor, _ = parse(PROTOCOL_VERSION)
    if msg_major != cur_major:
        raise ValueError(f"Protocol MAJOR mismatch: message={msg_major}, client={cur_major}")
    if msg_minor > cur_minor:
        raise ValueError(
            f"Protocol MINOR too new: message={msg_minor}, client supports up to {cur_minor}"
        )
