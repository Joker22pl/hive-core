"""Coverage tests for H0 skeleton modules.

These modules intentionally contain only ``NotImplementedInStageError`` stubs
at H0. Real implementations arrive in H1/H3. To keep coverage at the
90% threshold required by CI, we exercise the constructors and the
``NotImplementedInStageError``-raising paths so the stubs are not
"untested code" hiding real bugs.
"""

from __future__ import annotations

import logging

import pytest

from hive.common.errors import NotImplementedInStageError

# ---------- discovery ----------


def test_discovery_module_construction() -> None:
    """DiscoveryService can be constructed (H0 stub)."""
    from hive.discovery import DiscoveryService

    svc = DiscoveryService()
    assert svc is not None


def test_discovery_scan_no_devices_returns_empty() -> None:
    """DiscoveryService.scan returns empty list when no devices found (H1 real impl)."""
    from hive.discovery import DiscoveryService

    svc = DiscoveryService(
        include_usb=False,
        include_serial=False,
    )
    assert svc.scan() == []


# ---------- verification ----------


def test_verification_runner_construction() -> None:
    """VerificationRunner can be constructed (H0 stub)."""
    from hive.verification import VerificationContext, VerificationRunner

    ctx = VerificationContext(device_id="d1", artifact_ref="a1", session_id="s1")
    runner = VerificationRunner(context=ctx)
    assert runner.context is ctx
    assert runner.context.device_id == "d1"


def test_verification_runner_run_raises_not_implemented_in_stage() -> None:
    """VerificationRunner.run raises NotImplementedInStageError."""
    from hive.verification import VerificationContext, VerificationRunner

    runner = VerificationRunner(
        context=VerificationContext(device_id="d1", artifact_ref="a1", session_id="s1")
    )
    with pytest.raises(NotImplementedInStageError) as exc_info:
        runner.run(profile=None)  # type: ignore[arg-type]
    assert exc_info.value.feature == "VerificationRunner.run"
    assert exc_info.value.planned_stage == "H1"


# ---------- recovery ----------


def test_recovery_runner_construction() -> None:
    """RecoveryRunner can be constructed (H0 stub)."""
    from hive.common.models.device import DeviceManifest
    from hive.recovery import RecoveryContext, RecoveryRunner

    manifest = DeviceManifest.model_validate(
        {
            "device_id": "d1",
            "type": "microcontroller",
            "project": "TEST",
            "role": "test",
            "identity": {"usb_vid": "303A", "usb_pid": "1001"},
        }
    )
    ctx = RecoveryContext(device=manifest, attempt=1, session_id="s1")
    runner = RecoveryRunner(context=ctx)
    assert runner.context.attempt == 1


def test_recovery_runner_run_raises_not_implemented_in_stage() -> None:
    """RecoveryRunner.run raises NotImplementedInStageError."""
    from hive.common.models.device import DeviceManifest
    from hive.recovery import RecoveryContext, RecoveryRunner

    manifest = DeviceManifest.model_validate(
        {
            "device_id": "d1",
            "type": "microcontroller",
            "project": "TEST",
            "role": "test",
            "identity": {"usb_vid": "303A", "usb_pid": "1001"},
        }
    )
    runner = RecoveryRunner(context=RecoveryContext(device=manifest, attempt=1, session_id="s1"))
    with pytest.raises(NotImplementedInStageError) as exc_info:
        runner.run()
    assert exc_info.value.feature == "RecoveryRunner.run"
    assert exc_info.value.planned_stage == "H3"


# ---------- logging ----------


def test_setup_logging_default(caplog: pytest.LogCaptureFixture) -> None:
    """setup_logging configures the root logger with structured format."""
    from hive.common.logging import setup_logging

    setup_logging()
    # Calling again should be idempotent (no exception).
    setup_logging("DEBUG")
    # The formatter should be configured on the root logger.
    root = logging.getLogger()
    assert root.level <= logging.DEBUG


def test_get_logger_returns_named_logger() -> None:
    """get_logger returns a logger with the given name."""
    from hive.common.logging import get_logger

    logger = get_logger("hive.test.something")
    assert logger.name == "hive.test.something"
    assert isinstance(logger, logging.Logger)


def test_get_logger_honors_hive_log_level_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HIVE_LOG_LEVEL env var is respected on first setup."""
    monkeypatch.setenv("HIVE_LOG_LEVEL", "DEBUG")
    # Re-import fresh module to pick up env var.
    import importlib

    from hive.common import logging as logging_mod

    importlib.reload(logging_mod)
    try:
        logging_mod.setup_logging()
        assert logging.getLogger().level == logging.DEBUG
    finally:
        # Restore default by reloading with cleared env.
        monkeypatch.delenv("HIVE_LOG_LEVEL", raising=False)
        importlib.reload(logging_mod)
        logging_mod.setup_logging()
