"""Device / artifact / profile registry.

H0 scope: load and validate manifests from disk.
H1+: SQLite-backed registry, scan helpers, register CLI.
"""

from hive.common.errors import (
    RegistryAccessError,
    RegistryNotFoundError,
)
from hive.registry.loader import (
    load_all_device_manifests,
    load_artifact_manifest,
    load_device_manifest,
    load_profile,
)
from hive.registry.validator import validate_manifest_against_schema

__all__ = [
    "RegistryAccessError",
    "RegistryNotFoundError",
    "load_all_device_manifests",
    "load_artifact_manifest",
    "load_device_manifest",
    "load_profile",
    "validate_manifest_against_schema",
]
