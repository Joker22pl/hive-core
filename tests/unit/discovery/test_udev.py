"""Unit tests for hive.discovery.udev."""

from __future__ import annotations

from pathlib import Path

from hive.discovery.fingerprint import compute_fingerprint
from hive.discovery.models import DiscoveredDevice
from hive.discovery.udev import UdevRule, UdevRuleInstaller


def _device(**kwargs):
    """Helper to build a DiscoveredDevice with sensible defaults.

    Only the fingerprint-relevant kwargs (vid, pid, serial, by_id, ssh_*)
    are passed to compute_fingerprint(). Other kwargs (port_path, etc.)
    are kept on the device record but excluded from the hash.
    """
    fp_kwargs = {}
    for k in (
        "usb_vid",
        "usb_pid",
        "serial_number",
        "serial_by_id",
        "ssh_host",
        "ssh_port",
        "ssh_user",
    ):
        if k in kwargs:
            fp_kwargs[k] = kwargs[k]
    defaults = {"source": "usb", "fingerprint": compute_fingerprint(source="usb", **fp_kwargs)}
    defaults.update(kwargs)
    return DiscoveredDevice(**defaults)


class TestUdevRuleRender:
    def test_basic_rule(self):
        rule = UdevRule(
            vid="239a",
            pid="811b",
            serial="ABC123",
            port_path="1-2.3",
            logical_name="robot_imu",
        )
        text = rule.render()
        assert 'SUBSYSTEM=="tty"' in text
        assert 'ATTRS{idVendor}=="239a"' in text
        assert 'ATTRS{idProduct}=="811b"' in text
        assert 'ATTRS{serial}=="ABC123"' in text
        assert 'SYMLINK+="hive/robot_imu"' in text

    def test_no_serial_uses_port_path(self):
        rule = UdevRule(
            vid="239a",
            pid="811b",
            serial=None,
            port_path="1-2.3",
            logical_name="robot_imu",
        )
        text = rule.render()
        assert "ATTRS{serial}" not in text
        assert 'ENV{ID_PATH}=="1-2.3"' in text
        assert 'SYMLINK+="hive/robot_imu"' in text

    def test_no_serial_no_port_skipped(self):
        rule = UdevRule(
            vid="239a",
            pid="811b",
            serial=None,
            port_path=None,
            logical_name="robot_imu",
        )
        text = rule.render()
        assert "SKIPPED" in text
        assert "SYMLINK" not in text

    def test_serial_with_double_quote_escaped(self):
        rule = UdevRule(
            vid="239a",
            pid="811b",
            serial='ABC"123',
            port_path="1-2.3",
            logical_name="robot_imu",
        )
        text = rule.render()
        # The double quote must be backslash-escaped
        assert 'ABC\\"123' in text


class TestUdevRuleInstallerGenerate:
    def test_empty_list(self):
        text = UdevRuleInstaller.generate([])
        assert "Auto-generated" in text
        assert "DO NOT EDIT" in text

    def test_skips_devices_without_vid(self):
        d = _device(
            usb_vid=None,
            usb_pid=None,
            serial_number="ABC",
            serial_port="/dev/ttyACM0",
        )
        text = UdevRuleInstaller.generate([d])
        assert "SYMLINK" not in text

    def test_full_device(self):
        d = _device(
            usb_vid="239a",
            usb_pid="811b",
            serial_number="ABC123",
            usb_port_path="1-2.3",
        )
        text = UdevRuleInstaller.generate([d])
        assert 'ATTRS{serial}=="ABC123"' in text
        assert 'SYMLINK+="hive/239a-811b-ABC123"' in text

    def test_name_map_override(self):
        d = _device(usb_vid="239a", usb_pid="811b", serial_number="ABC")
        text = UdevRuleInstaller.generate([d], name_map={d.fingerprint: "robot_imu"})
        assert 'SYMLINK+="hive/robot_imu"' in text

    def test_default_name_includes_serial(self):
        d = _device(usb_vid="239a", usb_pid="811b", serial_number="ABC")
        text = UdevRuleInstaller.generate([d])
        assert "239a-811b-ABC" in text


class TestUdevRuleInstallerInstall:
    def test_install_to_tmp_path(self, tmp_path: Path):
        install_path = tmp_path / "99-hive.rules"
        installer = UdevRuleInstaller(install_path=install_path)
        installer.install("# HIVE test rule\n")
        assert install_path.exists()
        assert "HIVE test rule" in install_path.read_text()

    def test_install_creates_parent_dir(self, tmp_path: Path):
        install_path = tmp_path / "rules.d" / "99-hive.rules"
        installer = UdevRuleInstaller(install_path=install_path)
        installer.install("# HIVE test rule\n")
        assert install_path.exists()

    def test_install_overwrites_existing(self, tmp_path: Path):
        install_path = tmp_path / "99-hive.rules"
        install_path.write_text("# old content\n")
        installer = UdevRuleInstaller(install_path=install_path)
        installer.install("# new content\n")
        assert install_path.read_text() == "# new content\n"


class TestUdevRuleInstallerDefaultPath:
    def test_default_path_is_etc_udev(self):
        # The default path is /etc/udev/rules.d/99-hive.rules.
        # We don't write to it in tests (requires root), just verify.
        assert str(UdevRuleInstaller.DEFAULT_PATH).startswith("/etc/udev/rules.d/")
