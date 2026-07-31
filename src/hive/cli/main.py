"""Hive CLI entry point.

This file defines the `hive` command (registered in pyproject.toml as
`hive = "hive.cli.main:app"`).

H0 scope:
- Typer app with command groups mirroring the API surface defined in
  [`../../docs/architecture.md`](../../docs/architecture.md).
- Each command is a stub: it prints a friendly message indicating
  what would happen and what stage the real implementation belongs to.
- A few commands have real logic: `system status`, `device list`,
  `device inspect`, `lock list` (uses lock service).

H1+: replace stubs with real implementations progressively.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from hive import __stage__, __version__
from hive.common.errors import HiveError

app = typer.Typer(
    name="hive",
    help="HIVE — Hermes Integration & Verification Environment",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

# Subcommand groups
system_app = typer.Typer(help="System status and configuration")
device_app = typer.Typer(help="Device operations")
artifact_app = typer.Typer(help="Artifact operations")
io_app = typer.Typer(help="HIVE-IO controller operations")
lock_app = typer.Typer(help="Resource locking operations")
flash_app = typer.Typer(help="Flashing operations")
verify_app = typer.Typer(help="Verification operations")
recover_app = typer.Typer(help="Recovery operations")
evidence_app = typer.Typer(help="Evidence bundle operations")

app.add_typer(system_app, name="system")
app.add_typer(device_app, name="device")
app.add_typer(artifact_app, name="artifact")
app.add_typer(io_app, name="io")
app.add_typer(lock_app, name="lock")
app.add_typer(flash_app, name="flash")
app.add_typer(verify_app, name="verify")
app.add_typer(recover_app, name="recover")
app.add_typer(evidence_app, name="evidence")


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"hive {__version__} (stage {__stage__})")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """HIVE — controlled integration, programming, flashing, testing, diagnostics, recovery."""


# ---------- system ----------


@system_app.command("status")
def system_status() -> None:
    """Show HIVE Core system status (stage, version, paths)."""
    table = Table(title="HIVE Core — System Status")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("name", "hive-core")
    table.add_row("version", __version__)
    table.add_row("stage", __stage__)
    table.add_row("python", "3.12+")
    table.add_row("io_controller", "not connected (skeleton)")
    table.add_row("lock_store", "in-memory (default)")
    table.add_row("artifact_store", "(not configured)")
    console.print(table)
    console.print("[dim]H0: many subsystems are skeletons. Real I/O arrives in H1+.[/dim]")


# ---------- device ----------


@device_app.command("scan")
def device_scan(
    no_persist: bool = typer.Option(
        False,
        "--no-persist",
        help="Don't persist scan results to the SQLite registry.",
    ),
    no_usb: bool = typer.Option(False, "--no-usb", help="Skip USB enumeration."),
    no_serial: bool = typer.Option(False, "--no-serial", help="Skip serial enumeration."),
    no_ssh: bool = typer.Option(False, "--no-ssh", help="Skip SSH enumeration (H4 stub)."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Scan for USB / serial / SSH devices (H1).

    Default: enumerate USB (pyudev) + serial (pyserial) and persist
    results to the SQLite registry (XDG default path).
    """
    from hive.database.engine import HiveDatabase
    from hive.database.registry import DeviceRegistry
    from hive.discovery import DiscoveryService

    try:
        svc = DiscoveryService(
            include_usb=not no_usb,
            include_serial=not no_serial,
            include_ssh=not no_ssh,
        )
        devices = svc.scan()
    except Exception as e:
        console.print(f"[red]Scan failed[/red]: {e}")
        raise typer.Exit(code=1) from e

    if not no_persist and devices:
        try:
            db = HiveDatabase.default()
            reg = DeviceRegistry(db)
            count = reg.upsert(devices)
            persisted_note = f" (persisted {count} to registry)"
        except Exception as e:
            persisted_note = f" (persist failed: {e})"
    elif not devices:
        persisted_note = ""
    else:
        persisted_note = " (--no-persist)"

    if json_output:
        from hive.cli._io import emit_json

        emit_json(
            {
                "scanned": len(devices),
                "devices": [d.model_dump(mode="json") for d in devices],
            }
        )
        return

    console.print(f"[green]Scanned[/green] {len(devices)} device(s){persisted_note}")

    if not devices:
        return

    table = Table(title=f"Discovered Devices ({len(devices)})")
    table.add_column("source", style="cyan")
    table.add_column("VID:PID", style="white")
    table.add_column("serial", style="white")
    table.add_column("port / ssh", style="white")
    table.add_column("fingerprint", style="dim")
    for d in devices:
        vid_pid = f"{d.usb_vid}:{d.usb_pid}" if d.usb_vid and d.usb_pid else "—"
        port_or_ssh = (
            d.serial_port
            or (f"{d.ssh_user}@{d.ssh_host}:{d.ssh_port}" if d.ssh_host else "—")
            or "—"
        )
        table.add_row(
            d.source,
            vid_pid,
            d.serial_number or "—",
            port_or_ssh,
            d.fingerprint[:16] + "…",
        )
    console.print(table)


@device_app.command("list")
def device_list(
    registry_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--registry",
        help="Override registry/devices directory.",
    ),
) -> None:
    """List devices from the registry."""
    from hive.common.errors import (
        RegistryAccessError,
        RegistryNotFoundError,
        SchemaValidationError,
    )
    from hive.registry import load_all_device_manifests

    base = Path(__file__).resolve().parents[3]
    reg_dir = registry_dir or (base / "registry" / "devices")

    try:
        manifests = load_all_device_manifests(reg_dir)
    except RegistryNotFoundError as e:
        console.print(f"[red]Registry directory not found:[/red] {e.message}")
        raise typer.Exit(code=1) from e
    except RegistryAccessError as e:
        console.print(f"[red]Cannot access registry:[/red] {e.message}")
        raise typer.Exit(code=1) from e
    except SchemaValidationError as e:
        # Show a clean error message — no traceback.
        console.print(f"[red]Invalid manifest:[/red] {e.message}")
        if e.details:
            console.print(f"  details: {e.details}")
        raise typer.Exit(code=1) from e
    table = Table(title=f"Devices ({len(manifests)})")
    table.add_column("device_id", style="cyan")
    table.add_column("type", style="white")
    table.add_column("board", style="white")
    table.add_column("project", style="white")
    table.add_column("role", style="white")
    for m in manifests:
        table.add_row(
            m.device_id,
            m.type,
            m.board or "—",
            m.project,
            m.role,
        )
    console.print(table)


@device_app.command("inspect")
def device_inspect(
    device_id: str = typer.Argument(...),
    registry_dir: Path | None = typer.Option(None, "--registry"),  # noqa: B008
) -> None:
    """Inspect a single device manifest."""
    from hive.registry import load_device_manifest

    base = Path(__file__).resolve().parents[3]
    reg_dir = registry_dir or (base / "registry" / "devices")
    path = reg_dir / f"{device_id}.yaml"
    if not path.exists():
        console.print(f"[red]Manifest not found:[/red] {path}")
        raise typer.Exit(code=1)
    manifest = load_device_manifest(path)
    console.print_json(data=manifest.model_dump(mode="json"))


@device_app.command("register")
def device_register(
    fingerprint: str = typer.Option(
        ...,
        "--fingerprint",
        "-f",
        help="Fingerprint of the discovered device (16+ hex chars).",
    ),
    device_id: str = typer.Option(
        ...,
        "--device-id",
        help="Logical device_id (matches a registry/<id>.yaml).",
    ),
    manifest: Path | None = typer.Option(  # noqa: B008
        None,
        "--manifest",
        help="Path to a DeviceManifest YAML to link (relative to repo root).",
    ),
) -> None:
    """Claim a discovered device and assign it a logical device_id (H1).

    Looks up the device by fingerprint (from `hive device scan`) and
    records the assignment in the SQLite registry. The device_id can
    later be used with `hive lock acquire <device_id>`.
    """
    from hive.database.engine import HiveDatabase
    from hive.database.registry import DeviceRegistry, RegistryError

    try:
        db = HiveDatabase.default()
        reg = DeviceRegistry(db)
        rec = reg.claim(
            fingerprint,
            device_id=device_id,
            manifest_path=manifest,
        )
    except RegistryError as e:
        console.print(f"[red]Claim failed[/red]: {e.message}")
        raise typer.Exit(code=1) from e

    console.print(
        f"[green]Claimed[/green] fingerprint={fingerprint[:16]}… "
        f"device_id={rec.device_id}"
        + (f" manifest={rec.manifest_path}" if rec.manifest_path else "")
    )


@device_app.command("db-list")
def device_db_list(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List devices persisted in the SQLite registry (H1)."""
    from hive.database.engine import HiveDatabase
    from hive.database.registry import DeviceRegistry

    db = HiveDatabase.default()
    reg = DeviceRegistry(db)
    devices = reg.list_devices()

    if json_output:
        from hive.cli._io import emit_json

        emit_json(
            {
                "devices": [
                    {
                        "fingerprint": d.fingerprint,
                        "device_id": d.device_id,
                        "usb_vid": d.usb_vid,
                        "usb_pid": d.usb_pid,
                        "serial_number": d.serial_number,
                        "serial_port": d.serial_port,
                        "serial_by_id": d.serial_by_id,
                        "ssh_host": d.ssh_host,
                        "ssh_user": d.ssh_user,
                        "last_seen_at": d.last_seen_at,
                        "manifest_path": d.manifest_path,
                    }
                    for d in devices
                ],
            }
        )
        return

    if not devices:
        console.print("[dim]No devices in registry. Run `hive device scan` first.[/dim]")
        return

    table = Table(title=f"Registry ({len(devices)})")
    table.add_column("device_id", style="cyan")
    table.add_column("VID:PID", style="white")
    table.add_column("serial", style="white")
    table.add_column("port / ssh", style="white")
    table.add_column("last_seen", style="dim")
    table.add_column("fingerprint", style="dim")
    for d in devices:
        vid_pid = f"{d.usb_vid}:{d.usb_pid}" if d.usb_vid and d.usb_pid else "—"
        port_or_ssh = d.serial_port or (f"{d.ssh_user}@{d.ssh_host}" if d.ssh_host else "—") or "—"
        table.add_row(
            d.device_id or "—",
            vid_pid,
            d.serial_number or "—",
            port_or_ssh,
            d.last_seen_at[:19] if d.last_seen_at else "—",
            d.fingerprint[:16] + "…",
        )
    console.print(table)


@device_app.command("install-udev-rules")
def device_install_udev_rules(
    output: Path | None = typer.Option(  # noqa: B008
        None,
        "--output",
        "-o",
        help="Write rules to this file instead of /etc/udev/rules.d/99-hive.rules.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write to /etc/udev/rules.d/99-hive.rules (requires sudo).",
    ),
) -> None:
    """Generate udev rules for stable /dev/hive/<name> symlinks (H1).

    Default: print the generated rules to stdout.
    With --output <path>: write to that path.
    With --apply: write to /etc/udev/rules.d/99-hive.rules (requires sudo).
    """
    from hive.discovery import DiscoveryService
    from hive.discovery.udev import UdevRuleInstaller

    svc = DiscoveryService()
    devices = svc.scan()
    installer = UdevRuleInstaller(
        install_path=output if output is not None else UdevRuleInstaller.DEFAULT_PATH
    )
    rules_text = installer.generate(devices)

    if apply and output is None:
        try:
            installer.install(rules_text)
            console.print(
                f"[green]Wrote[/green] {installer.install_path}\n"
                "Reload with: sudo udevadm control --reload-rules && sudo udevadm trigger"
            )
        except Exception as e:
            console.print(f"[red]Install failed[/red]: {e}")
            raise typer.Exit(code=1) from e
    elif output is not None:
        installer.install(rules_text)
        console.print(f"[green]Wrote[/green] {output}")
    else:
        # Just print to stdout for inspection
        import sys

        sys.stdout.write(rules_text)
        sys.stdout.flush()


# ---------- artifact ----------


@artifact_app.command("build")
def artifact_build() -> None:
    """Build a firmware artifact (H3+)."""
    console.print(
        "[yellow]artifact build[/yellow] is planned for H3 (idf.py / picotool / Linux package)."
    )


@artifact_app.command("list")
def artifact_list() -> None:
    """List artifacts in the registry (H3+)."""
    console.print(
        "[yellow]artifact list[/yellow] is planned for H3 (SQLite-backed artifact store)."
    )


@artifact_app.command("inspect")
def artifact_inspect(artifact_id: str = typer.Argument(...)) -> None:
    """Inspect an artifact manifest (H3+)."""
    console.print(f"[yellow]artifact inspect {artifact_id}[/yellow] is planned for H3.")


@artifact_app.command("mark-known-good")
def artifact_mark_known_good(artifact_id: str = typer.Argument(...)) -> None:
    """Mark an artifact as known-good (H3+)."""
    console.print(f"[yellow]artifact mark-known-good {artifact_id}[/yellow] is planned for H3.")


# ---------- io ----------


@io_app.command("status")
def io_status() -> None:
    """Show HIVE-IO controller status."""
    from hive.io_controller import MockHiveIOClient

    client = MockHiveIOClient()
    client.connect()
    caps = client.get_capabilities()
    status = client.get_status()
    caps_dict: dict = caps.observed_state if isinstance(caps.observed_state, dict) else {}
    console.print("[cyan]Mock HIVE-IO[/cyan] connected")
    console.print(f"protocol_version: {caps_dict.get('protocol_version')}")
    console.print(f"firmware_version: {caps_dict.get('firmware_version')}")
    console.print(f"status: {status.observed_state}")
    client.close()


@io_app.command("safe-state")
def io_safe_state() -> None:
    """Force HIVE-IO into safe state (idempotent)."""
    from hive.io_controller import MockHiveIOClient

    client = MockHiveIOClient()
    client.connect()
    result = client.safe_state()
    console.print(f"safe_state → {result.result}, observed_state={result.observed_state}")
    client.close()


@io_app.command("power")
def io_power(
    channel: str = typer.Argument(...),
    state: str = typer.Argument(..., help="on / off"),
) -> None:
    """Set power channel on/off."""
    from hive.io_controller import MockHiveIOClient

    if state not in ("on", "off"):
        console.print("[red]state must be 'on' or 'off'[/red]")
        raise typer.Exit(code=1)
    client = MockHiveIOClient()
    client.connect()
    result = client.power_set(channel, state == "on")
    console.print(f"power_set {channel} {state} → {result.result}")
    client.close()


@io_app.command("power-cycle")
def io_power_cycle(channel: str = typer.Argument(...)) -> None:
    """Power-cycle a channel."""
    from hive.io_controller import MockHiveIOClient

    client = MockHiveIOClient()
    client.connect()
    result = client.power_cycle(channel)
    console.print(f"power_cycle {channel} → {result.result}")
    client.close()


@io_app.command("reset")
def io_reset(channel: str = typer.Argument(...)) -> None:
    """Emit a reset pulse."""
    from hive.io_controller import MockHiveIOClient

    client = MockHiveIOClient()
    client.connect()
    result = client.reset_pulse(channel)
    console.print(f"reset_pulse {channel} → {result.result}")
    client.close()


# ---------- lock ----------


@lock_app.command("acquire")
def lock_acquire(
    device_id: str = typer.Argument(...),
    owner: str = typer.Option("hare", "--owner", "-o", help="Lock owner."),
    operation: str = typer.Option("unspecified", "--operation", help="Operation name."),
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Session ID. If omitted, a UUID is generated and printed on acquire.",
    ),
    ttl: int = typer.Option(900, "--ttl", help="Lease TTL in seconds."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a single-line JSON object on stdout.",
    ),
    json_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--json-store",
        help="Optional path to a JSON lock store (H1 will add SQLite).",
    ),
) -> None:
    """Acquire (or renew) a device lock.

    If --session-id is provided, the same session re-acquires and the
    lease is renewed. If a different session_id has the lock, this command
    fails with a non-zero exit code and a clear error message.
    """
    from hive.cli._lock import build_default_service, emit_json, serialize_acquire

    service = build_default_service(json_path=str(json_path) if json_path else None)
    try:
        result = service.acquire(
            device_id,
            owner=owner,
            session_id=session_id,
            operation=operation,
            ttl_seconds=ttl,
        )
    except Exception as e:
        if json_output:
            from hive.cli._lock import serialize_error

            if isinstance(e, HiveError):
                emit_json(serialize_error(e))
            else:
                emit_json({"error": "InternalError", "message": str(e)})
        else:
            console.print(f"[red]Lock acquire failed[/red]: {e}")
        raise typer.Exit(code=1) from e

    if json_output:
        emit_json(serialize_acquire(result))
    else:
        action = "renewed" if result.renewed else "created"
        console.print(
            f"[green]Lock {action}[/green] device_id={device_id} "
            f"session_id={result.lock.session_id} operation={result.lock.operation} "
            f"expires_at={result.lock.expires_at}"
        )
        # Always print session_id prominently for round-trip use.
        console.print(f"session_id = {result.lock.session_id}")


@lock_app.command("release")
def lock_release(
    device_id: str = typer.Argument(...),
    session_id: str = typer.Option(..., "--session-id", "-s", help="Session ID."),
    json_output: bool = typer.Option(False, "--json"),
    json_path: Path | None = typer.Option(None, "--json-store"),  # noqa: B008
) -> None:
    """Release a device lock.

    Requires the session_id returned by `lock acquire`. Mismatched
    session_id is a no-op (returns False) — it does NOT raise, to avoid
    operator confusion.
    """
    from hive.cli._lock import (
        build_default_service,
        emit_json,
        serialize_release,
    )

    service = build_default_service(json_path=str(json_path) if json_path else None)
    released = service.release(device_id, session_id)

    if json_output:
        emit_json(serialize_release(released, device_id, session_id))
    elif released:
        console.print(f"[green]Released[/green] lock for {device_id}")
    else:
        console.print(f"[red]No matching lock[/red] for {device_id} / session {session_id}")
    if not released:
        raise typer.Exit(code=1)


@lock_app.command("list")
def lock_list(
    json_output: bool = typer.Option(False, "--json"),
    json_path: Path | None = typer.Option(None, "--json-store"),  # noqa: B008
    sqlite: bool = typer.Option(
        False,
        "--sqlite",
        help="Use the SQLite registry's lock store instead of in-memory / JSON.",
    ),
) -> None:
    """List active locks.

    By default uses an in-memory store (per-process, lost on exit).
    With --json-store <path>: persistent JSON file store.
    With --sqlite: persistent SQLite store at the default registry path.
    """
    from hive.cli._lock import build_default_service, emit_json

    if sqlite:
        from hive.database.engine import HiveDatabase
        from hive.locking import LockService, SqliteLockStore

        db = HiveDatabase.default()
        service = LockService(SqliteLockStore(db))
    else:
        service = build_default_service(json_path=str(json_path) if json_path else None)
    locks = service.list_active()

    if json_output:
        emit_json({"locks": [lock.model_dump(mode="json") for lock in locks]})
        return

    table = Table(title=f"Active Locks ({len(locks)})")
    table.add_column("device_id", style="cyan")
    table.add_column("owner", style="white")
    table.add_column("session_id", style="white")
    table.add_column("operation", style="white")
    table.add_column("expires_at", style="white")
    for lock in locks:
        table.add_row(
            lock.device_id,
            lock.owner,
            lock.session_id,
            lock.operation,
            str(lock.expires_at),
        )
    console.print(table)


@lock_app.command("sweep")
def lock_sweep(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Remove all expired locks from the SQLite registry (H1)."""
    from hive.database.engine import HiveDatabase
    from hive.locking import LockSweeper, SqliteLockStore

    db = HiveDatabase.default()
    sweeper = LockSweeper(SqliteLockStore(db))
    removed = sweeper.sweep()
    if json_output:
        from hive.cli._io import emit_json

        emit_json({"removed": removed})
        return
    console.print(f"[green]Swept[/green] {removed} expired lock(s)")


# ---------- flash / verify / recover / evidence ----------


@flash_app.command("device")
def flash_cmd(
    device_id: str = typer.Argument(...),
    artifact: str = typer.Option(..., "--artifact", "-a"),
) -> None:
    """Flash an artifact to a device (H3+)."""
    console.print(
        f"[yellow]flash device {device_id} --artifact {artifact}[/yellow] is planned for H3."
    )


@verify_app.command("run")
def verify_run(
    device_id: str = typer.Argument(...),
    profile: str = typer.Option(..., "--profile", "-p"),
) -> None:
    """Run a verification profile on a device (H1+)."""
    console.print(f"[yellow]verify run {device_id} --profile {profile}[/yellow] is planned for H1.")


@recover_app.command("device")
def recover_cmd(device_id: str = typer.Argument(...)) -> None:
    """Run recovery for a device (H3+)."""
    console.print(f"[yellow]recover device {device_id}[/yellow] is planned for H3.")


@evidence_app.command("show")
def evidence_show(run_id: str = typer.Argument(...)) -> None:
    """Show an evidence bundle (H3+)."""
    console.print(f"[yellow]evidence show {run_id}[/yellow] is planned for H3.")


@evidence_app.command("export")
def evidence_export(run_id: str = typer.Argument(...)) -> None:
    """Export an evidence bundle (H3+)."""
    console.print(f"[yellow]evidence export {run_id}[/yellow] is planned for H3.")


if __name__ == "__main__":
    app()
