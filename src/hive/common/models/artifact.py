"""Pydantic model for artifact manifests."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class GitRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repo: str
    commit_sha: str
    branch: str | None = None
    dirty: bool = False

    @field_validator("commit_sha")
    @classmethod
    def _validate_commit(cls, v: str) -> str:
        if not _COMMIT_RE.match(v):
            raise ValueError("commit_sha must be 7-40 lowercase hex characters")
        return v


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    format: Literal["esp32-binary", "rp2040-uf2", "deb", "tar.zst", "container-image"]

    @field_validator("sha256")
    @classmethod
    def _validate_sha(cls, v: str) -> str:
        if not _SHA256_RE.match(v):
            raise ValueError("sha256 must be 64 hex characters")
        return v


class BuildInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    toolchain_version: str | None = None
    build_profile: str | None = None
    build_host: str | None = None
    built_at: datetime
    build_command: str
    build_duration_s: float | None = Field(default=None, ge=0)


class TestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str
    result: Literal["passed", "failed", "error", "skipped"]
    evidence_bundle_id: str | None = None
    duration_s: float | None = Field(default=None, ge=0)


class ArtifactManifest(BaseModel):
    """HIVE artifact manifest."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    project: str
    target: str
    target_board: str | None = None
    target_role: str | None = None
    git: GitRef
    artifact: ArtifactRef
    build: BuildInfo
    compatible_devices: list[str] = Field(default_factory=list)
    tests: list[TestResult] = Field(default_factory=list)
    status: Literal[
        "built", "tested", "verified", "known-good", "rejected", "superseded", "archived"
    ]
    superseded_by: str | None = None
    evidence_bundle_id: str | None = None

    @field_validator("artifact_id")
    @classmethod
    def _validate_uuid(cls, v: str) -> str:
        if not _UUID_RE.match(v):
            # Allow also deterministic ids by accepting any 8+ chars matching UUID shape
            # but also allow simple test ids; fall back to UUID parse.
            try:
                UUID(v)
            except (ValueError, AttributeError):
                raise ValueError("artifact_id must be a UUID v4 (or compatible format)") from None
        return v
