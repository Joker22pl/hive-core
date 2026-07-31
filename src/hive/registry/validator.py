"""JSON Schema validation for HIVE manifests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from hive.common.errors import SchemaValidationError

_SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"


def _load_schema(name: str) -> dict:
    path = _SCHEMAS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _load_schema(schema_name)
    return Draft202012Validator(schema)


def validate_manifest_against_schema(data: dict, schema_name: str) -> None:
    """Validate `data` against the named schema. Raises SchemaValidationError on failure.

    `schema_name` is the filename in `schemas/` (e.g. 'device.schema.json').
    """
    validator = _validator(schema_name)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msg_lines = [
            f"- {'/'.join(str(p) for p in err.absolute_path)}: {err.message}" for err in errors
        ]
        raise SchemaValidationError(
            f"Manifest failed schema validation ({schema_name}):\n" + "\n".join(msg_lines),
            details={"schema": schema_name, "errors": [e.message for e in errors]},
        )


__all__ = ["validate_manifest_against_schema"]
