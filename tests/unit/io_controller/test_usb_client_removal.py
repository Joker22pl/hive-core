"""Tests for the post-UsbHiveIOClient cleanup.

UsbHiveIOClient used to be the H2 stub — it raised
NotImplementedInStageError on every method. SerialHiveIOClient now
implements the full surface, so the stub is gone.
"""

from __future__ import annotations

import hive.io_controller.client as client_module


def test_usb_hive_io_client_class_removed() -> None:
    """The H2 stub must no longer exist after the H2 impl is real."""
    assert not hasattr(client_module, "UsbHiveIOClient")


def test_io_controller_module_does_not_export_usb_stub() -> None:
    from hive.io_controller import __all__ as exports

    assert "UsbHiveIOClient" not in exports


def test_serial_hive_io_client_is_constructable_from_module() -> None:
    """The public surface still exposes the real client."""
    from hive.io_controller import SerialHiveIOClient

    assert SerialHiveIOClient is not None


def test_hive_io_client_abc_remains_the_protocol_base() -> None:
    """HiveIOClient is still importable as the abstract base."""
    from hive.io_controller import HiveIOClient

    assert HiveIOClient.__abstractmethods__  # has at least one abstract method
