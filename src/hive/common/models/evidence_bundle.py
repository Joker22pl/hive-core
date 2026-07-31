"""Pydantic model for evidence bundles."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str | None = None
    manifest_path: str | None = None
    identification_status: str | None = None
    observed_port: str | None = None
    observed_serial: str | None = None


class EvidenceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_id: str | None = None
    manifest_path: str | None = None
    sha256: str | None = None


class EvidenceGit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hive_core_repo: str | None = None
    hive_core_commit: str | None = None
    project_repo: str | None = None
    project_commit: str | None = None
    dirty: bool = False


class EvidenceEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hive_host: str | None = None
    hive_user: str | None = None
    python_version: str | None = None
    platform: str | None = None
    kernel: str | None = None


class EvidenceCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str
    params: dict[str, Any] = Field(default_factory=dict)
    exit_code: int | None = None
    duration_s: float | None = Field(default=None, ge=0)


class EvidenceLogs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    build_log_path: str | None = None
    flash_log_path: str | None = None
    device_log_path: str | None = None
    io_log_path: str | None = None


class EvidenceStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    status: Literal["passed", "failed", "error", "skipped"]
    duration_s: float | None = Field(default=None, ge=0)
    observed: str | None = None
    error_class: str | None = None


class EvidenceSafetyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceRecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: str
    attempt: int = Field(ge=1)
    outcome: Literal["passed", "failed", "escalated"]
    timestamp: datetime


class EvidenceRollback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    performed: bool = False
    from_artifact_id: str | None = None
    to_artifact_id: str | None = None
    timestamp: datetime | None = None


class EvidenceBundle(BaseModel):
    """HIVE evidence bundle."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,}$")
    operation: Literal[
        "scan",
        "identify",
        "register",
        "build",
        "flash",
        "verify",
        "recovery",
        "deploy",
        "rollback",
        "io-control",
    ]
    device: EvidenceDevice | None = None
    artifact: EvidenceArtifact | None = None
    git: EvidenceGit | None = None
    environment: EvidenceEnvironment | None = None
    tool_versions: dict[str, str] = Field(default_factory=dict)
    commands: list[EvidenceCommand] = Field(default_factory=list)
    logs: EvidenceLogs | None = None
    step_results: list[EvidenceStepResult] = Field(default_factory=list)
    safety_events: list[EvidenceSafetyEvent] = Field(default_factory=list)
    recovery_decisions: list[EvidenceRecoveryDecision] = Field(default_factory=list)
    rollback: EvidenceRollback | None = None
    started_at: datetime
    ended_at: datetime
    final_status: Literal["passed", "failed", "error", "aborted", "escalated"]

    def duration_s(self) -> float:
        return (self.ended_at - self.started_at).total_seconds()
