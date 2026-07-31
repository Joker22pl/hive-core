"""Evidence bundle — model and serialization helpers.

H0: model serialization to JSON, path conventions.
H3+: full bundle generation in runtime operations.
"""

from __future__ import annotations

import json
from pathlib import Path

from hive.common.models.evidence_bundle import EvidenceBundle


def write_bundle(bundle: EvidenceBundle, path: str | Path) -> Path:
    """Write an EvidenceBundle to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        bundle.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return p


def read_bundle(path: str | Path) -> EvidenceBundle:
    """Read an EvidenceBundle from a JSON file."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return EvidenceBundle.model_validate(data)


__all__ = ["read_bundle", "write_bundle"]
