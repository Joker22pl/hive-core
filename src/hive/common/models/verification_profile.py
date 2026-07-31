"""Pydantic model for verification profiles."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PRECONDITION_ALLOWED = {
    "device_match_confirmed",
    "device_locked_by_self",
    "motor_enable_off",
    "estop_inactive",
    "artifact_compatible",
    "artifact_known_good",
    "io_controller_connected",
}

_STEP_TYPE_ALLOWED = {
    "adapter_call",
    "serial_observe",
    "serial_collect",
    "assertion",
    "delay",
    "script",
    "parallel",
}


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    description: str | None = None
    timeout_s: float | None = Field(default=None, gt=0)
    on_failure: Literal["abort", "continue", "classify_failure"] = "abort"
    params: dict[str, Any] = Field(default_factory=dict)
    steps: list[Step] | None = None  # for parallel type only

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in _STEP_TYPE_ALLOWED:
            raise ValueError(f"step.type must be one of {sorted(_STEP_TYPE_ALLOWED)}")
        return v


class SuccessPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    all_steps_passed: bool = True
    collect_evidence: bool = True
    mark_artifact_known_good: bool = False


class FailurePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collect_evidence: bool = True
    attempt_recovery: bool = False
    rollback_to_known_good: bool = False
    max_recovery_attempts: int = Field(default=0, ge=0, le=10)


class VerificationProfile(BaseModel):
    """HIVE verification profile."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    target_type: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1)
    success: SuccessPolicy = Field(default_factory=SuccessPolicy)
    failure: FailurePolicy = Field(default_factory=FailurePolicy)

    @field_validator("preconditions")
    @classmethod
    def _validate_preconditions(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in _PRECONDITION_ALLOWED:
                raise ValueError(f"Unknown precondition: {p!r}")
        return v


Step.model_rebuild()
