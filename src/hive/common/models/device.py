"""Pydantic model for device manifests."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SSH_FP_RE = re.compile(r"^SHA256:[A-Za-z0-9+/=]+$")
_VID_PID_RE = re.compile(r"^[0-9A-Fa-f]{4}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class SshIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(default=22, ge=1, le=65535)
    user: str
    host_key_fingerprint: str | None = None
    credential_reference: str | None = None

    @field_validator("host_key_fingerprint")
    @classmethod
    def _validate_fingerprint(cls, v: str | None) -> str | None:
        if v is not None and not _SSH_FP_RE.match(v):
            raise ValueError("ssh.host_key_fingerprint must match SHA256:<base64> pattern")
        return v


class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usb_vid: str | None = None
    usb_pid: str | None = None
    serial_number: str | None = None
    stable_path: str | None = None
    ssh: SshIdentity | None = None

    @field_validator("usb_vid", "usb_pid")
    @classmethod
    def _validate_vid_pid(cls, v: str | None) -> str | None:
        if v is not None and not _VID_PID_RE.match(v):
            raise ValueError("usb_vid/usb_pid must be 4 hex characters")
        return v


class FirmwareRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str | None = None
    expected_project: str | None = None
    known_good_artifact: str | None = None


class SafetyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motor_power_required: bool = False
    motor_enable_must_be_off_during_flash: bool = True
    automatic_power_cycle_allowed: bool = False
    automatic_flash_allowed: bool = False


class RecoveryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: str = "none"
    max_attempts: int = Field(default=3, ge=0, le=10)
    escalate_to_human_after: int = Field(default=3, ge=0, le=10)


class DeviceManifest(BaseModel):
    """HIVE device manifest (validated against device.schema.json)."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str | None = None
    type: Literal["microcontroller", "linux_host", "io_controller", "programmer", "debugger"]
    board: str | None = None
    project: str
    role: str
    identity: Identity
    capabilities: list[str] = Field(default_factory=list)
    firmware: FirmwareRef = Field(default_factory=FirmwareRef)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capabilities")
    @classmethod
    def _validate_capabilities(cls, v: list[str]) -> list[str]:
        allowed = {
            "usb-cdc",
            "uart",
            "spi",
            "i2c",
            "can",
            "flash",
            "reset",
            "reset-control",
            "boot-control",
            "motor-control",
            "motor-enable",
            "microros-serial",
            "power-control",
            "estop-sense",
            "watchdog",
            "ssh",
            "systemd",
            "ros2",
        }
        for c in v:
            if c not in allowed:
                raise ValueError(f"Unknown capability: {c!r}")
        return v

    @property
    def has_serial(self) -> bool:
        return bool(self.identity.serial_number)

    @property
    def has_strong_identity(self) -> bool:
        """Strong identification requires (VID + PID) + serial."""
        return bool(self.identity.usb_vid and self.identity.usb_pid and self.identity.serial_number)

    def has_capability(self, name: str) -> bool:
        return name in self.capabilities
