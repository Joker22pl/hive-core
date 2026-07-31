"""Coverage tests for ``hive.io_controller.client``.

``UsbHiveIOClient`` is an H2 stub. Each method raises
``NotImplementedInStageError``. Exercising every method here keeps
coverage high and ensures the planned_stage markers are correct.
"""

from __future__ import annotations

import pytest

from hive.common.errors import NotImplementedInStageError
from hive.io_controller.client import UsbHiveIOClient


def test_usb_client_construction() -> None:
    """UsbHiveIOClient can be constructed."""
    client = UsbHiveIOClient()
    assert client._STAGE == "H2"
    assert client.protocol_version == "0.1.0"


def test_usb_client_connect_raises_h2() -> None:
    with pytest.raises(NotImplementedInStageError) as exc_info:
        UsbHiveIOClient().connect()
    assert exc_info.value.planned_stage == "H2"


def test_usb_client_close_raises_h2() -> None:
    with pytest.raises(NotImplementedInStageError) as exc:
        UsbHiveIOClient().close()
    assert exc.value.planned_stage == "H2"


def test_usb_client_send_request_raises_h2() -> None:
    from hive.io_controller.protocol import Request

    with pytest.raises(NotImplementedInStageError):
        UsbHiveIOClient().send_request(Request(command="ping"))


@pytest.mark.parametrize(
    "method_name",
    [
        "get_status",
        "get_capabilities",
        "heartbeat",
        "safe_state",
        "estop_status",
        "firmware_version",
    ],
)
def test_usb_client_methods_raise_h2(method_name: str) -> None:
    """All high-level methods raise NotImplementedInStageError(H2)."""
    client = UsbHiveIOClient()
    method = getattr(client, method_name)
    with pytest.raises(NotImplementedInStageError) as exc_info:
        method()
    assert exc_info.value.planned_stage == "H2"


def test_usb_client_power_set_rejects_unknown_channel() -> None:
    """Unknown channel raises ValueError BEFORE the H2 stub fires."""
    # This is the only "early" validation path in UsbHiveIOClient.
    with pytest.raises(ValueError, match="Unknown power channel"):
        UsbHiveIOClient().power_set("unicorn_channel", True)


def test_usb_client_power_cycle_rejects_unknown_channel() -> None:
    with pytest.raises(ValueError, match="Unknown power channel"):
        UsbHiveIOClient().power_cycle("unicorn_channel")
