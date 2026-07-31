"""Example: end-to-end CLI round-trip.

Run from the hive-core root::

    python examples/cli_round_trip.py

This script drives the `hive` CLI the same way a human or HARE agent
would. It uses ``--json-store`` so the lock survives across separate
processes — that is the only way to test the cross-process path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _find_hive() -> str:
    """Locate the hive CLI: prefer PATH, fall back to the venv copy."""
    import shutil
    found = shutil.which("hive")
    if found:
        return found
    # Look in the conventional venv layout.
    here = Path(__file__).resolve().parent
    for cand in [
        here.parent / ".venv" / "bin" / "hive",
        here.parent / "bin" / "hive",
    ]:
        if cand.exists():
            return str(cand)
    raise FileNotFoundError(
        "hive CLI not found in PATH and no ../.venv/bin/hive next to this script"
    )


HIVE_BIN = _find_hive()


def run(args: list[str], store: str) -> dict:
    """Invoke ``hive`` and return the parsed JSON output."""
    result = subprocess.run(
        [HIVE_BIN, *args, "--json", "--json-store", store],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"hive {args} failed: rc={result.returncode} stderr={result.stderr.strip()}"
        )
    return json.loads(result.stdout.strip())


def main() -> int:
    with tempfile.NamedTemporaryFile(
        suffix=".json", prefix="hive-cli-roundtrip-", delete=False
    ) as f:
        store = f.name

    try:
        # 1. Acquire (auto session_id).
        r1 = run(["lock", "acquire", "cli-demo", "--owner", "audit"], store)
        session_id = r1["lock"]["session_id"]
        assert r1["created"] is True
        assert r1["renewed"] is False
        print(f"acquire: created session_id={session_id}")

        # 2. Re-acquire with the same session_id → renewal.
        r2 = run(
            ["lock", "acquire", "cli-demo", "--owner", "audit",
             "--session-id", session_id],
            store,
        )
        assert r2["created"] is False
        assert r2["renewed"] is True
        print("renew: same session → renewed=True")

        # 3. Release.
        r3 = run(
            ["lock", "release", "cli-demo", "--session-id", session_id],
            store,
        )
        assert r3["released"] is True
        print("release: released=True")

        # 4. Re-acquire (fresh lock, since the previous one was released).
        r4 = run(
            ["lock", "acquire", "cli-demo", "--owner", "audit",
             "--session-id", session_id],
            store,
        )
        assert r4["created"] is True
        print(f"re-acquire: created new lock (session_id={r4['lock']['session_id']})")

        # 5. Clean up.
        run(["lock", "release", "cli-demo", "--session-id", r4["lock"]["session_id"]], store)
        print("cleanup: released")
        return 0
    finally:
        Path(store).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
