"""Example: validate a device manifest file.

Run from the hive-core root::

    python examples/manifest_validation.py registry/devices/esp32s3-imp2-motor-01.yaml

Or import in your own code::

    from examples.manifest_validation import validate_manifest
    result = validate_manifest("path/to/manifest.yaml")
    if result["ok"]:
        print(f"OK: {result['manifest'].device_id}")
    else:
        print(f"FAIL: {result['error']}")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hive.common.errors import SchemaValidationError
from hive.common.models.device import DeviceManifest
from hive.registry import load_device_manifest
from hive.registry.validator import validate_manifest_against_schema

import yaml


def validate_manifest(path: str | Path) -> dict:
    """Validate a single device manifest.

    Returns ``{"ok": True, "manifest", "pydantic_ok", "schema_ok"}`` on success,
    or ``{"ok": False, "error", "details"}`` on failure.
    """
    p = Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"ok": False, "error": "YAML root is not a mapping"}
    except yaml.YAMLError as e:
        return {"ok": False, "error": f"YAML parse error: {e}"}

    # Layer 1: JSON Schema validation against device.schema.json.
    try:
        validate_manifest_against_schema(data, "device.schema.json")
        schema_ok = True
    except SchemaValidationError as e:
        return {"ok": False, "error": "schema validation failed", "details": e.details}

    # Layer 2: Pydantic strict validation.
    try:
        manifest = DeviceManifest.model_validate(data)
    except Exception as e:
        return {"ok": False, "error": f"pydantic validation failed: {e}"}

    return {
        "ok": True,
        "manifest": manifest,
        "pydantic_ok": True,
        "schema_ok": schema_ok,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/manifest_validation.py <path-to-manifest.yaml>")
        return 2
    result = validate_manifest(sys.argv[1])
    print(json.dumps(
        {k: v if not isinstance(v, DeviceManifest) else v.model_dump(mode="json")
         for k, v in result.items()},
        default=str,
        indent=2,
    ))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
