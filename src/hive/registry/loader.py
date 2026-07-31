"""Manifest loaders (YAML → Pydantic model).

This module exposes a *list-returning* ``load_all_device_manifests``
function (rather than a generator) so that callers see errors eagerly
instead of silently receiving an empty list.

The following failure modes are explicitly distinguished:

* ``RegistryNotFoundError`` — path does not exist or is not a directory.
* ``RegistryAccessError`` — path exists but cannot be read (perms,
  capability, OS-level I/O error).
* ``SchemaValidationError`` — at least one manifest failed validation
  (this is raised on the first invalid file).

Each individual loader (``load_device_manifest``,
``load_artifact_manifest``, ``load_profile``) raises
``SchemaValidationError`` on any failure.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from hive.common.errors import (
    RegistryAccessError,
    RegistryNotFoundError,
    SchemaValidationError,
)
from hive.common.models.artifact import ArtifactManifest
from hive.common.models.device import DeviceManifest
from hive.common.models.verification_profile import VerificationProfile


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_device_manifest(path: str | Path) -> DeviceManifest:
    """Load and validate a device manifest from a YAML file."""
    p = Path(path)
    try:
        data = _read_yaml(p)
        return DeviceManifest.model_validate(data)
    except Exception as e:
        raise SchemaValidationError(
            f"Failed to load device manifest from {p}",
            details={"path": str(p), "error": str(e)},
        ) from e


def load_all_device_manifests(directory: str | Path) -> list[DeviceManifest]:
    """Load and validate all device manifests from a directory.

    Returns a list (not a generator) so callers can ``len()`` it and so
    that errors surface **eagerly** rather than lazily.

    Raises:
        RegistryNotFoundError: if ``directory`` does not exist or is not
            a directory.
        RegistryAccessError: if the directory exists but cannot be
            enumerated (e.g., permission denied).
        SchemaValidationError: if at least one manifest fails validation.
    """
    d = Path(directory)
    if not d.exists():
        raise RegistryNotFoundError(
            f"Registry directory does not exist: {d}",
            details={"path": str(d)},
        )
    if not d.is_dir():
        raise RegistryNotFoundError(
            f"Registry path is not a directory: {d}",
            details={"path": str(d)},
        )
    try:
        candidate_paths = sorted(d.glob("*.yaml"))
    except PermissionError as e:
        raise RegistryAccessError(
            f"Cannot enumerate registry directory: {d}",
            details={"path": str(d), "error": str(e)},
        ) from e
    except OSError as e:
        raise RegistryAccessError(
            f"OS error while enumerating registry directory: {d}",
            details={"path": str(d), "error": str(e)},
        ) from e

    manifests: list[DeviceManifest] = []
    for path in candidate_paths:
        if path.name.startswith("_"):
            continue
        if path.name == "README.md":
            continue
        manifests.append(load_device_manifest(path))
    return manifests


def load_artifact_manifest(path: str | Path) -> ArtifactManifest:
    """Load and validate an artifact manifest from a YAML file."""
    p = Path(path)
    try:
        data = _read_yaml(p)
        return ArtifactManifest.model_validate(data)
    except Exception as e:
        raise SchemaValidationError(
            f"Failed to load artifact manifest from {p}",
            details={"path": str(p), "error": str(e)},
        ) from e


def load_profile(path: str | Path) -> VerificationProfile:
    """Load and validate a verification profile from a YAML file."""
    p = Path(path)
    try:
        data = _read_yaml(p)
        return VerificationProfile.model_validate(data)
    except Exception as e:
        raise SchemaValidationError(
            f"Failed to load verification profile from {p}",
            details={"path": str(p), "error": str(e)},
        ) from e
