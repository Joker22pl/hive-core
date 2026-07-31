"""Test fixtures: in-memory registry directories with sample manifests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def registry_dir(tmp_path: Path) -> Path:
    """Create a temporary registry/devices directory with sample manifests."""
    d = tmp_path / "registry" / "devices"
    d.mkdir(parents=True)

    (d / "esp32s3-test-01.yaml").write_text(
        """
device_id: esp32s3-test-01
display_name: Test ESP32-S3
type: microcontroller
board: esp32-s3-pico
project: TEST
role: motor-controller

identity:
  usb_vid: "303A"
  usb_pid: "1001"
  serial_number: TEST-SN-001
  stable_path: /dev/hive/esp32s3-test-01

capabilities:
  - usb-cdc
  - uart
  - flash
  - reset

safety:
  motor_enable_must_be_off_during_flash: true
  automatic_flash_allowed: true

recovery:
  strategy: esp32-bootloader-reflash
  max_attempts: 3
  escalate_to_human_after: 3
""",
        encoding="utf-8",
    )

    (d / "_README.md").write_text("# README", encoding="utf-8")
    (d / "README.md").write_text("# README", encoding="utf-8")

    return d
