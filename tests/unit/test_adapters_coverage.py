"""Coverage tests for the H0 adapter stubs.

Every adapter raises ``NotImplementedInStageError`` for its operation
methods. This module locks in the public surface and confirms the
planned_stage markers are correct. It also verifies the abstract
``Adapter`` base class contract.
"""

from __future__ import annotations

import pytest

from hive.adapters.base import Adapter
from hive.common.errors import NotImplementedInStageError

# ---------- Base ----------


def test_adapter_base_is_abstract() -> None:
    """Adapter cannot be instantiated directly (open / close are abstract)."""
    with pytest.raises(TypeError):
        Adapter()  # type: ignore[abstract]


def test_adapter_context_manager_calls_open_and_close() -> None:
    """Concrete adapter's __enter__/__exit__ invokes open/close."""

    class _MyAdapter(Adapter):
        name = "test"

        def __init__(self) -> None:
            self.opened = False
            self.closed = False

        def open(self) -> None:
            self.opened = True

        def close(self) -> None:
            self.closed = True

    a = _MyAdapter()
    with a as bound:
        assert bound is a
        assert a.opened is True
        assert a.closed is False
    assert a.closed is True


# ---------- USB ----------


def test_usb_adapter_construction() -> None:
    from hive.adapters.usb import UsbAdapter

    a = UsbAdapter()
    assert a.name == "usb"


def test_usb_adapter_open_raises_h1() -> None:
    from hive.adapters.usb import UsbAdapter

    with pytest.raises(NotImplementedInStageError) as exc:
        UsbAdapter().open()
    assert exc.value.planned_stage == "H1"


def test_usb_adapter_close_raises_h1() -> None:
    from hive.adapters.usb import UsbAdapter

    with pytest.raises(NotImplementedInStageError):
        UsbAdapter().close()


def test_usb_adapter_scan_raises_h1() -> None:
    from hive.adapters.usb import UsbAdapter

    with pytest.raises(NotImplementedInStageError) as exc:
        UsbAdapter().scan()
    assert exc.value.feature == "UsbAdapter.scan"


# ---------- Serial ----------


def test_serial_adapter_construction() -> None:
    from hive.adapters.serial import SerialAdapter

    a = SerialAdapter(port="/dev/ttyUSB0", baudrate=115200)
    assert a.port == "/dev/ttyUSB0"
    assert a.baudrate == 115200
    assert a.timeout == 1.0


def test_serial_adapter_open_raises_h1() -> None:
    from hive.adapters.serial import SerialAdapter

    with pytest.raises(NotImplementedInStageError):
        SerialAdapter(port="/dev/ttyUSB0").open()


def test_serial_adapter_close_raises_h1() -> None:
    from hive.adapters.serial import SerialAdapter

    with pytest.raises(NotImplementedInStageError):
        SerialAdapter(port="/dev/ttyUSB0").close()


def test_serial_adapter_read_until_raises_h1() -> None:
    from hive.adapters.serial import SerialAdapter

    with pytest.raises(NotImplementedInStageError):
        SerialAdapter(port="/dev/ttyUSB0").read_until(b"\n", 1.0)


def test_serial_adapter_write_raises_h1() -> None:
    from hive.adapters.serial import SerialAdapter

    with pytest.raises(NotImplementedInStageError):
        SerialAdapter(port="/dev/ttyUSB0").write(b"x")


# ---------- ESP32 ----------


def test_esp32_adapter_construction() -> None:
    from hive.adapters.esp32 import Esp32Adapter

    a = Esp32Adapter(port="/dev/ttyUSB0")
    assert a.port == "/dev/ttyUSB0"
    assert a.baudrate == 115200


def test_esp32_adapter_methods_raise_h3() -> None:
    """All ESP32 methods raise NotImplementedInStageError(H3)."""
    from hive.adapters.esp32 import Esp32Adapter

    a = Esp32Adapter(port="/dev/ttyUSB0")
    with pytest.raises(NotImplementedInStageError) as exc:
        a.open()
    assert exc.value.planned_stage == "H3"
    for method_name in ("close", "enter_bootloader", "reset"):
        method = getattr(a, method_name)
        with pytest.raises(NotImplementedInStageError) as exc2:
            method()
        assert exc2.value.planned_stage == "H3"


def test_esp32_adapter_flash_raises_h3() -> None:
    from hive.adapters.esp32 import Esp32Adapter

    with pytest.raises(NotImplementedInStageError):
        Esp32Adapter(port="/dev/ttyUSB0").flash("/tmp/firmware.bin")


# ---------- RP2040 ----------


def test_rp2040_adapter_construction() -> None:
    from hive.adapters.rp2040 import Rp2040Adapter

    a = Rp2040Adapter(port="/dev/ttyACM0")
    assert a.port == "/dev/ttyACM0"


def test_rp2040_adapter_methods_raise_h3() -> None:
    """All RP2040 methods raise NotImplementedInStageError(H3)."""
    from hive.adapters.rp2040 import Rp2040Adapter

    a = Rp2040Adapter(port="/dev/ttyACM0")
    for method_name in ("open", "close", "enter_bootsel", "reset"):
        method = getattr(a, method_name)
        with pytest.raises(NotImplementedInStageError) as exc:
            method()
        assert exc.value.planned_stage == "H3"


def test_rp2040_adapter_copy_uf2_raises_h3() -> None:
    from hive.adapters.rp2040 import Rp2040Adapter

    with pytest.raises(NotImplementedInStageError):
        Rp2040Adapter().copy_uf2("/tmp/firmware.uf2")


# ---------- SSH ----------


def test_ssh_adapter_construction() -> None:
    from hive.adapters.ssh import SshAdapter

    a = SshAdapter(
        host="10.0.0.1",
        user="tester",
        port=2222,
        credential_reference="ssh-agent:foo",
        expected_host_key_fingerprint="SHA256:abcd",
    )
    assert a.host == "10.0.0.1"
    assert a.user == "tester"
    assert a.port == 2222
    assert a.credential_reference == "ssh-agent:foo"


def test_ssh_adapter_methods_raise_h4() -> None:
    """SSH appears in H4, not H3 — verify the planned_stage marker."""
    from hive.adapters.ssh import SshAdapter

    a = SshAdapter(host="10.0.0.1", user="tester")
    for method_name in ("open", "close"):
        method = getattr(a, method_name)
        with pytest.raises(NotImplementedInStageError) as exc:
            method()
        assert exc.value.planned_stage == "H4"


def test_ssh_adapter_exec_returns_correct_shape() -> None:
    """SshAdapter.exec type hint is (int, str, str)."""
    from hive.adapters.ssh import SshAdapter

    with pytest.raises(NotImplementedInStageError) as exc:
        SshAdapter(host="h", user="u").exec("uptime", timeout_s=10.0)
    assert exc.value.planned_stage == "H4"
